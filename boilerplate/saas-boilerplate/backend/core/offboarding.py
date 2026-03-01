"""
offboarding.py - User Offboarding (Cancellation) Flow
=======================================================

WHY: Records why a user is leaving and drives cancellation analytics.
     Side effects (Stripe cancel, cancellation email) live in the API
     layer — this module is pure DB state management.

REASONS: too_expensive | missing_feature | not_using |
         switching_product | other
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)

CANCELLATION_REASONS = (
    "too_expensive",
    "missing_feature",
    "not_using",
    "switching_product",
    "other",
)


class OffboardingRecord(Base):
    __tablename__ = "offboarding_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    cancellation_reason = Column(String(64), nullable=False)
    cancellation_feedback = Column(Text, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=True)
    stripe_subscription_id = Column(String(128), nullable=True)
    initiated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


def initiate_offboarding(
    db: Session,
    auth0_user_id: str,
    tenant_id: str,
    reason: str,
    stripe_subscription_id: Optional[str] = None,
    feedback: Optional[str] = None,
    cancel_at_period_end: bool = True,
) -> OffboardingRecord:
    """
    Create an OffboardingRecord.

    Raises ValueError if:
    - reason is not in CANCELLATION_REASONS
    - an active (not yet completed) offboarding already exists

    NOTE: Allows re-initiation after a previous offboarding was completed.
    Side effects (Stripe cancel, email) happen in the API layer.
    """
    if reason not in CANCELLATION_REASONS:
        raise ValueError(
            f"Invalid reason '{reason}'. Must be one of: {CANCELLATION_REASONS}"
        )

    # Only block on an ACTIVE (not completed) offboarding
    if db.query(OffboardingRecord).filter(
        OffboardingRecord.auth0_user_id == auth0_user_id,
        OffboardingRecord.completed_at.is_(None),
    ).first():
        raise ValueError(f"Offboarding already active for {auth0_user_id}")

    record = OffboardingRecord(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        cancellation_reason=reason,
        cancellation_feedback=feedback,
        cancel_at_period_end=cancel_at_period_end,
        stripe_subscription_id=stripe_subscription_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(f"Offboarding initiated: {auth0_user_id} reason={reason}")
    return record


def complete_offboarding(db: Session, auth0_user_id: str) -> OffboardingRecord:
    """
    Mark the active offboarding as complete (sets completed_at).
    Called after Stripe cancellation is confirmed.
    """
    record = db.query(OffboardingRecord).filter(
        OffboardingRecord.auth0_user_id == auth0_user_id,
        OffboardingRecord.completed_at.is_(None),
    ).first()
    if not record:
        raise ValueError(f"No active offboarding found for {auth0_user_id}")
    record.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def get_offboarding_record(
    db: Session, auth0_user_id: str
) -> Optional[OffboardingRecord]:
    """Return the most recent OffboardingRecord for a user, or None."""
    return (
        db.query(OffboardingRecord)
        .filter(OffboardingRecord.auth0_user_id == auth0_user_id)
        .order_by(OffboardingRecord.initiated_at.desc())
        .first()
    )
