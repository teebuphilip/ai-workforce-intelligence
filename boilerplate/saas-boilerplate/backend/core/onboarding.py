"""
onboarding.py - User Onboarding Flow
======================================

WHY: First-time users need a guided setup path. This module tracks
     per-user progress through 3 onboarding steps.

STEPS: profile_setup → plan_selected → integration_connected

completed_steps stored as JSON array string (Text column, same
pattern as listings.images — avoids SQLite JSON column quirks).
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)

ONBOARDING_STEPS = ("profile_setup", "plan_selected", "integration_connected")


class OnboardingState(Base):
    __tablename__ = "onboarding_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth0_user_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    completed_steps = Column(Text, nullable=False, default="[]")  # JSON array string
    is_complete = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def get_steps(self):
        """Deserialize completed_steps JSON string to list."""
        return json.loads(self.completed_steps or "[]")

    def set_steps(self, steps_list):
        """Serialize list to JSON string."""
        self.completed_steps = json.dumps(steps_list)


def get_or_create_onboarding(
    db: Session, auth0_user_id: str, tenant_id: str
) -> OnboardingState:
    """
    Get existing OnboardingState or create a new one.
    Idempotent — returns the same row on repeated calls.
    """
    existing = db.query(OnboardingState).filter(
        OnboardingState.auth0_user_id == auth0_user_id
    ).first()
    if existing:
        return existing
    state = OnboardingState(
        auth0_user_id=auth0_user_id,
        tenant_id=tenant_id,
        completed_steps="[]",
        is_complete=False,
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    logger.info(f"Created onboarding state for {auth0_user_id}")
    return state


def mark_step_complete(
    db: Session, auth0_user_id: str, step: str
) -> OnboardingState:
    """
    Mark a step complete. Raises ValueError if step is invalid or state missing.
    When all 3 steps done, sets is_complete=True and completed_at.
    """
    if step not in ONBOARDING_STEPS:
        raise ValueError(
            f"Invalid step '{step}'. Must be one of: {ONBOARDING_STEPS}"
        )
    state = db.query(OnboardingState).filter(
        OnboardingState.auth0_user_id == auth0_user_id
    ).first()
    if not state:
        raise ValueError(f"No onboarding state found for {auth0_user_id}")

    steps = state.get_steps()
    if step not in steps:
        steps.append(step)
        state.set_steps(steps)

    if all(s in steps for s in ONBOARDING_STEPS) and not state.is_complete:
        state.is_complete = True
        state.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(state)
    return state


def is_onboarding_complete(db: Session, auth0_user_id: str) -> bool:
    """Return True if all onboarding steps are complete."""
    state = db.query(OnboardingState).filter(
        OnboardingState.auth0_user_id == auth0_user_id
    ).first()
    return state.is_complete if state else False


def reset_onboarding(db: Session, auth0_user_id: str) -> OnboardingState:
    """Reset all onboarding steps. Used for testing/admin use."""
    state = db.query(OnboardingState).filter(
        OnboardingState.auth0_user_id == auth0_user_id
    ).first()
    if not state:
        raise ValueError(f"No onboarding state found for {auth0_user_id}")
    state.completed_steps = "[]"
    state.is_complete = False
    state.completed_at = None
    db.commit()
    db.refresh(state)
    return state
