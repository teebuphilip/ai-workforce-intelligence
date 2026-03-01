"""
financial_governance.py - P1 Financial Governance

#37: Stripe Fee Attribution — StripeTransactionRecord table; records Stripe gross/fee/net
     per charge or payout. get_stripe_fee_summary() aggregates by tenant/period.
     Webhook handler for charge.succeeded in main.py auto-populates when
     balance_transaction is expanded; otherwise admin records manually.

#38: Gross Margin Calculation — get_gross_margin() separates Cost of Revenue
     (Stripe fees = COGS) from Operating Expenses (AI, infra, email, domain).
     Gross Profit = Revenue - COGS; Net Profit = Gross Profit - Opex.

#39: Multi-Source Reconciliation — ReconciliationRecord table; reconcile_period()
     auto-computes Stripe net deposits from StripeTransactionRecord and compares
     against manually-entered bank statement total. Flags |variance| > $0.01.

#40: Accounting Export (CSV) — export_accounting_csv() joins StripeTransactionRecord
     and ExpenseLog into a QuickBooks-compatible CSV (Date, Type, Description,
     Account, Amount_USD, Tenant, Period, Reference).
"""
import csv
import io
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, func
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)

TRANSACTION_TYPES = ("charge", "refund", "payout", "adjustment")
RECONCILIATION_STATUSES = ("pending", "matched", "variance")

# Rounding differences up to $0.01 between Stripe and bank are acceptable
RECONCILIATION_TOLERANCE_USD = 0.01


# ─── MODELS ───────────────────────────────────────────────────────────────────

class StripeTransactionRecord(Base):
    """#37: One row per Stripe balance transaction with fee attribution."""
    __tablename__ = "stripe_transaction_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    stripe_balance_txn_id = Column(String(64), nullable=True, unique=True, index=True)
    stripe_charge_id = Column(String(64), nullable=True, index=True)
    stripe_payment_intent_id = Column(String(64), nullable=True, index=True)
    transaction_type = Column(String(32), nullable=False)   # charge | refund | payout | adjustment
    gross_usd = Column(Float, nullable=False)               # Full amount charged
    fee_usd = Column(Float, nullable=False)                 # Stripe's cut
    net_usd = Column(Float, nullable=False)                 # gross - fee
    currency = Column(String(8), default="usd")
    description = Column(String(256), nullable=True)
    period_key = Column(String(7), nullable=False, index=True)  # YYYY-MM
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReconciliationRecord(Base):
    """#39: One row per (tenant, period) reconciliation run."""
    __tablename__ = "reconciliation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    period_key = Column(String(7), nullable=False, index=True)   # YYYY-MM
    stripe_total_usd = Column(Float, nullable=False)             # Sum of Stripe net deposits
    bank_total_usd = Column(Float, nullable=False)               # Manually-entered bank figure
    variance_usd = Column(Float, nullable=False)                 # stripe - bank (0.00 = clean)
    status = Column(String(16), nullable=False)                  # matched | variance | pending
    notes = Column(Text, nullable=True)
    reconciled_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── #37: Stripe Fee Attribution ──────────────────────────────────────────────

