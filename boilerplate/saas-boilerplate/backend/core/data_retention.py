"""
data_retention.py - P2 Data Lifecycle

#41: Log Retention Policy — RetentionPolicy table; configurable TTL per log type.
     purge_expired_logs() deletes rows older than the configured window.
     Defaults: ai_cost_log=90d, fraud_event=365d, activation_event=365d.

#42: Data Retention Rules — Same RetentionPolicy mechanism for compliance data.
     Defaults: consent_audit=2555d (7yr), expense_log=2555d, stripe_transaction=2555d.
     apply_retention_rules() runs the full set of configured compliance retention policies.

#43: Archival Strategy — ArchivedRecord table; archive_tenant_data() serializes all
     tenant rows from registered models to JSON cold storage before purge.

#44: Data Deletion SLA — DataDeletionRequest table; GDPR 30-day SLA tracking.
     request_data_deletion() creates request. complete_deletion() archives then purges.
     get_overdue_deletions() lists requests past the SLA window.
"""
import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)

# Default retention windows (days)
RETENTION_DEFAULTS: Dict[str, int] = {
    "ai_cost_log":        90,
    "fraud_event":        365,
    "activation_event":   365,
    "consent_audit":      2555,   # ~7 years
    "expense_log":        2555,
    "stripe_transaction": 2555,
}

# #41: operational/short-lived log types
LOG_DATA_TYPES: Tuple[str, ...] = ("ai_cost_log", "fraud_event", "activation_event")

# #42: compliance/business data types (long retention)
COMPLIANCE_DATA_TYPES: Tuple[str, ...] = (
    "consent_audit", "expense_log", "stripe_transaction"
)

# #44: GDPR deletion SLA
DELETION_SLA_DAYS = 30
DELETION_STATUSES = ("pending", "in_progress", "completed", "failed")


# ─── MODELS ───────────────────────────────────────────────────────────────────

class RetentionPolicy(Base):
    """#41/#42: One row per data_type defining the max age before purge."""
    __tablename__ = "retention_policies"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    data_type      = Column(String(64), nullable=False, unique=True, index=True)
    retention_days = Column(Integer, nullable=False)
    description    = Column(String(256), nullable=True)
    updated_at     = Column(DateTime, default=datetime.utcnow)
    created_at     = Column(DateTime, default=datetime.utcnow)


class ArchivedRecord(Base):
    """#43: Cold-storage snapshot of a row serialised before it is purged."""
    __tablename__ = "archived_records"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id     = Column(String(64), nullable=False, index=True)
    data_type     = Column(String(64), nullable=False, index=True)
    source_id     = Column(Integer, nullable=True)    # PK of original row
    archived_data = Column(Text, nullable=False)      # JSON blob
    archived_at   = Column(DateTime, default=datetime.utcnow, index=True)


class DataDeletionRequest(Base):
    """#44: GDPR deletion request with 30-day SLA tracking."""
    __tablename__ = "data_deletion_requests"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id          = Column(String(64), nullable=False, index=True)
    requested_by       = Column(String(128), nullable=False)   # auth0_user_id
    requested_at       = Column(DateTime, default=datetime.utcnow, index=True)
    sla_deadline       = Column(DateTime, nullable=False)
    status             = Column(String(16), nullable=False, default="pending", index=True)
    completed_at       = Column(DateTime, nullable=True)
    data_types_deleted = Column(Text, nullable=True)   # JSON list of data_types purged
    notes              = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)


# ─── MODEL REGISTRY ───────────────────────────────────────────────────────────

def _get_model_registry() -> Dict[str, Tuple]:
    """
    Lazy registry mapping data_type → (ModelClass, date_column_name, tenant_column_name).
    tenant_column_name is None for user-keyed models (consent_audit uses auth0_user_id).
    Imported lazily to avoid circular imports at module load time.
    """
    from core.ai_governance import AICostLog
    from core.fraud import FraudEvent
    from core.activation import ActivationEvent
    from core.legal_consent import ConsentAuditLog
    from core.expense_tracking import ExpenseLog
    from core.financial_governance import StripeTransactionRecord

    return {
        "ai_cost_log":        (AICostLog,                "created_at",   "tenant_id"),
        "fraud_event":        (FraudEvent,               "occurred_at",  "tenant_id"),
        "activation_event":   (ActivationEvent,          "occurred_at",  "tenant_id"),
        "consent_audit":      (ConsentAuditLog,          "occurred_at",  None),   # user-keyed
        "expense_log":        (ExpenseLog,               "created_at",   "tenant_id"),
        "stripe_transaction": (StripeTransactionRecord,  "occurred_at",  "tenant_id"),
    }


