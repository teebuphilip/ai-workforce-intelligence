"""
usage_limits.py - Per-Tenant Usage Quota Enforcement
======================================================

WHY: Plans have feature limits. Basic = 1000 API calls/month.
     Without enforcement, a basic tier user can make unlimited calls.
     That costs us money and breaks the pricing model.

HOW:
    1. UsageCounter tracks usage per tenant per feature per period
    2. check_limit() called before any limited operation
    3. If at limit → raise UsageLimitExceeded (→ HTTP 429)
    4. If within limit → increment counter, proceed

    Usage limits are defined per plan tier in PLAN_LIMITS dict.
    Override per-tenant possible via tenant.config_overrides.

USAGE:
    # In any route that has usage limits:
    from core.usage_limits import check_and_increment, UsageLimitExceeded

    @router.post("/api/export")
    def export_data(
        tenant_id = Depends(get_tenant_id),
        db = Depends(get_tenant_db)
    ):
        try:
            check_and_increment(db, tenant_id, "exports", tier="basic")
        except UsageLimitExceeded as e:
            raise HTTPException(429, detail=str(e))

        # ... do the export
"""

import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Integer, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core.database import Base

logger = logging.getLogger(__name__)


# ============================================================
# PLAN LIMITS DEFINITION
# WHY: Single source of truth for what each tier allows.
#      Add new limit types here. Business logic never hardcodes limits.
# ============================================================

PLAN_LIMITS: Dict[str, Dict[str, int]] = {
    "basic": {
        "api_calls":        1_000,   # Per month
        "exports":          10,      # Per month
        "ai_generations":   50,      # Per month
        "social_posts":     20,      # Per month
        "projects":         5,       # Total (lifetime limit)
        "team_members":     1,       # Total
    },
    "pro": {
        "api_calls":        10_000,
        "exports":          100,
        "ai_generations":   500,
        "social_posts":     200,
        "projects":         25,
        "team_members":     5,
    },
    "enterprise": {
        "api_calls":        -1,      # -1 = unlimited
        "exports":          -1,
        "ai_generations":   -1,
        "social_posts":     -1,
        "projects":         -1,
        "team_members":     -1,
    },
}

# Which limits reset monthly vs. are lifetime totals
MONTHLY_LIMITS = {"api_calls", "exports", "ai_generations", "social_posts"}
LIFETIME_LIMITS = {"projects", "team_members"}


# ============================================================
# EXCEPTION
# ============================================================

class UsageLimitExceeded(Exception):
    """Raised when tenant hits a usage limit."""
    def __init__(self, tenant_id: str, feature: str, limit: int, current: int, tier: str):
        self.tenant_id = tenant_id
        self.feature = feature
        self.limit = limit
        self.current = current
        self.tier = tier
        super().__init__(
            f"Usage limit reached: {feature} ({current}/{limit} for {tier} tier). "
            f"Upgrade your plan at /pricing"
        )


# ============================================================
# DATABASE MODEL - usage_counters table
# WHY: Persistent tracking survives restarts.
#      One row per tenant+feature+period combination.
# ============================================================

class UsageCounter(Base):
    """
    Tracks usage count per tenant per feature per time period.

    period_type: "monthly" | "lifetime"
    period_key:  "2026-02" for monthly, "all" for lifetime
    """
    __tablename__ = "usage_counters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    feature = Column(String(128), nullable=False, index=True,
                     comment="Feature being tracked: api_calls, exports, etc.")
    period_type = Column(String(32), nullable=False,
                         comment="monthly | lifetime")
    period_key = Column(String(16), nullable=False,
                        comment="YYYY-MM for monthly, 'all' for lifetime")
    count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One row per tenant+feature+period
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature", "period_key",
                         name="uq_usage_counter"),
    )

    def __repr__(self):
        return (
            f"<UsageCounter tenant={self.tenant_id} feature={self.feature} "
            f"period={self.period_key} count={self.count}>"
        )


# ============================================================
# CORE FUNCTIONS
# ============================================================

def get_current_period_key(feature: str) -> str:
    """
    Get the period key for a feature.
    Monthly features: "2026-02"
    Lifetime features: "all"
    """
    if feature in MONTHLY_LIMITS:
        return datetime.utcnow().strftime("%Y-%m")
    return "all"


def get_period_type(feature: str) -> str:
    """Returns "monthly" or "lifetime" for a feature."""
    return "monthly" if feature in MONTHLY_LIMITS else "lifetime"


def get_current_count(db: Session, tenant_id: str, feature: str) -> int:
    """Get current usage count for tenant+feature in current period."""
    period_key = get_current_period_key(feature)

    counter = db.query(UsageCounter).filter(
        UsageCounter.tenant_id == tenant_id,
        UsageCounter.feature == feature,
        UsageCounter.period_key == period_key,
    ).first()

    return counter.count if counter else 0


def get_limit_for_tier(tier: str, feature: str) -> int:
    """
    Get the limit for a feature+tier combo.
    Returns -1 for unlimited.
    Returns 0 if feature not in tier's limits (denied).
    """
    tier_limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["basic"])
    return tier_limits.get(feature, 0)