def record_stripe_transaction(
    db: Session,
    tenant_id: str,
    gross_usd: float,
    fee_usd: float,
    transaction_type: str = "charge",
    stripe_balance_txn_id: Optional[str] = None,
    stripe_charge_id: Optional[str] = None,
    stripe_payment_intent_id: Optional[str] = None,
    description: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
    period_key: Optional[str] = None,
) -> StripeTransactionRecord:
    """
    Record a Stripe balance transaction with fee attribution.

    Called automatically from the charge.succeeded webhook handler (main.py)
    when balance_transaction is expanded, or manually via the admin API.
    """
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError(
            f"Invalid transaction_type '{transaction_type}'. "
            f"Must be one of: {TRANSACTION_TYPES}"
        )
    if fee_usd < 0:
        raise ValueError("fee_usd cannot be negative")

    now = occurred_at or datetime.utcnow()
    pk = period_key or now.strftime("%Y-%m")
    net = round(gross_usd - fee_usd, 6)

    record = StripeTransactionRecord(
        tenant_id=tenant_id,
        stripe_balance_txn_id=stripe_balance_txn_id,
        stripe_charge_id=stripe_charge_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        transaction_type=transaction_type,
        gross_usd=gross_usd,
        fee_usd=fee_usd,
        net_usd=net,
        description=description,
        period_key=pk,
        occurred_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(
        f"StripeTransaction: type={transaction_type} gross={gross_usd} "
        f"fee={fee_usd} net={net} tenant={tenant_id}"
    )
    return record


def get_stripe_fee_summary(
    db: Session,
    tenant_id: Optional[str] = None,
    period_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate gross, fees, and net across Stripe transactions.

    effective_rate_pct = (total_fees / gross) * 100.
    Returns 0.0 for all fields when no transactions exist.
    """
    q = db.query(
        func.coalesce(func.sum(StripeTransactionRecord.gross_usd), 0.0),
        func.coalesce(func.sum(StripeTransactionRecord.fee_usd), 0.0),
        func.coalesce(func.sum(StripeTransactionRecord.net_usd), 0.0),
        func.count(StripeTransactionRecord.id),
    )
    if tenant_id:
        q = q.filter(StripeTransactionRecord.tenant_id == tenant_id)
    if period_key:
        q = q.filter(StripeTransactionRecord.period_key == period_key)

    gross, fees, net, count = q.one()
    gross, fees, net = float(gross), float(fees), float(net)

    return {
        "tenant_id": tenant_id,
        "period_key": period_key,
        "gross_usd": round(gross, 2),
        "total_fees_usd": round(fees, 2),
        "net_usd": round(net, 2),
        "transaction_count": count,
        "effective_rate_pct": round(fees / gross * 100, 4) if gross else 0.0,
    }


# ─── #38: Gross Margin Calculation ────────────────────────────────────────────

def get_gross_margin(
    db: Session,
    tenant_id: str,
    period_key: str,
    revenue_usd: float,
) -> Dict[str, Any]:
    """
    Full two-layer P&L for a tenant/month.

    Layer 1 — Gross Margin:
        Gross Profit  = Revenue - Stripe fees (Cost of Revenue)
        Gross Margin% = Gross Profit / Revenue * 100

    Layer 2 — Net Margin:
        Net Profit  = Gross Profit - Operating Expenses
        Net Margin% = Net Profit / Revenue * 100

    Operating Expenses come from ExpenseLog (ai_api, infra, email, domain, misc).
    Stripe fees come from StripeTransactionRecord (separate from ExpenseLog stripe_fee
    category — avoid double-counting if both are populated).
    """
    from core.expense_tracking import get_expense_summary

    # COGS: Stripe payment processing fees
    fee_summary = get_stripe_fee_summary(db, tenant_id=tenant_id, period_key=period_key)
    stripe_fees = fee_summary["total_fees_usd"]

    gross_profit = round(revenue_usd - stripe_fees, 2)
    gross_margin_pct = round(gross_profit / revenue_usd * 100, 2) if revenue_usd else 0.0

    # Opex: AI API + infra + email + domain + misc
    expense_summary = get_expense_summary(db, tenant_id=tenant_id, month_key=period_key)
    total_opex = round(expense_summary.get("total_usd", 0.0), 2)

    net_profit = round(gross_profit - total_opex, 2)
    net_margin_pct = round(net_profit / revenue_usd * 100, 2) if revenue_usd else 0.0

    return {
        "tenant_id": tenant_id,
        "period_key": period_key,
        "revenue_usd": revenue_usd,
        "stripe_fees_usd": stripe_fees,
        "gross_profit_usd": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "operating_expenses_usd": total_opex,
        "opex_by_category": expense_summary.get("by_category", {}),
        "net_profit_usd": net_profit,
        "net_margin_pct": net_margin_pct,
        "stripe_transaction_count": fee_summary["transaction_count"],
    }


# ─── #39: Multi-Source Reconciliation ─────────────────────────────────────────

def reconcile_period(
    db: Session,
    tenant_id: str,
    period_key: str,
    bank_total_usd: float,
    notes: Optional[str] = None,
) -> ReconciliationRecord:
    """
    Create or update a reconciliation record for a (tenant, period).

    stripe_total is auto-computed from StripeTransactionRecord.net_usd.
    status = 'matched' when |variance| <= $0.01, else 'variance'.
    Calling again for the same period re-runs the calc (upsert).
    """
    fee_summary = get_stripe_fee_summary(db, tenant_id=tenant_id, period_key=period_key)
    stripe_total = fee_summary["net_usd"]
    variance = round(stripe_total - bank_total_usd, 2)
    status = "matched" if abs(variance) <= RECONCILIATION_TOLERANCE_USD else "variance"

    existing = (
        db.query(ReconciliationRecord)
        .filter(
            ReconciliationRecord.tenant_id == tenant_id,
            ReconciliationRecord.period_key == period_key,
        )
        .first()
    )

    if existing:
        existing.stripe_total_usd = stripe_total
        existing.bank_total_usd = bank_total_usd
        existing.variance_usd = variance
        existing.status = status
        existing.notes = notes
        existing.reconciled_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        logger.info(
            f"Reconciliation updated: tenant={tenant_id} period={period_key} "
            f"status={status} variance={variance}"
        )
        return existing

    record = ReconciliationRecord(
        tenant_id=tenant_id,
        period_key=period_key,
        stripe_total_usd=stripe_total,
        bank_total_usd=bank_total_usd,
        variance_usd=variance,
        status=status,
        notes=notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(
        f"Reconciliation created: tenant={tenant_id} period={period_key} "
        f"status={status} variance={variance}"
    )
    return record


def get_reconciliation(
    db: Session,
    tenant_id: str,
    period_key: str,
) -> Optional[ReconciliationRecord]:
    return (
        db.query(ReconciliationRecord)
        .filter(
            ReconciliationRecord.tenant_id == tenant_id,
            ReconciliationRecord.period_key == period_key,
        )
        .first()
    )


def list_reconciliations(
    db: Session,
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[ReconciliationRecord]:
    q = db.query(ReconciliationRecord)
    if tenant_id:
        q = q.filter(ReconciliationRecord.tenant_id == tenant_id)
    if status:
        if status not in RECONCILIATION_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {RECONCILIATION_STATUSES}"
            )
        q = q.filter(ReconciliationRecord.status == status)
    return q.order_by(ReconciliationRecord.period_key.desc()).all()


# ─── #40: Accounting Export (CSV) ─────────────────────────────────────────────

QB_HEADERS = [
    "Date", "Type", "Description", "Account",
    "Amount_USD", "Tenant", "Period", "Reference",
]

# Maps transaction/expense types to QuickBooks chart-of-accounts names
_ACCOUNT_MAP = {
    "charge":     "Revenue",
    "refund":     "Revenue Refunds",
    "payout":     "Bank Payout",
    "adjustment": "Stripe Adjustment",
    "ai_api":     "AI API Costs",
    "infra":      "Infrastructure",
    "stripe_fee": "Payment Processing Fees",
    "email":      "Email Marketing",
    "domain":     "Domain & Hosting",
    "misc":       "Miscellaneous Expense",
}


def export_accounting_csv(
    db: Session,
    tenant_id: Optional[str] = None,
    period_key: Optional[str] = None,
) -> str:
    """
    #40: QuickBooks-compatible CSV export combining revenue and expenses.

    Revenue rows: one gross line + one fee line per StripeTransactionRecord.
    Expense rows: one line per ExpenseLog entry (Amount_USD is negative = outflow).

    Sorted ascending by Date. Returns CSV as a string.
    """
    from core.expense_tracking import ExpenseLog

    rows: List[Dict[str, Any]] = []

    # Revenue and fee rows from StripeTransactionRecord
    stripe_q = db.query(StripeTransactionRecord)
    if tenant_id:
        stripe_q = stripe_q.filter(StripeTransactionRecord.tenant_id == tenant_id)
    if period_key:
        stripe_q = stripe_q.filter(StripeTransactionRecord.period_key == period_key)

    for txn in stripe_q.order_by(StripeTransactionRecord.occurred_at).all():
        rows.append({
            "Date": txn.occurred_at.strftime("%Y-%m-%d"),
            "Type": "Revenue",
            "Description": txn.description or f"Stripe {txn.transaction_type}",
            "Account": _ACCOUNT_MAP.get(txn.transaction_type, "Revenue"),
            "Amount_USD": txn.gross_usd,
            "Tenant": txn.tenant_id,
            "Period": txn.period_key,
            "Reference": txn.stripe_charge_id or txn.stripe_balance_txn_id or "",
        })
        if txn.fee_usd > 0:
            rows.append({
                "Date": txn.occurred_at.strftime("%Y-%m-%d"),
                "Type": "Expense",
                "Description": (
                    f"Stripe fee — "
                    f"{txn.stripe_charge_id or txn.stripe_balance_txn_id or 'txn'}"
                ),
                "Account": "Payment Processing Fees",
                "Amount_USD": -txn.fee_usd,
                "Tenant": txn.tenant_id,
                "Period": txn.period_key,
                "Reference": txn.stripe_balance_txn_id or "",
            })

    # Expense rows from ExpenseLog
    exp_q = db.query(ExpenseLog)
    if tenant_id:
        exp_q = exp_q.filter(ExpenseLog.tenant_id == tenant_id)
    if period_key:
        exp_q = exp_q.filter(ExpenseLog.month_key == period_key)

    for exp in exp_q.order_by(ExpenseLog.log_date).all():
        rows.append({
            "Date": exp.log_date.strftime("%Y-%m-%d"),
            "Type": "Expense",
            "Description": exp.description or f"{exp.source} — {exp.category}",
            "Account": _ACCOUNT_MAP.get(exp.category, "Miscellaneous Expense"),
            "Amount_USD": -exp.amount_usd,   # Negative = money out
            "Tenant": exp.tenant_id,
            "Period": exp.month_key,
            "Reference": exp.source,
        })

    rows.sort(key=lambda r: r["Date"])

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=QB_HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
