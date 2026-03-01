"""
entitlements.py - Core Entitlement Engine

WHY: Stripe tells us what a customer BOUGHT. This module translates
     that into what they're ALLOWED TO DO. The mapping lives in
     business_config.json so the hero configures it, not the code.

FLOW:
  Stripe webhook fires
        ↓
  sync_entitlements_from_stripe(customer_id, product_ids)
        ↓
  Reads stripe_products map from business_config.json
        ↓
  Writes entitlements to DB
        ↓
  Routes/pages call get_entitlements(user_id) or require_entitlement("feature")
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Session, relationship

from core.database import Base, get_db
try:
    from core.auth import get_current_user  # Auth0 JWT validation
except ImportError:
    get_current_user = None  # Auth0 not yet configured (test / dev environments)

logger = logging.getLogger(__name__)

# ============================================================
# LOAD PRODUCT → ENTITLEMENT MAP FROM CONFIG
# WHY: Hero fills this in. Code never changes per business.
# ============================================================

def _load_product_map() -> dict:
    """
    Load stripe_products map from business_config.json.
    Returns dict: {stripe_product_id: [entitlement, ...]}
    """
    config_path = Path(__file__).parent.parent / "config" / "business_config.json"

    if not config_path.exists():
        logger.warning("business_config.json not found - no entitlements will be granted")
        return {}

    try:
        with open(config_path) as f:
            config = json.load(f)

        product_map = {}
        for product_id, product_data in config.get("stripe_products", {}).items():
            # Support both list format and dict format
            if isinstance(product_data, list):
                product_map[product_id] = product_data
            elif isinstance(product_data, dict):
                product_map[product_id] = product_data.get("entitlements", [])

        logger.info(f"Loaded entitlement map: {len(product_map)} products")
        return product_map

    except Exception as e:
        logger.error(f"Failed to load product map: {e}")
        return {}


# ============================================================
# DATABASE MODEL
# WHY: Persist entitlements so we survive server restarts.
#      Keyed by auth0_user_id so we can look up fast.
# ============================================================

class UserEntitlement(Base):
    """
    One row per user per entitlement.
    WHY flat rows: Easy to query ("does user have X?"),
    easy to add/remove individual features.
    """
    __tablename__ = "user_entitlements"

    id = Column(Integer, primary_key=True, index=True)
    auth0_user_id = Column(String, nullable=False, index=True)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_product_id = Column(String, nullable=False)
    entitlement = Column(String, nullable=False)       # e.g. "ai_sorting"
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)       # null = never expires
    revoked_at = Column(DateTime, nullable=True)       # null = still active

    def is_active(self) -> bool:
        """WHY: Check both expiry and revocation in one place."""
        now = datetime.now(timezone.utc)
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < now:
            return False
        return True


# ============================================================
# CORE ENGINE FUNCTIONS
# ============================================================

def get_entitlements(auth0_user_id: str, db: Session) -> List[str]:
    """
    Get all active entitlements for a user.
    Returns list of entitlement strings e.g. ["dashboard", "ai_sorting"]

    WHY return strings: Simple to check with 'in', easy to serialize to JSON.
    """
    rows = db.query(UserEntitlement).filter(
        UserEntitlement.auth0_user_id == auth0_user_id,
        UserEntitlement.revoked_at.is_(None)
    ).all()

    # Filter active (handles expiry too)
    active = [row.entitlement for row in rows if row.is_active()]

    # Deduplicate (user might have same feature from multiple products)
    return list(set(active))


def has_entitlement(auth0_user_id: str, entitlement: str, db: Session) -> bool:
    """
    Check if user has a specific entitlement.
    WHY separate function: Cleaner than 'x in get_entitlements(...)' everywhere.
    """
    return entitlement in get_entitlements(auth0_user_id, db)


def sync_entitlements_from_stripe(
    auth0_user_id: str,
    stripe_customer_id: str,
    active_product_ids: List[str],
    db: Session
) -> List[str]:
    """
    Called by Stripe webhook handler when subscription changes.
    Replaces all entitlements for this user based on current active products.

    WHY replace-all: Simpler than diffing. Stripe is source of truth.
    If they downgrade, old features get revoked. If they upgrade, new ones added.
    """
    product_map = _load_product_map()
    now = datetime.now(timezone.utc)

    # Step 1: Revoke ALL existing active entitlements for this user
    # WHY: Start fresh from what Stripe says they have right now
    existing = db.query(UserEntitlement).filter(
        UserEntitlement.auth0_user_id == auth0_user_id,
        UserEntitlement.revoked_at.is_(None)
    ).all()

    for row in existing:
        row.revoked_at = now
        logger.info(f"Revoked entitlement: {auth0_user_id} → {row.entitlement}")

    db.flush()

    # Step 2: Grant entitlements from all active products
    granted = []
    seen = set()  # Prevent duplicate rows for same feature

    for product_id in active_product_ids:
        entitlements = product_map.get(product_id, [])

        if not entitlements:
            logger.warning(f"Product {product_id} not found in config or has no entitlements")

        for entitlement in entitlements:
            if entitlement in seen:
                continue  # Already granting this feature from another product
            seen.add(entitlement)

            row = UserEntitlement(
                auth0_user_id=auth0_user_id,
                stripe_customer_id=stripe_customer_id,
                stripe_product_id=product_id,
                entitlement=entitlement,
                granted_at=now
            )
            db.add(row)
            granted.append(entitlement)
            logger.info(f"Granted entitlement: {auth0_user_id} → {entitlement} (from {product_id})")

    db.commit()
    logger.info(f"Sync complete for {auth0_user_id}: {len(granted)} entitlements active")
    return granted


def revoke_all_entitlements(auth0_user_id: str, db: Session) -> int:
    """
    Revoke everything. Called when subscription cancelled/payment failed.
    WHY: Soft delete - keep the history, just mark revoked.
    """
    now = datetime.now(timezone.utc)
    rows = db.query(UserEntitlement).filter(
        UserEntitlement.auth0_user_id == auth0_user_id,
        UserEntitlement.revoked_at.is_(None)
    ).all()

    count = 0
    for row in rows:
        row.revoked_at = now
        count += 1

    db.commit()
    logger.info(f"Revoked all {count} entitlements for {auth0_user_id}")
    return count


# ============================================================
# FASTAPI DEPENDENCY GUARDS
# WHY: Drop these into any route with Depends() - one line to protect a route.
# ============================================================

def get_current_entitlements(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[str]:
    """
    FastAPI dependency - injects user's current entitlements into route.

    Usage:
        @router.get("/dashboard")
        def dashboard(entitlements: List[str] = Depends(get_current_entitlements)):
            if "dashboard" not in entitlements:
                raise HTTPException(403)
    """
    return get_entitlements(user.id, db)


def require_entitlement(feature: str):
    """
    FastAPI dependency factory - enforces a single entitlement on a route.
    Returns 403 with upgrade message if user lacks the feature.

    WHY factory pattern: Creates a specific guard per feature name.

    Usage:
        @router.get("/ai-sort")
        def ai_sort(user=Depends(require_entitlement("ai_sorting"))):
            # Only reaches here if user has ai_sorting entitlement
            ...
    """
    def _guard(
        user=Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not has_entitlement(user.id, feature, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "entitlement_required",
                    "feature": feature,
                    "message": f"Upgrade your plan to access '{feature}'",
                    "upgrade_url": "/pricing"
                }
            )
        return user

    return _guard


def require_any_entitlement(*features: str):
    """
    Guard requiring at least ONE of the listed features.
    WHY: Some routes are accessible on multiple plans.

    Usage:
        @router.get("/reports")
        def reports(user=Depends(require_any_entitlement("analytics", "reports_basic"))):
            ...
    """
    def _guard(
        user=Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        user_entitlements = get_entitlements(user.id, db)
        if not any(f in user_entitlements for f in features):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "entitlement_required",
                    "features": list(features),
                    "message": "Upgrade your plan to access this feature",
                    "upgrade_url": "/pricing"
                }
            )
        return user

    return _guard
