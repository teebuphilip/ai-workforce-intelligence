"""
listings.py - Marketplace Listing CRUD
=======================================

WHY: Platform Rule #2 — every capability needs a single adapter.
     This module owns all listing data access. Routes never query listings directly.

WHAT:
    Generic marketplace listings (title, description, price, category, images, status).
    Tenant-scoped: each tenant's listings are isolated by tenant_id.

HOW:
    1. Create listings via create_listing()
    2. Index them in MeiliSearch via listing_to_search_doc() + meilisearch_lib.add_documents()
       (indexing is done by the API layer, not here, so this module stays framework-agnostic)
    3. Query via list_listings() or search via MeiliSearch search endpoint

USAGE:
    from core.listings import create_listing, get_listing, list_listings, Listing

    listing = create_listing(
        db=db,
        tenant_id="acme",
        seller_id="auth0|abc123",
        title="Vintage lamp",
        price_usd=25.0,
        category="furniture",
        status="active",
    )
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import Session

from core.database import Base
from core.tenancy import TenantMixin

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

LISTING_STATUSES = ("active", "sold", "draft")


# ============================================================
# MODEL
# ============================================================

class Listing(TenantMixin, Base):
    """
    One row per marketplace listing.

    Tenant-scoped via TenantMixin (tenant_id column + index).
    Images stored as JSON array string (portable across SQLite and PostgreSQL).
    """
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Ownership
    seller_id = Column(String(128), nullable=False, index=True,
                       comment="Auth0 user ID of the listing's creator")

    # Content
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    price_usd = Column(Float, nullable=False)
    category = Column(String(64), nullable=True, index=True)
    images = Column(Text, nullable=True,
                    comment="JSON array of image URLs, e.g. [\"https://...\"]")

    # Status
    status = Column(String(16), nullable=False, default="draft", index=True,
                    comment="active | sold | draft")

    def __repr__(self):
        return (
            f"<Listing id={self.id} tenant={self.tenant_id} "
            f"title={self.title!r} status={self.status} price=${self.price_usd:.2f}>"
        )

    def images_list(self) -> List[str]:
        """Deserialise images JSON string to a Python list."""
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except (json.JSONDecodeError, TypeError):
            return []


# ============================================================
# CORE FUNCTIONS
# ============================================================

def create_listing(
    db: Session,
    tenant_id: str,
    seller_id: str,
    title: str,
    price_usd: float,
    description: Optional[str] = None,
    category: Optional[str] = None,
    images: Optional[List[str]] = None,
    status: str = "draft",
) -> Listing:
    """
    Create a new marketplace listing.

    Args:
        db: SQLAlchemy session
        tenant_id: Owning tenant
        seller_id: Auth0 user ID of the seller
        title: Listing title
        price_usd: Price in USD
        description: Optional long description
        category: Optional category string
        images: Optional list of image URLs
        status: "active" | "sold" | "draft" (default "draft")

    Returns:
        The created Listing row

    Raises:
        ValueError: If status is not one of LISTING_STATUSES
    """
    if status not in LISTING_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {LISTING_STATUSES}"
        )

    images_json = json.dumps(images) if images else None

    listing = Listing(
        tenant_id=tenant_id,
        seller_id=seller_id,
        title=title,
        price_usd=price_usd,
        description=description,
        category=category,
        images=images_json,
        status=status,
    )

    db.add(listing)
    db.commit()
    db.refresh(listing)

    logger.debug(
        f"Listing created: id={listing.id} tenant={tenant_id} "
        f"title={title!r} status={status}"
    )
    return listing


def get_listing(
    db: Session,
    listing_id: int,
    tenant_id: Optional[str] = None,
) -> Optional[Listing]:
    """
    Retrieve a single listing by ID.

    Args:
        db: SQLAlchemy session
        listing_id: Listing primary key
        tenant_id: If provided, filters to this tenant only

    Returns:
        Listing row or None if not found
    """
    query = db.query(Listing).filter(Listing.id == listing_id)
    if tenant_id:
        query = query.filter(Listing.tenant_id == tenant_id)
    return query.first()


def list_listings(
    db: Session,
    tenant_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Listing]:
    """
    List listings with optional filters.

    Args:
        db: SQLAlchemy session
        tenant_id: Filter by tenant (None = all tenants)
        category: Filter by category string
        status: Filter by status ("active", "sold", "draft")
        limit: Max rows to return (default 50)
        offset: Pagination offset (default 0)

    Returns:
        List of Listing rows
    """
    query = db.query(Listing)

    if tenant_id:
        query = query.filter(Listing.tenant_id == tenant_id)
    if category:
        query = query.filter(Listing.category == category)
    if status:
        query = query.filter(Listing.status == status)

    return query.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()


def update_listing(
    db: Session,
    listing_id: int,
    tenant_id: str,
    **fields,
) -> Optional[Listing]:
    """
    Update a listing's fields.

    Args:
        db: SQLAlchemy session
        listing_id: Listing to update
        tenant_id: Must match listing's tenant (security guard)
        **fields: Fields to update (title, description, price_usd, category, images, status)

    Returns:
        Updated Listing or None if not found / tenant mismatch

    Raises:
        ValueError: If status field value is invalid
    """
    listing = get_listing(db, listing_id, tenant_id=tenant_id)
    if listing is None:
        return None

    allowed = {"title", "description", "price_usd", "category", "images", "status"}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "status" and value not in LISTING_STATUSES:
            raise ValueError(
                f"Invalid status '{value}'. Must be one of: {LISTING_STATUSES}"
            )
        if key == "images" and isinstance(value, list):
            value = json.dumps(value)
        setattr(listing, key, value)

    listing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(listing)
    return listing


def delete_listing(
    db: Session,
    listing_id: int,
    tenant_id: str,
) -> bool:
    """
    Delete a listing.

    Args:
        db: SQLAlchemy session
        listing_id: Listing to delete
        tenant_id: Must match listing's tenant (security guard)

    Returns:
        True if deleted

    Raises:
        ValueError: If listing not found or belongs to a different tenant
    """
    listing = get_listing(db, listing_id, tenant_id=tenant_id)
    if listing is None:
        raise ValueError(
            f"Listing {listing_id} not found for tenant '{tenant_id}'"
        )
    db.delete(listing)
    db.commit()
    return True


def listing_to_search_doc(listing: Listing) -> Dict[str, Any]:
    """
    Serialise a Listing to a MeiliSearch document dict.

    The 'id' field is required as the MeiliSearch primary key.

    Args:
        listing: Listing ORM row

    Returns:
        Dict ready for meilisearch_lib.add_documents()
    """
    return {
        "id": listing.id,
        "tenant_id": listing.tenant_id,
        "seller_id": listing.seller_id,
        "title": listing.title,
        "description": listing.description or "",
        "price_usd": listing.price_usd,
        "category": listing.category or "",
        "status": listing.status,
        "images": listing.images_list(),
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
    }
