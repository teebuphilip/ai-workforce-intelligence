"""
expense_tracking.py - Platform Expense Tracking & P&L Attribution
==================================================================

WHY: Platform Rule #2 — every capability needs a single adapter.
     This is the expense tracking module. All cost logging goes here.

     AI costs are tracked separately in ai_governance.py (AICostLog).
     This module tracks everything else:
     - Infrastructure (Railway hosting)
     - Stripe processing fees (2.9% + $0.30 per transaction)
     - Email service costs (MailerLite)
     - Domain costs (GoDaddy)
     - Miscellaneous operational costs

     With both tables populated, get_pl_summary() computes:
         MRR (from subscriptions) - All costs = Profit per tenant/product

HOW:
    1. Log infrastructure costs monthly (Railway invoices)
    2. Log Stripe fees from webhook events (payment_intent.succeeded)
    3. Log AI costs automatically via ai_governance.py (already happens)
    4. View P&L at /api/admin/pl

USAGE:
    from core.expense_tracking import log_expense, get_pl_summary

    # Log a Stripe processing fee when payment succeeds:
    log_expense(
        db=db,
        tenant_id="courtdominion",
        category="stripe_fee",
        amount_usd=1.72,
        source="stripe",
        description="Processing fee: $49 payment (2.9% + $0.30)",
    )

    # Get this month's P&L for a tenant:
    pl = get_pl_summary(db, tenant_id="courtdominion", month_key="2026-02")
"""

import os
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from collections import defaultdict

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, func
from sqlalchemy.orm import Session

from core.database import Base

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

EXPENSE_CATEGORIES = (
    "ai_api",       # AI API costs (Claude, OpenAI) — cross-ref with AICostLog
    "infra",        # Railway hosting, PostgreSQL
    "stripe_fee",   # Stripe processing fees (2.9% + $0.30)
    "email",        # MailerLite costs
    "domain",       # GoDaddy domain renewals
    "misc",         # Any other operational cost
)


# ============================================================
# MODEL
# ============================================================

class ExpenseLog(Base):
    """
    One row per logged expense.

    Tracks non-AI operational costs per tenant/product.
    AI costs are in AICostLog (ai_governance.py) — don't duplicate.

    Use get_pl_summary() to combine both tables for full P&L.
    """
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    log_date = Column(Date, default=date.today, nullable=False, index=True,
                      comment="Date for fast aggregation queries")

    # PERIOD
    month_key = Column(String(7), nullable=False, index=True,
                       comment="YYYY-MM format for monthly grouping, e.g. '2026-02'")

    # WHO / WHAT
    tenant_id = Column(String(64), nullable=False, index=True,
                       comment="Which tenant this cost is attributed to")
    product_name = Column(String(128), nullable=True,
                          comment="Product/business name (e.g. CourtDominion, AutoFounderHub)")

    # COST
    category = Column(String(32), nullable=False, index=True,
                      comment="ai_api | infra | stripe_fee | email | domain | misc")
    amount_usd = Column(Float, nullable=False,
                        comment="Cost in USD (positive = expense)")
    source = Column(String(64), nullable=False,
                    comment="Service that generated this cost: railway/stripe/mailerlite/godaddy/etc")
    description = Column(Text, nullable=True,
                         comment="Human-readable description of this expense")
    is_recurring = Column(Boolean, nullable=False, default=False,
                          comment="True for monthly subscriptions, False for one-time fees")

    def __repr__(self):
        return (
            f"<ExpenseLog {self.month_key} tenant={self.tenant_id} "
            f"category={self.category} amount=${self.amount_usd:.4f}>"
        )


# ============================================================
# CORE FUNCTIONS
# ============================================================

