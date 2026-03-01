"""
activation.py - User Activation Event Tracking
================================================

WHY: Tracks when users first complete a meaningful action ("activate").
     Powers activation rate metrics in the admin dashboard and triggers
     lifecycle automations (e.g. skip trial-expired email for activated users).

HOW: record_activation() is idempotent — only the FIRST occurrence of each
     event_name per user is stored. Subsequent calls return the existing record.

SIDE EFFECT: On first record, fires a GA4 event via analytics_lib (try/except,
             non-fatal — never blocks the primary DB write).
"""

import json
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)

ACTIVATION_EVENTS = (
    "first_ai_generation",
    "first_listing_created",
    "first_api_call",
    "profile_completed",
)


class ActivationEvent(Base):
    __tablename__ = "activation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    event_name = Column(String(128), nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    event_metadata = Column(Text, nullable=True)  # JSON string for extra context


def record_activation(
    db: Session,
    auth0_user_id: str,
    tenant_id: str,
    event_name: str,
    metadata: Optional[dict] = None,
) -> ActivationEvent:
    """
    Record an activation event.
    Idempotent — only stores first occurrence per event_name per user.
    Returns existing event if already recorded.

    Side effect: fires GA4 event via analytics_lib (non-fatal try/except).
    """
    existing = db.query(ActivationEvent).filter(
        ActivationEvent.auth0_user_id == auth0_user_id,
        ActivationEvent.event_name == event_name,
    ).first()
    if existing:
        return existing

    event = ActivationEvent(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        event_name=event_name,
        occurred_at=datetime.utcnow(),
        event_metadata=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"Activation event recorded: {auth0_user_id} → {event_name}")

    # Non-fatal GA4 side effect
    try:
        import os
        from analytics_lib import load_analytics_lib
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "analytics_config.json"
        )
        analytics = load_analytics_lib(config_path)
        analytics.track_event(
            event_name=event_name,
            user_id=auth0_user_id,
            event_params=metadata or {},
        )
    except Exception as e:
        logger.debug(f"Analytics side-effect failed (non-fatal): {e}")

    return event


def is_activated(db: Session, auth0_user_id: str) -> bool:
    """True if any ActivationEvent exists for this user."""
    return (
        db.query(ActivationEvent)
        .filter(ActivationEvent.auth0_user_id == auth0_user_id)
        .first()
    ) is not None


def get_activation_events(
    db: Session, auth0_user_id: str
) -> List[ActivationEvent]:
    """Return all activation events for a user, oldest first."""
    return (
        db.query(ActivationEvent)
        .filter(ActivationEvent.auth0_user_id == auth0_user_id)
        .order_by(ActivationEvent.occurred_at.asc())
        .all()
    )


def get_first_activation(
    db: Session, auth0_user_id: str
) -> Optional[ActivationEvent]:
    """Return the earliest activation event for a user."""
    return (
        db.query(ActivationEvent)
        .filter(ActivationEvent.auth0_user_id == auth0_user_id)
        .order_by(ActivationEvent.occurred_at.asc())
        .first()
    )