# ─── #41 / #42: Retention Policy CRUD ────────────────────────────────────────

def set_retention_policy(
    db: Session,
    data_type: str,
    retention_days: int,
    description: Optional[str] = None,
) -> RetentionPolicy:
    """
    Upsert a retention policy for data_type.

    Raises ValueError for unknown data_type or non-positive retention_days.
    """
    if data_type not in RETENTION_DEFAULTS:
        raise ValueError(
            f"Unknown data_type '{data_type}'. "
            f"Must be one of: {sorted(RETENTION_DEFAULTS)}"
        )
    if retention_days <= 0:
        raise ValueError("retention_days must be a positive integer")

    existing = (
        db.query(RetentionPolicy)
        .filter(RetentionPolicy.data_type == data_type)
        .first()
    )
    if existing:
        existing.retention_days = retention_days
        if description is not None:
            existing.description = description
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        logger.info(f"RetentionPolicy updated: {data_type} → {retention_days}d")
        return existing

    policy = RetentionPolicy(
        data_type=data_type,
        retention_days=retention_days,
        description=description,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    logger.info(f"RetentionPolicy created: {data_type} → {retention_days}d")
    return policy


def get_retention_days(db: Session, data_type: str) -> int:
    """Return retention_days for data_type — DB value if set, else hardcoded default."""
    row = (
        db.query(RetentionPolicy)
        .filter(RetentionPolicy.data_type == data_type)
        .first()
    )
    return row.retention_days if row else RETENTION_DEFAULTS.get(data_type, 365)


def list_retention_policies(db: Session) -> List[RetentionPolicy]:
    return db.query(RetentionPolicy).order_by(RetentionPolicy.data_type).all()


# ─── Internal purge helper ────────────────────────────────────────────────────

def _purge_data_type(db: Session, data_type: str) -> int:
    """
    Delete rows for data_type older than their configured retention window.
    Returns count of deleted rows.
    """
    registry = _get_model_registry()
    if data_type not in registry:
        raise ValueError(f"Unknown data_type '{data_type}'")

    model, date_col_name, _ = registry[data_type]
    date_col = getattr(model, date_col_name)
    cutoff = datetime.utcnow() - timedelta(days=get_retention_days(db, data_type))

    count = db.query(model).filter(date_col < cutoff).delete(synchronize_session="fetch")
    db.commit()
    logger.info(f"Purged {count} {data_type} rows (cutoff={cutoff.date()})")
    return count


# ─── #41: Log Retention Policy ───────────────────────────────────────────────

def purge_expired_logs(
    db: Session,
    data_type: Optional[str] = None,
) -> Dict[str, int]:
    """
    #41: Delete operational log records past their retention window.

    If data_type is specified, purges only that type.
    Otherwise purges all LOG_DATA_TYPES (ai_cost_log, fraud_event, activation_event).
    Returns {data_type: deleted_count}.
    """
    types = [data_type] if data_type else list(LOG_DATA_TYPES)
    return {dt: _purge_data_type(db, dt) for dt in types}


# ─── #42: Data Retention Rules ───────────────────────────────────────────────

def apply_retention_rules(
    db: Session,
    data_type: Optional[str] = None,
) -> Dict[str, int]:
    """
    #42: Apply retention rules for compliance/business data.

    If data_type is specified, applies only that type.
    Otherwise applies all COMPLIANCE_DATA_TYPES.
    Returns {data_type: deleted_count}.
    """
    types = [data_type] if data_type else list(COMPLIANCE_DATA_TYPES)
    return {dt: _purge_data_type(db, dt) for dt in types}


# ─── #43: Archival Strategy ──────────────────────────────────────────────────

def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Serialize a SQLAlchemy row to a JSON-safe dict."""
    result = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, date):
            val = val.isoformat()
        result[col.name] = val
    return result


def archive_tenant_data(
    db: Session,
    tenant_id: str,
    data_types: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    #43: Serialize all tenant rows to ArchivedRecord cold storage.

    Queries each tenant_id-keyed model and writes a JSON snapshot for every row.
    Models without a tenant_id column (consent_audit) are skipped and return 0.
    Returns {data_type: archived_count}.
    """
    registry = _get_model_registry()
    # Default: all tenant_id-keyed types
    types = data_types or [
        dt for dt, (_, _, tc) in registry.items() if tc == "tenant_id"
    ]

    results: Dict[str, int] = {}
    for dt in types:
        if dt not in registry:
            continue
        model, _, tenant_col = registry[dt]
        if not tenant_col:
            results[dt] = 0
            continue

        rows = db.query(model).filter(
            getattr(model, tenant_col) == tenant_id
        ).all()

        for row in rows:
            db.add(ArchivedRecord(
                tenant_id=tenant_id,
                data_type=dt,
                source_id=row.id,
                archived_data=json.dumps(_row_to_dict(row)),
            ))

        db.flush()
        results[dt] = len(rows)
        logger.info(f"Archived {len(rows)} rows: tenant={tenant_id} data_type={dt}")

    db.commit()
    return results


def list_archives(
    db: Session,
    tenant_id: Optional[str] = None,
    data_type: Optional[str] = None,
) -> List[ArchivedRecord]:
    q = db.query(ArchivedRecord)
    if tenant_id:
        q = q.filter(ArchivedRecord.tenant_id == tenant_id)
    if data_type:
        q = q.filter(ArchivedRecord.data_type == data_type)
    return q.order_by(ArchivedRecord.archived_at.desc()).all()


# ─── #44: Data Deletion SLA ──────────────────────────────────────────────────

def request_data_deletion(
    db: Session,
    tenant_id: str,
    requested_by: str,
    notes: Optional[str] = None,
) -> DataDeletionRequest:
    """
    #44: Create a GDPR data deletion request with a 30-day SLA deadline.
    """
    now = datetime.utcnow()
    req = DataDeletionRequest(
        tenant_id=tenant_id,
        requested_by=requested_by,
        requested_at=now,
        sla_deadline=now + timedelta(days=DELETION_SLA_DAYS),
        status="pending",
        notes=notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    logger.info(
        f"DataDeletionRequest #{req.id}: tenant={tenant_id} "
        f"deadline={req.sla_deadline.date()}"
    )
    return req


def complete_deletion(
    db: Session,
    request_id: int,
    data_types: Optional[List[str]] = None,
) -> DataDeletionRequest:
    """
    #44: Fulfil a deletion request — archive then purge all tenant data.

    1. Archives all tenant rows to cold storage (ArchivedRecord).
    2. Deletes all rows from every tenant_id-keyed model for the tenant.
    3. Marks request status = 'completed'.

    Raises ValueError if request not found or already completed.
    """
    req = db.query(DataDeletionRequest).filter(
        DataDeletionRequest.id == request_id
    ).first()
    if not req:
        raise ValueError(f"DataDeletionRequest {request_id} not found")
    if req.status == "completed":
        raise ValueError(f"DataDeletionRequest {request_id} is already completed")

    req.status = "in_progress"
    db.commit()

    # Step 1: archive
    archive_tenant_data(db, req.tenant_id, data_types)

    # Step 2: purge
    registry = _get_model_registry()
    types = data_types or [
        dt for dt, (_, _, tc) in registry.items() if tc == "tenant_id"
    ]
    deleted: Dict[str, int] = {}
    for dt in types:
        if dt not in registry:
            continue
        model, _, tenant_col = registry[dt]
        if not tenant_col:
            continue
        count = db.query(model).filter(
            getattr(model, tenant_col) == req.tenant_id
        ).delete(synchronize_session="fetch")
        deleted[dt] = count
    db.flush()

    # Step 3: mark completed
    req.status = "completed"
    req.completed_at = datetime.utcnow()
    req.data_types_deleted = json.dumps(list(deleted.keys()))
    db.commit()
    db.refresh(req)
    logger.info(
        f"DataDeletion #{request_id} completed: tenant={req.tenant_id} "
        f"deleted={sum(deleted.values())} rows"
    )
    return req


def get_overdue_deletions(db: Session) -> List[DataDeletionRequest]:
    """
    #44: Return pending/in_progress deletion requests that have passed their SLA deadline.
    """
    now = datetime.utcnow()
    return (
        db.query(DataDeletionRequest)
        .filter(
            DataDeletionRequest.status.in_(["pending", "in_progress"]),
            DataDeletionRequest.sla_deadline < now,
        )
        .order_by(DataDeletionRequest.sla_deadline)
        .all()
    )


def get_deletion_request(
    db: Session, request_id: int
) -> Optional[DataDeletionRequest]:
    return db.query(DataDeletionRequest).filter(
        DataDeletionRequest.id == request_id
    ).first()


def list_deletion_requests(
    db: Session,
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[DataDeletionRequest]:
    q = db.query(DataDeletionRequest)
    if tenant_id:
        q = q.filter(DataDeletionRequest.tenant_id == tenant_id)
    if status:
        if status not in DELETION_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {DELETION_STATUSES}"
            )
        q = q.filter(DataDeletionRequest.status == status)
    return q.order_by(DataDeletionRequest.requested_at.desc()).all()