def log_expense(
    db: Session,
    tenant_id: str,
    category: str,
    amount_usd: float,
    source: str,
    description: Optional[str] = None,
    product_name: Optional[str] = None,
    is_recurring: bool = False,
    log_date: Optional[date] = None,
) -> ExpenseLog:
    """
    Log an operational expense to the expense table.

    Args:
        db: SQLAlchemy session
        tenant_id: Tenant this cost is attributed to
        category: One of EXPENSE_CATEGORIES
        amount_usd: Cost in USD (positive number)
        source: Service name (railway, stripe, mailerlite, godaddy, etc.)
        description: Human-readable description
        product_name: Product/business name
        is_recurring: True for monthly subscription costs
        log_date: Date of expense (defaults to today)

    Returns:
        The created ExpenseLog row

    Raises:
        ValueError: If category is not one of EXPENSE_CATEGORIES
    """
    if category not in EXPENSE_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {EXPENSE_CATEGORIES}"
        )

    expense_date = log_date or date.today()
    month_key = expense_date.strftime("%Y-%m")

    entry = ExpenseLog(
        log_date=expense_date,
        month_key=month_key,
        tenant_id=tenant_id,
        product_name=product_name,
        category=category,
        amount_usd=amount_usd,
        source=source,
        description=description,
        is_recurring=is_recurring,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.debug(
        f"Expense logged: tenant={tenant_id} category={category} "
        f"amount=${amount_usd:.4f} source={source}"
    )
    return entry


def get_expense_summary(
    db: Session,
    month_key: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get expense totals grouped by category.

    Args:
        db: SQLAlchemy session
        month_key: Filter by month (e.g. "2026-02"). None = all time.
        tenant_id: Filter by tenant. None = all tenants.

    Returns:
        Dict with:
            total_usd: float — sum of all expenses
            by_category: {category: total_usd} — breakdown
            by_tenant: {tenant_id: total_usd} — breakdown (only when tenant_id=None)
            month_key: str — the month filtered (or "all")
            row_count: int — number of expense rows
    """
    query = db.query(ExpenseLog)

    if month_key:
        query = query.filter(ExpenseLog.month_key == month_key)
    if tenant_id:
        query = query.filter(ExpenseLog.tenant_id == tenant_id)

    rows = query.all()

    by_category: Dict[str, float] = defaultdict(float)
    by_tenant: Dict[str, float] = defaultdict(float)
    total = 0.0

    for row in rows:
        by_category[row.category] += row.amount_usd
        by_tenant[row.tenant_id] += row.amount_usd
        total += row.amount_usd

    result: Dict[str, Any] = {
        "total_usd": round(total, 4),
        "by_category": {k: round(v, 4) for k, v in by_category.items()},
        "month_key": month_key or "all",
        "row_count": len(rows),
    }

    if not tenant_id:
        result["by_tenant"] = {k: round(v, 4) for k, v in by_tenant.items()}

    return result


def get_pl_summary(
    db: Session,
    tenant_id: str,
    month_key: str,
    revenue_usd: float = 0.0,
) -> Dict[str, Any]:
    """
    Compute a simple P&L for a tenant for a given month.

    AI costs come from AICostLog (ai_governance.py).
    Other costs come from ExpenseLog (this module).
    Revenue is passed in (typically sum of Stripe payments that month).

    Args:
        db: SQLAlchemy session
        tenant_id: The tenant to compute P&L for
        month_key: Month in YYYY-MM format
        revenue_usd: Total revenue for the month (from Stripe or manual input)

    Returns:
        Dict with:
            revenue_usd: float
            total_expenses_usd: float
            net_profit_usd: float
            margin_pct: float — profit as % of revenue (0 if no revenue)
            by_category: {category: total_usd}
    """
    # Get non-AI operational costs
    expense_summary = get_expense_summary(db, month_key=month_key, tenant_id=tenant_id)
    operational_costs = expense_summary["total_usd"]

    # Get AI costs from AICostLog (cross-module query)
    try:
        from core.ai_governance import AICostLog
        ai_costs_query = (
            db.query(func.sum(AICostLog.cost_usd))
            .filter(
                AICostLog.tenant_id == tenant_id,
                AICostLog.log_date >= date.fromisoformat(f"{month_key}-01"),
            )
            .scalar()
        ) or 0.0
    except Exception:
        ai_costs_query = 0.0
        logger.warning("Could not load AI costs from AICostLog — included as 0")

    total_expenses = round(operational_costs + ai_costs_query, 4)
    net_profit = round(revenue_usd - total_expenses, 4)
    margin_pct = round((net_profit / revenue_usd * 100) if revenue_usd > 0 else 0.0, 2)

    return {
        "tenant_id": tenant_id,
        "month_key": month_key,
        "revenue_usd": round(revenue_usd, 4),
        "total_expenses_usd": total_expenses,
        "operational_costs_usd": round(operational_costs, 4),
        "ai_costs_usd": round(ai_costs_query, 4),
        "net_profit_usd": net_profit,
        "margin_pct": margin_pct,
        "by_category": expense_summary["by_category"],
    }
