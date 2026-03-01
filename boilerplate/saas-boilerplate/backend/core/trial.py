"""
trial.py - Trial Subscription Management
==========================================

WHY: Tracks Stripe trial state per user so the platform knows
     whether a user is in trial, converted, or expired — without
     hitting Stripe on every request.

FLOW:
  POST /api/trial/start
      ↓
  stripe.create_trial_subscription() → Stripe subscription (trialing)
      ↓
  start_trial() → TrialRecord in DB
      ↓
  Stripe webhook: subscription.updated (trialing → active)
      ↓
  mark_trial_converted()

Statuses: "active" | "converted" | "expired" | "cancelled"
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)


class TrialRecord(Base):
    __tablename__ = "trial_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    trial_days = Column(Integer, nullable=False, default=14)
    trial_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    trial_end_at = Column(DateTime, nullable=False, index=True)
    stripe_subscription_id = Column(String(128), nullable=True)
    status = Column(String(16), nullable=False, default="active")
    converted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def start_trial(
    db: Session,
    auth0_user_id: str,
    tenant_id: str,
    trial_days: int = 14,
    stripe_subscription_id: Optional[str] = None,
) -> TrialRecord:
    """
    Create a TrialRecord. Raises ValueError if a trial already exists for this user.
    trial_end_at = trial_start + trial_days days.
    """
    if db.query(TrialRecord).filter(
        TrialRecord.auth0_user_id == auth0_user_id
    ).first():
        raise ValueError(f"Trial already exists for {auth0_user_id}")

    now = datetime.utcnow()
    record = TrialRecord(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        trial_days=trial_days,
        trial_start=now,
        trial_end_at=now + timedelta(days=trial_days),
        stripe_subscription_id=stripe_subscription_id,
        status="active",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(f"Trial started for {auth0_user_id}: {trial_days} days")
    return record


def get_trial(db: Session, auth0_user_id: str) -> Optional[TrialRecord]:
    """Return TrialRecord for user, or None."""
    return db.query(TrialRecord).filter(
        TrialRecord.auth0_user_id == auth0_user_id
    ).first()


def is_trial_active(db: Session, auth0_user_id: str) -> bool:
    """
    True if trial status == "active" AND trial_end_at > now.
    Both conditions must hold.
    """
    record = get_trial(db, auth0_user_id)
    if not record or record.status != "active":
        return False
    return record.trial_end_at > datetime.utcnow()


def mark_trial_converted(db: Session, auth0_user_id: str) -> TrialRecord:
    """Called when Stripe subscription transitions trialing → active."""
    record = get_trial(db, auth0_user_id)
    if not record:
        raise ValueError(f"No trial found for {auth0_user_id}")
    record.status = "converted"
    record.converted_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


def mark_trial_expired(db: Session, auth0_user_id: str) -> TrialRecord:
    """Called when Stripe subscription deleted while in trial state."""
    record = get_trial(db, auth0_user_id)
    if not record:
        raise ValueError(f"No trial found for {auth0_user_id}")
    record.status = "expired"
    db.commit()
    db.refresh(record)
    return record


def get_expiring_trials(db: Session, days_ahead: int = 3) -> List[TrialRecord]:
    """
    Return active trials ending within the next `days_ahead` days.
    Used by background jobs to send expiry warning emails.
    """
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_ahead)
    return db.query(TrialRecord).filter(
        TrialRecord.status == "active",
        TrialRecord.trial_end_at >= now,
        TrialRecord.trial_end_at <= cutoff,
    ).all()
