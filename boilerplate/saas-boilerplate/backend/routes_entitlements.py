"""
routes/entitlements.py - Entitlements API

WHY: Frontend needs to know what the user is allowed to do.
     This route exposes that cleanly so React can gate features.

AUTO-LOADED by boilerplate loader.py - no imports needed in main.py.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import get_current_user
from core.entitlements import get_entitlements, has_entitlement

logger = logging.getLogger(__name__)
router = APIRouter(tags=["entitlements"])


# ============================================================
# RESPONSE MODELS
# ============================================================

class EntitlementsResponse(BaseModel):
    """WHY: Typed response so frontend knows exactly what to expect."""
    user_id: str
    entitlements: List[str]
    count: int


class EntitlementCheckResponse(BaseModel):
    feature: str
    allowed: bool


# ============================================================
# ROUTES
# ============================================================

@router.get("/", response_model=EntitlementsResponse)
def get_my_entitlements(
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all active entitlements for the logged-in user.
    Frontend calls this on load to know what to show/hide.

    GET /api/entitlements/
    Response: { user_id, entitlements: ["dashboard", "ai_sorting", ...], count }
    """
    entitlements = get_entitlements(user.id, db)
    return EntitlementsResponse(
        user_id=user.id,
        entitlements=entitlements,
        count=len(entitlements)
    )


@router.get("/check/{feature}", response_model=EntitlementCheckResponse)
def check_entitlement(
    feature: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if logged-in user has a specific entitlement.
    WHY: Useful for one-off checks without fetching everything.

    GET /api/entitlements/check/ai_sorting
    Response: { feature: "ai_sorting", allowed: true }
    """
    allowed = has_entitlement(user.id, feature, db)
    return EntitlementCheckResponse(feature=feature, allowed=allowed)