def check_limit(
    db: Session,
    tenant_id: str,
    feature: str,
    tier: str = "pro",
    tenant_config_overrides: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Check if tenant is within their usage limit for a feature.

    Does NOT increment the counter. Call increment_usage() separately
    if you want to count the operation.

    Args:
        db: Database session
        tenant_id: Tenant to check
        feature: Feature name (must be in PLAN_LIMITS)
        tier: Tenant's plan tier
        tenant_config_overrides: Per-tenant limit overrides from tenant.config_overrides

    Returns:
        {
            "allowed": True,
            "current": 45,
            "limit": 1000,
            "remaining": 955,
            "period": "2026-02"
        }

    Raises:
        UsageLimitExceeded if over limit
    """
    limit = get_limit_for_tier(tier, feature)

    # Check per-tenant override
    if tenant_config_overrides:
        override_limits = tenant_config_overrides.get("usage_limits", {})
        if feature in override_limits:
            limit = override_limits[feature]
            logger.debug(f"Using override limit for tenant={tenant_id} feature={feature}: {limit}")

    # -1 = unlimited
    if limit == -1:
        return {
            "allowed": True,
            "current": 0,
            "limit": -1,
            "remaining": -1,
            "period": get_current_period_key(feature),
            "unlimited": True,
        }

    current = get_current_count(db, tenant_id, feature)
    period_key = get_current_period_key(feature)

    if current >= limit:
        logger.warning(
            f"Usage limit hit: tenant={tenant_id} feature={feature} "
            f"count={current}/{limit} tier={tier}"
        )
        raise UsageLimitExceeded(
            tenant_id=tenant_id,
            feature=feature,
            limit=limit,
            current=current,
            tier=tier,
        )

    return {
        "allowed": True,
        "current": current,
        "limit": limit,
        "remaining": limit - current,
        "period": period_key,
    }


def increment_usage(
    db: Session,
    tenant_id: str,
    feature: str,
    amount: int = 1,
) -> int:
    """
    Increment usage counter for tenant+feature.
    Creates the row if it doesn't exist.
    Returns new count.

    WHY: Separate from check_limit() so we can check-then-act-then-increment.
         Don't increment if the operation fails.
    """
    period_key = get_current_period_key(feature)
    period_type = get_period_type(feature)

    counter = db.query(UsageCounter).filter(
        UsageCounter.tenant_id == tenant_id,
        UsageCounter.feature == feature,
        UsageCounter.period_key == period_key,
    ).first()

    if not counter:
        counter = UsageCounter(
            tenant_id=tenant_id,
            feature=feature,
            period_type=period_type,
            period_key=period_key,
            count=0,
        )
        db.add(counter)

    counter.count += amount
    counter.last_updated = datetime.utcnow()
    db.commit()

    logger.debug(f"Usage incremented: tenant={tenant_id} feature={feature} count={counter.count}")
    return counter.count


def check_and_increment(
    db: Session,
    tenant_id: str,
    feature: str,
    tier: str = "pro",
    tenant_config_overrides: Optional[dict] = None,
    amount: int = 1,
) -> Dict[str, Any]:
    """
    Atomic check + increment. The most common usage pattern.

    Raises UsageLimitExceeded before incrementing if at limit.
    Returns usage info after incrementing.

    Usage:
        try:
            usage = check_and_increment(db, tenant_id, "api_calls", tier="basic")
        except UsageLimitExceeded as e:
            raise HTTPException(429, detail=str(e))
    """
    # Check first (raises if over limit)
    status_info = check_limit(db, tenant_id, feature, tier, tenant_config_overrides)

    # Only increment if check passed
    new_count = increment_usage(db, tenant_id, feature, amount)

    return {
        **status_info,
        "current": new_count,
        "remaining": max(0, status_info["limit"] - new_count) if status_info.get("limit", -1) != -1 else -1,
    }


def get_usage_summary(db: Session, tenant_id: str, tier: str = "pro") -> Dict[str, Any]:
    """
    Get all usage stats for a tenant. Used in dashboard.

    Returns current counts vs limits for all tracked features.
    """
    summary = {}
    tier_limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["basic"])

    for feature, limit in tier_limits.items():
        current = get_current_count(db, tenant_id, feature)
        summary[feature] = {
            "current": current,
            "limit": limit,
            "unlimited": limit == -1,
            "remaining": -1 if limit == -1 else max(0, limit - current),
            "pct_used": 0 if limit <= 0 else round(current / limit * 100, 1),
            "period": get_current_period_key(feature),
        }

    return {
        "tenant_id": tenant_id,
        "tier": tier,
        "usage": summary,
    }


# ============================================================
# FASTAPI MIDDLEWARE for per-request usage tracking
# WHY: Automatic api_calls tracking without adding to every route
# ============================================================

async def usage_tracking_middleware(request, call_next):
    """
    Middleware: auto-increments api_calls counter for authenticated requests.

    Add to app in main.py:
        app.middleware("http")(usage_tracking_middleware)

    Skip paths: /health, /docs, /openapi.json, /api/webhooks/
    """
    # Paths that don't count as "API calls" for billing
    skip_prefixes = ["/health", "/docs", "/openapi.json", "/api/webhooks/",
                     "/api/analytics/", "/favicon"]

    should_skip = any(request.url.path.startswith(p) for p in skip_prefixes)

    response = await call_next(request)

    if not should_skip and response.status_code < 400:
        # Only count successful requests
        # Get tenant context (set by tenant_middleware)
        from core.tenancy import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        if tenant_id:
            try:
                db = SessionLocal()
                try:
                    increment_usage(db, tenant_id, "api_calls")
                finally:
                    db.close()
            except Exception as e:
                # Never fail the request due to usage tracking error
                logger.warning(f"Usage tracking failed (non-fatal): {e}")

    return response


# Import SessionLocal here (after Base is defined)
from core.database import SessionLocal
