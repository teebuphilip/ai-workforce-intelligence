"""
account_closure.py - Account Closure & Data Purge
===================================================

WHY: GDPR-aligned account deletion with a 30-day grace period.

FLOW:
  initiate_closure()
    → Tenant.is_active = False  (soft disable — auth checks fail)
    → revoke_all_entitlements() (soft delete — keeps audit trail)
    → AccountClosure row with purge_at = now + 30 days

  [30 days later — background job or admin action]

  execute_purge()
    → Hard-delete all user data rows
    → AICostLog is PRESERVED (financial audit trail)
    → AccountClosure.status = "purged"

RECOVERY:
  cancel_closure() — reactivates tenant + sets status="reactivated"
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import Session

from core.database import Base
from core.tenancy import Tenant  # Tenant.id is the String(64) primary key

logger = logging.getLogger(__name__)

PURGE_DELAY_DAYS = 30


class AccountClosure(Base):
    __tablename__ = "account_closures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    reason = Column(String(64), nullable=True)
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    purge_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(16), nullable=False, default="pending_purge")
    # "pending_purge" | "purged" | "reactivated"
    purged_at = Column(DateTime, nullable=True)


def initiate_closure(
    db: Session,
    auth0_user_id: str,
    tenant_id: str,
    reason: Optional[str] = None,
) -> AccountClosure:
    """
    Initiate account closure:
    1. Raises ValueError if closure already pending
    2. Sets Tenant.is_active = False
    3. Revokes all entitlements (soft delete)
    4. Creates AccountClosure with purge_at = now + 30 days
    """
    if db.query(AccountClosure).filter(
        AccountClosure.auth0_user_id == auth0_user_id,
        AccountClosure.status == "pending_purge",
    ).first():
        raise ValueError(f"Account closure already pending for {auth0_user_id}")

    # Soft-disable tenant (Tenant.id is the PK, not tenant_id column)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant:
        tenant.is_active = False
        db.flush()

    # Soft-revoke entitlements (sets revoked_at, keeps rows for audit)
    from core.entitlements import revoke_all_entitlements
    revoke_all_entitlements(auth0_user_id, db)  # user_id first, db second

    now = datetime.utcnow()
    closure = AccountClosure(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        reason=reason,
        requested_at=now,
        purge_at=now + timedelta(days=PURGE_DELAY_DAYS),
        status="pending_purge",
    )
    db.add(closure)
    db.commit()
    db.refresh(closure)
    logger.info(
        f"Account closure initiated for {auth0_user_id}, purge_at={closure.purge_at}"
    )
    return closure


def cancel_closure(db: Session, auth0_user_id: str) -> bool:
    """
    Cancel a pending closure.
    Sets status="reactivated" and re-activates Tenant.
    Returns True if cancelled, False if no pending closure found.
    """
    closure = db.query(AccountClosure).filter(
        AccountClosure.auth0_user_id == auth0_user_id,
        AccountClosure.status == "pending_purge",
    ).first()
    if not closure:
        return False

    closure.status = "reactivated"
    tenant = db.query(Tenant).filter(Tenant.id == closure.tenant_id).first()
    if tenant:
        tenant.is_active = True

    db.commit()
    logger.info(f"Account closure cancelled for {auth0_user_id}")
    return True


def get_closure_request(
    db: Session, auth0_user_id: str
) -> Optional[AccountClosure]:
    """Return the most recent AccountClosure for a user, or None."""
    return (
        db.query(AccountClosure)
        .filter(AccountClosure.auth0_user_id == auth0_user_id)
        .order_by(AccountClosure.requested_at.desc())
        .first()
    )


def get_pending_purges(db: Session) -> List[AccountClosure]:
    """
    Return all closures where purge_at <= now and status="pending_purge".
    Used by scheduled background jobs.
    """
    return db.query(AccountClosure).filter(
        AccountClosure.status == "pending_purge",
        AccountClosure.purge_at <= datetime.utcnow(),
    ).all()


def execute_purge(db: Session, auth0_user_id: str) -> Dict[str, Any]:
    """
    Hard-delete all user data rows. AICostLog is preserved (financial audit trail).
    UsageCounter is deleted by tenant_id (not auth0_user_id) since it's tenant-keyed.
    Returns a dict of {table: row_count_deleted}.
    """
    from core.entitlements import UserEntitlement
    from core.usage_limits import UsageCounter
    from core.activation import ActivationEvent
    from core.onboarding import OnboardingState
    from core.trial import TrialRecord
    from core.offboarding import OffboardingRecord
    from core.legal_consent import UserConsent, ConsentAuditLog

    closure = get_closure_request(db, auth0_user_id)
    tenant_id = closure.tenant_id if closure else auth0_user_id  # fallback

    summary: Dict[str, int] = {}

    summary["user_entitlements"] = (
        db.query(UserEntitlement)
        .filter(UserEntitlement.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    # UsageCounter is keyed by tenant_id, not auth0_user_id
    summary["usage_counters"] = (
        db.query(UsageCounter)
        .filter(UsageCounter.tenant_id == tenant_id)
        .delete(synchronize_session=False)
    )
    summary["activation_events"] = (
        db.query(ActivationEvent)
        .filter(ActivationEvent.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    summary["onboarding_states"] = (
        db.query(OnboardingState)
        .filter(OnboardingState.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    summary["trial_records"] = (
        db.query(TrialRecord)
        .filter(TrialRecord.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    summary["offboarding_records"] = (
        db.query(OffboardingRecord)
        .filter(OffboardingRecord.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    summary["user_consents"] = (
        db.query(UserConsent)
        .filter(UserConsent.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    summary["consent_audit_logs"] = (
        db.query(ConsentAuditLog)
        .filter(ConsentAuditLog.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )

    from core.fraud import FraudEvent, AccountLockout

    summary["fraud_events"] = (
        db.query(FraudEvent)
        .filter(FraudEvent.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )
    summary["account_lockouts"] = (
        db.query(AccountLockout)
        .filter(AccountLockout.auth0_user_id == auth0_user_id)
        .delete(synchronize_session=False)
    )

    # Ensure tenant stays disabled
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant:
        tenant.is_active = False

    # Mark closure as purged
    if closure and closure.status == "pending_purge":
        closure.status = "purged"
        closure.purged_at = datetime.utcnow()

    db.commit()
    logger.info(f"Purge executed for {auth0_user_id}: {summary}")
    return summary
