"""
purchase_delivery.py - Purchase Delivery via Entitlements
==========================================================

WHY: Platform Rule #2 — every capability needs a single adapter.
     This module handles purchase fulfillment. When a buyer pays for a listing,
     this module records the purchase and grants them an entitlement so the
     existing entitlement guard system controls access.

HOW:
    1. Payment succeeds (Stripe webhook or direct call)
    2. Call deliver_purchase() — creates PurchaseRecord + UserEntitlement
    3. Buyer now has entitlement "listing:{listing_id}"
    4. Gate access with has_purchased() or has_entitlement() from entitlements.py

USAGE:
    from core.purchase_delivery import deliver_purchase, has_purchased

    # After Stripe payment_intent.succeeded webhook:
    record = deliver_purchase(
        db=db,
        buyer_auth0_id="auth0|abc123",
        listing_id=42,
        tenant_id="acme",
        stripe_payment_intent_id="pi_3xxx",
    )

    # Check access:
    if has_purchased(db, "auth0|abc123", 42):
        # allow download / feature unlock
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session

from core.database import Base
from core.entitlements import UserEntitlement
from core.listings import get_listing

logger = logging.getLogger(__name__)


# ============================================================
# MODEL
# ============================================================

class PurchaseRecord(Base):
    """
    One row per completed purchase.

    Records who bought what, when, and via which payment.
    The actual access control is enforced by the UserEntitlement row
    that deliver_purchase() writes alongside this record.
    """
    __tablename__ = "purchase_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Seller's tenant
    tenant_id = Column(String(64), nullable=False, index=True)

    # What was purchased
    listing_id = Column(Integer, nullable=False, index=True)

    # Who bought it
    buyer_auth0_id = Column(String(128), nullable=False, index=True)

    # Payment reference (nullable — allows manual / test deliveries without Stripe)
    stripe_payment_intent_id = Column(String(128), nullable=True)

    # Entitlement key written to UserEntitlement (e.g. "listing:42")
    entitlement_key = Column(String(128), nullable=False)

    # Timestamp when access was actually granted
    delivered_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<PurchaseRecord id={self.id} buyer={self.buyer_auth0_id} "
            f"listing={self.listing_id} key={self.entitlement_key}>"
        )


# ============================================================
# CORE FUNCTIONS
# ============================================================

def deliver_purchase(
    db: Session,
    buyer_auth0_id: str,
    listing_id: int,
    tenant_id: str,
    stripe_payment_intent_id: Optional[str] = None,
) -> PurchaseRecord:
    """
    Fulfill a purchase by creating a PurchaseRecord and a UserEntitlement.

    Steps:
      1. Verify the listing exists and belongs to tenant_id
      2. Reject duplicate purchases (idempotency guard)
      3. Write PurchaseRecord row
      4. Write UserEntitlement row (entitlement = "listing:{listing_id}")
      5. Set delivered_at = utcnow()

    Args:
        db: SQLAlchemy session
        buyer_auth0_id: Auth0 user ID of the buyer
        listing_id: ID of the listing being purchased
        tenant_id: Tenant that owns the listing
        stripe_payment_intent_id: Optional Stripe payment reference

    Returns:
        The created PurchaseRecord

    Raises:
        ValueError: If listing not found, or buyer already purchased this listing
    """
    # 1. Verify listing exists in this tenant
    listing = get_listing(db, listing_id, tenant_id=tenant_id)
    if listing is None:
        raise ValueError(
            f"Listing {listing_id} not found for tenant '{tenant_id}'"
        )

    # 2. Idempotency guard — reject duplicates
    already_purchased = has_purchased(db, buyer_auth0_id, listing_id)
    if already_purchased:
        raise ValueError(
            f"Buyer '{buyer_auth0_id}' has already purchased listing {listing_id}"
        )

    now = datetime.now(timezone.utc)
    entitlement_key = f"listing:{listing_id}"

    # 3. Write PurchaseRecord
    record = PurchaseRecord(
        tenant_id=tenant_id,
        listing_id=listing_id,
        buyer_auth0_id=buyer_auth0_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        entitlement_key=entitlement_key,
        delivered_at=now,
    )
    db.add(record)

    # 4. Write UserEntitlement (reuses existing entitlements system)
    entitlement = UserEntitlement(
        auth0_user_id=buyer_auth0_id,
        stripe_customer_id=None,
        stripe_product_id=stripe_payment_intent_id or entitlement_key,
        entitlement=entitlement_key,
        granted_at=now,
    )
    db.add(entitlement)

    db.commit()
    db.refresh(record)

    logger.info(
        f"Purchase delivered: buyer={buyer_auth0_id} listing={listing_id} "
        f"entitlement={entitlement_key}"
    )
    return record


def has_purchased(
    db: Session,
    buyer_auth0_id: str,
    listing_id: int,
) -> bool:
    """
    Check whether a buyer has purchased a specific listing.

    Args:
        db: SQLAlchemy session
        buyer_auth0_id: Auth0 user ID to check
        listing_id: Listing ID to check

    Returns:
        True if a PurchaseRecord exists for this buyer + listing
    """
    record = (
        db.query(PurchaseRecord)
        .filter(
            PurchaseRecord.buyer_auth0_id == buyer_auth0_id,
            PurchaseRecord.listing_id == listing_id,
        )
        .first()
    )
    return record is not None


def get_purchases_for_buyer(
    db: Session,
    buyer_auth0_id: str,
) -> List[PurchaseRecord]:
    """
    Return all purchases made by a buyer, newest first.

    Args:
        db: SQLAlchemy session
        buyer_auth0_id: Auth0 user ID of the buyer

    Returns:
        List of PurchaseRecord rows
    """
    return (
        db.query(PurchaseRecord)
        .filter(PurchaseRecord.buyer_auth0_id == buyer_auth0_id)
        .order_by(PurchaseRecord.created_at.desc())
        .all()
    )
