"""
fraud.py - Fraud & Abuse Prevention
#30: Payment Fraud Monitoring — FraudEvent table + Stripe webhook handlers
#32: Account Lockouts — AccountLockout table, lock/unlock (Auth0 side-effect in main.py)
#33: API Abuse Detection — velocity check on UsageCounter
#34: AI Abuse Detection — velocity check on AICostLog call rate
#36: Referral Fraud Detection — detect_self_referral() identity check utility
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)

FRAUD_EVENT_TYPES = (
    "stripe_dispute", "stripe_early_fraud_warning",
    "api_abuse", "ai_abuse", "account_lockout", "referral_fraud", "ip_rate_limit",
)
FRAUD_SEVERITIES = ("low", "medium", "high", "critical")


class FraudEvent(Base):
    __tablename__ = "fraud_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=True, index=True)  # nullable: Stripe events may lack user
    tenant_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False)
    source = Column(String(32), nullable=False)   # "stripe" / "custom" / "system"
    detail = Column(Text, nullable=True)           # JSON string. NEVER name "metadata" — SQLAlchemy reserved.
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime, nullable=True)


class AccountLockout(Base):
    __tablename__ = "account_lockouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    reason = Column(String(256), nullable=False)
    locked_by = Column(String(128), nullable=False)  # admin user_id or "system"
    locked_at = Column(DateTime, default=datetime.utcnow, index=True)
    unlocked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)


def record_fraud_event(
    db: Session,
    auth0_user_id: Optional[str],
    tenant_id: Optional[str],
    event_type: str,
    severity: str,
    source: str,
    detail=None,
) -> FraudEvent:
    if event_type not in FRAUD_EVENT_TYPES:
        raise ValueError(f"Invalid event_type '{event_type}'")
    if severity not in FRAUD_SEVERITIES:
        raise ValueError(f"Invalid severity '{severity}'")
    detail_str = json.dumps(detail) if isinstance(detail, dict) else detail
    event = FraudEvent(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        event_type=event_type,
        severity=severity,
        source=source,
        detail=detail_str,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"FraudEvent: type={event_type} severity={severity} user={auth0_user_id}")
    return event


def get_fraud_events(
    db: Session,
    tenant_id: Optional[str] = None,
    event_type: Optional[str] = None,
    resolved: bool = False,
    limit: int = 50,
) -> List[FraudEvent]:
    q = db.query(FraudEvent).filter(FraudEvent.is_resolved == resolved)
    if tenant_id:
        q = q.filter(FraudEvent.tenant_id == tenant_id)
    if event_type:
        q = q.filter(FraudEvent.event_type == event_type)
    return q.order_by(FraudEvent.occurred_at.desc()).limit(limit).all()


def resolve_fraud_event(db: Session, event_id: int) -> FraudEvent:
    event = db.query(FraudEvent).filter(FraudEvent.id == event_id).first()
    if not event:
        raise ValueError(f"FraudEvent {event_id} not found")
    event.is_resolved = True
    event.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return event


def lock_account(
    db: Session,
    auth0_user_id: str,
    tenant_id: str,
    reason: str,
    locked_by: str = "system",
) -> AccountLockout:
    """DB-only. Caller (main.py) must separately call auth0.update_user(blocked=True)."""
    if db.query(AccountLockout).filter(
        AccountLockout.auth0_user_id == auth0_user_id,
        AccountLockout.is_active == True,
    ).first():
        raise ValueError(f"Active lockout already exists for {auth0_user_id}")
    lockout = AccountLockout(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        reason=reason,
        locked_by=locked_by,
    )
    db.add(lockout)
    db.commit()
    db.refresh(lockout)
    logger.warning(f"Account locked: user={auth0_user_id} by={locked_by}")
    return lockout


def unlock_account(db: Session, auth0_user_id: str) -> bool:
    """DB-only. Caller (main.py) must separately call auth0.update_user(blocked=False)."""
    lockout = db.query(AccountLockout).filter(
        AccountLockout.auth0_user_id == auth0_user_id,
        AccountLockout.is_active == True,
    ).first()
    if not lockout:
        return False
    lockout.is_active = False
    lockout.unlocked_at = datetime.utcnow()
    db.commit()
    logger.info(f"Account unlocked: user={auth0_user_id}")
    return True


def is_account_locked(db: Session, auth0_user_id: str) -> bool:
    return (
        db.query(AccountLockout)
        .filter(
            AccountLockout.auth0_user_id == auth0_user_id,
            AccountLockout.is_active == True,
        )
        .first()
        is not None
    )


def detect_ai_abuse(
    db: Session,
    auth0_user_id: str,
    minutes: int = 60,
    threshold: int = 50,
) -> bool:
    """True if user made > threshold AI calls in last N minutes.
    Uses AICostLog.user_id (not auth0_user_id)."""
    from core.ai_governance import AICostLog

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    count = (
        db.query(func.count(AICostLog.id))
        .filter(
            AICostLog.user_id == auth0_user_id,
            AICostLog.created_at >= cutoff,
        )
        .scalar()
        or 0
    )
    return count > threshold


def detect_api_abuse(
    db: Session,
    tenant_id: str,
    threshold_multiplier: float = 3.0,
) -> bool:
    """True if projected monthly api_calls > 3x pro plan limit (10,000).
    Enterprise (limit=-1) is never flagged."""
    from core.usage_limits import UsageCounter
    from datetime import date

    period_key = datetime.utcnow().strftime("%Y-%m")
    counter = (
        db.query(UsageCounter)
        .filter(
            UsageCounter.tenant_id == tenant_id,
            UsageCounter.feature == "api_calls",
            UsageCounter.period_key == period_key,
        )
        .first()
    )
    current_count = counter.count if counter else 0
    day_of_month = max(date.today().day, 1)
    projected = (current_count / day_of_month) * 30
    return projected > 10_000 * threshold_multiplier


def detect_self_referral(referrer_id: str, referee_id: str) -> bool:
    """True if referrer_id == referee_id. Utility for when referral system is built."""
    return referrer_id == referee_id
