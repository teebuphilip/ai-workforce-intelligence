"""
legal_consent.py - Terms & Privacy Consent Management
=======================================================

WHY: Legal compliance requires proof that each user accepted specific
     versions of the ToS and Privacy Policy. Without this:
     - Cannot prove consent if challenged in court or by a regulator
     - No mechanism to force re-acceptance after policy updates
     - No audit trail (IP, timestamp, user agent)

CAPABILITIES:
    #26: Terms Version Tracking  — LegalDocVersion table, admin bump endpoint
    #27: Privacy Consent Logging — UserConsent upsert per (user, doc_type)
    #28: Re-Acceptance Enforcement — requires_reacceptance() + HTTP 451 depend
    #29: Consent Audit Log        — ConsentAuditLog with IP + UA + timestamp

HOW:
    set_current_version()  — admin bumps current doc version (atomic swap)
    record_consent()       — upsert UserConsent + append ConsentAuditLog
    requires_reacceptance() — check if user's accepted version is stale
    require_fresh_consent  — FastAPI Depends raising HTTP 451 when stale
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException

from core.database import Base, get_db
from core.rbac import get_current_user

logger = logging.getLogger(__name__)

DOC_TYPE_TERMS = "terms"
DOC_TYPE_PRIVACY = "privacy"
_VALID_DOC_TYPES = (DOC_TYPE_TERMS, DOC_TYPE_PRIVACY)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class LegalDocVersion(Base):
    """
    Tracks the current version of each legal document.
    One row per doc_type has is_current=True at any time.
    set_current_version() atomically swaps the current row.
    """
    __tablename__ = "legal_doc_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_type = Column(String(32), nullable=False, index=True)
    # "terms" | "privacy"
    version = Column(String(32), nullable=False)
    # Semantic string: "2.0", "2026-02-01". Not an int to allow date-style versions.
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    effective_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserConsent(Base):
    """
    One row per (auth0_user_id, doc_type). Holds the LATEST accepted version.
    Upserted by record_consent() — history lives in ConsentAuditLog.
    """
    __tablename__ = "user_consents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    doc_type = Column(String(32), nullable=False, index=True)
    accepted_version = Column(String(32), nullable=False)
    accepted_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ConsentAuditLog(Base):
    """
    Immutable audit trail — one row per consent event (including re-acceptances).
    Stores IP address and user agent for GDPR/legal evidence.
    """
    __tablename__ = "consent_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    doc_type = Column(String(32), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    client_ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------

def get_current_version(db: Session, doc_type: str) -> Optional[LegalDocVersion]:
    """Return the current LegalDocVersion for doc_type, or None if not configured."""
    return db.query(LegalDocVersion).filter(
        LegalDocVersion.doc_type == doc_type,
        LegalDocVersion.is_current == True,
    ).first()


def set_current_version(
    db: Session,
    doc_type: str,
    version: str,
) -> LegalDocVersion:
    """
    Admin: set the current version for a legal document.
    Atomically swaps is_current: old row → False, new row → True.
    After this call, all users who accepted a prior version need to re-accept.

    Raises ValueError for invalid doc_type or empty version.
    """
    if doc_type not in _VALID_DOC_TYPES:
        raise ValueError(f"Invalid doc_type '{doc_type}'. Must be one of {_VALID_DOC_TYPES}")
    if not version or not version.strip():
        raise ValueError("version cannot be empty")

    # Atomically deactivate all current rows for this doc_type
    db.query(LegalDocVersion).filter(
        LegalDocVersion.doc_type == doc_type,
        LegalDocVersion.is_current == True,
    ).update({"is_current": False})
    db.flush()

    # If this version was previously stored, reactivate it
    existing = db.query(LegalDocVersion).filter(
        LegalDocVersion.doc_type == doc_type,
        LegalDocVersion.version == version,
    ).first()
    if existing:
        existing.is_current = True
        existing.effective_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        logger.info(f"Legal doc version reactivated: {doc_type} → {version}")
        return existing

    new_v = LegalDocVersion(
        doc_type=doc_type,
        version=version,
        is_current=True,
        effective_at=datetime.utcnow(),
    )
    db.add(new_v)
    db.commit()
    db.refresh(new_v)
    logger.info(f"Legal doc version updated: {doc_type} → {version}")
    return new_v


# ---------------------------------------------------------------------------
# Consent recording
# ---------------------------------------------------------------------------

def record_consent(
    db: Session,
    auth0_user_id: str,
    doc_type: str,
    version: str,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> UserConsent:
    """
    Upsert the user's accepted version for doc_type, then write audit log.

    UserConsent: one row per (user, doc_type) — updated in place on re-acceptance.
    ConsentAuditLog: always appended — immutable record of every consent event.
    """
    consent = db.query(UserConsent).filter(
        UserConsent.auth0_user_id == auth0_user_id,
        UserConsent.doc_type == doc_type,
    ).first()

    if consent:
        consent.accepted_version = version
        consent.accepted_at = datetime.utcnow()
        db.flush()
    else:
        consent = UserConsent(
            auth0_user_id=auth0_user_id,
            doc_type=doc_type,
            accepted_version=version,
        )
        db.add(consent)
        db.flush()

    # Always append audit log entry
    db.add(ConsentAuditLog(
        auth0_user_id=auth0_user_id,
        doc_type=doc_type,
        version=version,
        client_ip=client_ip,
        user_agent=user_agent,
    ))

    db.commit()
    db.refresh(consent)
    logger.info(f"Consent recorded: {auth0_user_id} accepted {doc_type} v{version}")
    return consent


def get_user_consent(
    db: Session,
    auth0_user_id: str,
    doc_type: str,
) -> Optional[UserConsent]:
    """Return the UserConsent row for (user, doc_type), or None."""
    return db.query(UserConsent).filter(
        UserConsent.auth0_user_id == auth0_user_id,
        UserConsent.doc_type == doc_type,
    ).first()


# ---------------------------------------------------------------------------
# Re-acceptance enforcement
# ---------------------------------------------------------------------------

def requires_reacceptance(db: Session, auth0_user_id: str) -> bool:
    """
    True if user must re-accept any legal document.
    Returns False if no versions are configured (fresh deploy — don't block).
    Returns True if the user has no consent row, or if their accepted version
    differs from the current version for ANY configured doc type.
    """
    current_tos = get_current_version(db, DOC_TYPE_TERMS)
    current_priv = get_current_version(db, DOC_TYPE_PRIVACY)

    # No versions configured → no enforcement
    if not current_tos and not current_priv:
        return False

    user_tos = get_user_consent(db, auth0_user_id, DOC_TYPE_TERMS)
    user_priv = get_user_consent(db, auth0_user_id, DOC_TYPE_PRIVACY)

    if current_tos and (not user_tos or user_tos.accepted_version != current_tos.version):
        return True
    if current_priv and (not user_priv or user_priv.accepted_version != current_priv.version):
        return True

    return False


def get_consent_status(db: Session, auth0_user_id: str) -> Dict:
    """
    Return a structured status dict used by the /api/legal/consent/status endpoint.
    Frontend ConsentGate reads this on mount to decide whether to show the modal.
    """
    current_tos = get_current_version(db, DOC_TYPE_TERMS)
    current_priv = get_current_version(db, DOC_TYPE_PRIVACY)
    user_tos = get_user_consent(db, auth0_user_id, DOC_TYPE_TERMS)
    user_priv = get_user_consent(db, auth0_user_id, DOC_TYPE_PRIVACY)

    tos_current = bool(
        current_tos and user_tos
        and user_tos.accepted_version == current_tos.version
    )
    priv_current = bool(
        current_priv and user_priv
        and user_priv.accepted_version == current_priv.version
    )

    return {
        "requires_reacceptance": requires_reacceptance(db, auth0_user_id),
        "terms": {
            "current_version": current_tos.version if current_tos else None,
            "user_accepted_version": user_tos.accepted_version if user_tos else None,
            "is_current": tos_current,
        },
        "privacy": {
            "current_version": current_priv.version if current_priv else None,
            "user_accepted_version": user_priv.accepted_version if user_priv else None,
            "is_current": priv_current,
        },
    }


async def require_fresh_consent(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    FastAPI dependency — raises HTTP 451 (Unavailable For Legal Reasons)
    if the authenticated user must re-accept any current legal document.

    DO NOT apply to:
      - POST /api/legal/consent (this IS the fix — would cause circular block)
      - GET  /api/legal/consent/status
      - GET  /api/legal/versions
      - Any auth endpoints
    """
    if requires_reacceptance(db, user["sub"]):
        raise HTTPException(
            status_code=451,
            detail={
                "code": "CONSENT_REQUIRED",
                "message": "You must accept the updated Terms and/or Privacy Policy.",
                "requires_reacceptance": True,
            },
        )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def get_audit_log(
    db: Session,
    auth0_user_id: str,
    limit: int = 50,
) -> List[ConsentAuditLog]:
    """Return consent audit log for a user, most recent first."""
    return (
        db.query(ConsentAuditLog)
        .filter(ConsentAuditLog.auth0_user_id == auth0_user_id)
        .order_by(ConsentAuditLog.occurred_at.desc())
        .limit(limit)
        .all()
    )
