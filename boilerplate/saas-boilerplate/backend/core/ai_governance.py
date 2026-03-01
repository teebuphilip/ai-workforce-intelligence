"""
ai_governance.py - AI Cost Tracking, Budget Enforcement & Model Routing
=========================================================================

WHY: AI API costs are the #1 variable cost in this platform (~$50-500/month
     per business). Without governance:
     - Runaway loops can burn $500 in a weekend (happened in FounderOps testing)
     - No visibility into which feature/tenant drives cost
     - No way to enforce per-tenant budget limits

HOW:
    All AI calls go through call_ai(). No direct anthropic/openai calls allowed.
    Platform Rule #3: All AI calls MUST pass through AI Governance.

    call_ai():
      1. Checks tenant budget (raises BudgetExceededError if over limit)
      2. Routes to correct model based on task type + tenant tier
      3. Makes the actual API call
      4. Logs: timestamp, tenant_id, feature, model, tokens_in, tokens_out, cost_usd
      5. Returns response

USAGE:
    from core.ai_governance import call_ai, AIGovernanceError

    response = call_ai(
        prompt="Summarize this basketball game...",
        tenant_id="courtdominion",
        feature="game_summary",           # for cost attribution
        task_type="summarization",        # drives model routing
        system_prompt="You are a sports analyst..."
    )
    text = response["content"]
    cost = response["cost_usd"]

COST TRACKING SCHEMA (ai_costs table):
    date, tenant_id, feature, model, tokens_in, tokens_out, cost_usd, duration_ms
"""

import os
import time
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Text
from sqlalchemy.orm import Session

from core.database import Base, get_db, SessionLocal

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS - model names and pricing
# WHY: Centralized so price changes only need one edit.
#      Prices as of Feb 2026 - update if Anthropic changes rates.
# ============================================================

class AIModel(str, Enum):
    # Claude models (Anthropic)
    CLAUDE_SONNET = "claude-sonnet-4-6"       # Smart, more expensive
    CLAUDE_HAIKU = "claude-haiku-4-5-20251001" # Fast, cheap - use for iteration

    # OpenAI models (ChatGPT)
    GPT4O = "gpt-4o"                    # Business/narrative tasks (Big Brain)
    GPT4O_MINI = "gpt-4o-mini"          # Cheap GPT fallback


# Cost per 1M tokens (USD) - input / output
MODEL_PRICING = {
    AIModel.CLAUDE_SONNET: {"input": 3.00,  "output": 15.00},
    AIModel.CLAUDE_HAIKU:  {"input": 0.25,  "output": 1.25},
    AIModel.GPT4O:         {"input": 2.50,  "output": 10.00},
    AIModel.GPT4O_MINI:    {"input": 0.15,  "output": 0.60},
}

# Default budget per tenant per month (USD)
DEFAULT_MONTHLY_BUDGET_USD = 100

# Alert threshold - notify admin when tenant hits this % of budget
BUDGET_ALERT_THRESHOLD = 0.90  # 90%


# ============================================================
# EXCEPTIONS
# ============================================================

class AIGovernanceError(Exception):
    """Base exception for AI governance violations."""
    pass


class BudgetExceededError(AIGovernanceError):
    """Raised when tenant's monthly AI budget is exhausted."""
    def __init__(self, tenant_id: str, spent: float, budget: float):
        self.tenant_id = tenant_id
        self.spent = spent
        self.budget = budget
        super().__init__(
            f"Tenant {tenant_id} AI budget exceeded: ${spent:.2f} of ${budget:.2f} used"
        )


class ModelNotAllowedError(AIGovernanceError):
    """Raised when tenant tier doesn't allow the requested model."""
    pass


# ============================================================
# DATABASE MODEL - ai_costs table
# WHY: Persistent record of every AI call. Used for:
#      - Dashboard (cost per tenant/feature/day)
#      - Budget enforcement (sum monthly spend)
#      - Billing (charge tenants for AI overage)
#      - Debugging runaway cost loops
# ============================================================

class AICostLog(Base):
    """
    One row per AI API call.
    This IS the source of truth for all AI spending.
    """
    __tablename__ = "ai_costs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    log_date = Column(Date, default=date.today, nullable=False, index=True,
                      comment="Date portion for fast daily aggregation queries")

    # WHO
    tenant_id = Column(String(64), nullable=False, index=True,
                       comment="Which tenant made this call")
    user_id = Column(String(128), nullable=True,
                     comment="Auth0 user_id if call is user-initiated")

    # WHAT
    feature = Column(String(128), nullable=False, index=True,
                     comment="Feature that triggered the call (e.g. game_summary, idea_intake)")
    model = Column(String(64), nullable=False,
                   comment="Model used: claude-sonnet-4-6, gpt-4o, etc.")
    provider = Column(String(32), nullable=False,
                      comment="anthropic | openai")

    # TOKENS & COST
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0,
                      comment="Calculated cost in USD")

    # PERFORMANCE
    duration_ms = Column(Integer, nullable=True,
                         comment="API call latency in milliseconds")
    success = Column(Integer, nullable=False, default=1,
                     comment="1=success, 0=error")
    error_msg = Column(Text, nullable=True,
                       comment="Error message if success=0")

    # For migrating fo_run_log.csv data
    run_label = Column(String(255), nullable=True,
                       comment="Optional label (e.g. FounderOps startup name)")

    def __repr__(self):
        return (
            f"<AICostLog {self.log_date} tenant={self.tenant_id} "
            f"feature={self.feature} cost=${self.cost_usd:.4f}>"
        )


# ============================================================
# COST CALCULATION
# WHY: Deterministic. Pricing table is the source of truth.
# ============================================================

def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """
    Calculate cost in USD for an AI call.
    Returns 0.0 if model not in pricing table (log a warning).
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        logger.warning(f"No pricing data for model: {model}. Cost logged as 0.")
        return 0.0

    cost = (tokens_in / 1_000_000 * pricing["input"]) + \
           (tokens_out / 1_000_000 * pricing["output"])
    return round(cost, 6)


# ============================================================
# BUDGET ENFORCEMENT
# WHY: Hard stop before each AI call. Never exceed budget.
#      Soft alert at 90% so admin can intervene.
# ============================================================

def get_monthly_spend(db: Session, tenant_id: str) -> float:
    """
    Sum all AI costs for tenant in current calendar month.
    Called before every AI request.
    """
    from sqlalchemy import func, extract
    from sqlalchemy.sql import and_

    today = date.today()
    result = db.query(func.sum(AICostLog.cost_usd)).filter(
        and_(
            AICostLog.tenant_id == tenant_id,
            extract("year", AICostLog.log_date) == today.year,
            extract("month", AICostLog.log_date) == today.month,
        )
    ).scalar()

    return float(result or 0.0)


def get_tenant_budget(db: Session, tenant_id: str) -> float:
    """
    Get monthly AI budget for tenant from Tenant table.
    Falls back to DEFAULT_MONTHLY_BUDGET_USD if tenant not found.
    """
    try:
        from core.tenancy import Tenant
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant and tenant.monthly_ai_budget_usd:
            return float(tenant.monthly_ai_budget_usd)
    except Exception as e:
        logger.warning(f"Could not load tenant budget from DB: {e}")

    return float(DEFAULT_MONTHLY_BUDGET_USD)


def check_budget(db: Session, tenant_id: str) -> Dict[str, Any]:
    """
    Check if tenant is within budget. Sends alert at 90%, blocks at 100%.

    Returns:
        {"allowed": True, "spend": 45.50, "budget": 100.0, "pct": 0.455}
        {"allowed": False, ...} if at/over budget

    Raises:
        BudgetExceededError if over budget
    """
    spend = get_monthly_spend(db, tenant_id)
    budget = get_tenant_budget(db, tenant_id)

    # Budget of 0 means unlimited
    if budget == 0:
        return {"allowed": True, "spend": spend, "budget": 0, "pct": 0.0, "unlimited": True}

    pct = spend / budget if budget > 0 else 0.0

    result = {"allowed": True, "spend": spend, "budget": budget, "pct": pct}

    if pct >= 1.0:
        # HARD STOP
        logger.error(
            f"BUDGET EXCEEDED: tenant={tenant_id} spent=${spend:.2f} budget=${budget:.2f}"
        )
        raise BudgetExceededError(tenant_id=tenant_id, spent=spend, budget=budget)

    if pct >= BUDGET_ALERT_THRESHOLD:
        # SOFT ALERT - log + notify (fire and forget, don't block the call)
        logger.warning(
            f"BUDGET ALERT: tenant={tenant_id} at {pct:.0%} of ${budget:.2f} "
            f"(${spend:.2f} spent)"
        )
        result["alert"] = True
        # TODO: Wire up email alert via mailerlite_lib when admin email is configured
        # _send_budget_alert(tenant_id, spend, budget, pct)

    return result


# ============================================================
# MODEL ROUTING
# WHY: Route cheap/repetitive tasks to Haiku, complex/important
#      tasks to Sonnet. Saves ~80% on cost for iterative workflows.
#      Tenant tier also controls which models are available.
# ============================================================

# Task type → preferred model
TASK_MODEL_MAP = {
    # Cheap tasks → Haiku
    "qa_iteration": AIModel.CLAUDE_HAIKU,     # FounderOps QA loops
    "validation": AIModel.CLAUDE_HAIKU,        # Simple checks
    "formatting": AIModel.CLAUDE_HAIKU,        # Output formatting
    "classification": AIModel.CLAUDE_HAIKU,    # Simple categorization
    "extraction": AIModel.CLAUDE_HAIKU,        # Pulling structured data

    # Smart tasks → Sonnet
    "generation": AIModel.CLAUDE_SONNET,       # Creative/complex generation
    "analysis": AIModel.CLAUDE_SONNET,         # Deep analysis
    "summarization": AIModel.CLAUDE_SONNET,    # Summarizing long content
    "planning": AIModel.CLAUDE_SONNET,         # Strategic planning
    "code_review": AIModel.CLAUDE_SONNET,      # Code analysis

    # Business/narrative tasks → GPT-4o (Big Brain pattern)
    "business_strategy": AIModel.GPT4O,
    "narrative": AIModel.GPT4O,
    "market_analysis": AIModel.GPT4O,
}

# Tier restrictions - which models each tier can access
TIER_ALLOWED_MODELS = {
    "basic": {AIModel.CLAUDE_HAIKU, AIModel.GPT4O_MINI},
    "pro": {AIModel.CLAUDE_HAIKU, AIModel.CLAUDE_SONNET, AIModel.GPT4O_MINI, AIModel.GPT4O},
    "enterprise": set(AIModel),  # All models
}

# Default model if task type not in map
DEFAULT_MODEL = AIModel.CLAUDE_HAIKU


def route_model(task_type: str, tenant_tier: str = "pro") -> str:
    """
    Select the optimal model based on task type and tenant tier.

    Logic:
    1. Look up preferred model for task_type
    2. Check if tenant tier allows that model
    3. Downgrade to best allowed model if not permitted
    4. Return model string

    Args:
        task_type: One of TASK_MODEL_MAP keys (or "general" for default)
        tenant_tier: "basic" | "pro" | "enterprise"

    Returns:
        Model string (e.g. "claude-haiku-4-5-20251001")
    """
    preferred = TASK_MODEL_MAP.get(task_type, DEFAULT_MODEL)
    allowed = TIER_ALLOWED_MODELS.get(tenant_tier, TIER_ALLOWED_MODELS["basic"])

    if preferred in allowed:
        logger.debug(f"Routing task={task_type} tier={tenant_tier} → {preferred}")
        return preferred

    # Downgrade to best model available for this tier
    # Priority order: sonnet > haiku > gpt4o_mini
    fallback_order = [
        AIModel.CLAUDE_SONNET,
        AIModel.CLAUDE_HAIKU,
        AIModel.GPT4O_MINI,
    ]
    for model in fallback_order:
        if model in allowed:
            logger.info(
                f"Downgraded model for tier={tenant_tier}: {preferred} → {model}"
            )
            return model

    # Should never reach here, but safety fallback
    return AIModel.CLAUDE_HAIKU


# ============================================================
# MAIN ENTRY POINT - call_ai()
# WHY: Single choke point for all AI calls. No exceptions.
# ============================================================

def call_ai(
    prompt: str,
    tenant_id: str,
    feature: str,
    task_type: str = "generation",
    system_prompt: Optional[str] = None,
    model_override: Optional[str] = None,   # Admin can force a specific model
    tenant_tier: str = "pro",
    user_id: Optional[str] = None,
    max_tokens: int = 2048,
    run_label: Optional[str] = None,        # For FounderOps run tracking
) -> Dict[str, Any]:
    """
    THE only way to make AI calls in this platform.
    Platform Rule #3: All AI calls MUST pass through this function.

    Steps:
    1. Check budget - raises BudgetExceededError if over limit
    2. Route to correct model
    3. Make API call (Claude or GPT)
    4. Calculate cost
    5. Log to ai_costs table
    6. Return response + metadata

    Args:
        prompt: The user/task prompt
        tenant_id: Which tenant is making this call (for billing/budget)
        feature: What feature triggered this (e.g. "game_summary", "idea_intake")
        task_type: Task classification for model routing
        system_prompt: Optional system prompt
        model_override: Force a specific model (admin use only)
        tenant_tier: Tenant's plan tier for model routing
        user_id: Auth0 user ID if user-initiated
        max_tokens: Max response tokens
        run_label: Optional label for batch jobs

    Returns:
        {
            "content": "AI response text",
            "model": "claude-haiku-4-5-20251001",
            "tokens_in": 150,
            "tokens_out": 300,
            "cost_usd": 0.000425,
            "duration_ms": 1250
        }

    Raises:
        BudgetExceededError: If tenant's monthly budget is exhausted
        AIGovernanceError: For other governance violations
        Exception: Re-raises API errors after logging
    """
    start_time = time.time()
    db = SessionLocal()

    try:
        # STEP 1: Budget check - HARD STOP if over budget
        budget_info = check_budget(db, tenant_id)
        logger.debug(
            f"Budget check passed: tenant={tenant_id} "
            f"${budget_info['spend']:.2f}/${budget_info['budget']:.2f}"
        )

        # STEP 2: Model routing
        if model_override:
            model = model_override
            logger.info(f"Model override by admin: {model}")
        else:
            model = route_model(task_type, tenant_tier)

        # Determine provider from model name
        provider = "anthropic" if "claude" in model.lower() else "openai"

        # STEP 3: Make the actual API call
        tokens_in, tokens_out, content = 0, 0, ""

        if provider == "anthropic":
            tokens_in, tokens_out, content = _call_claude(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens
            )
        else:
            tokens_in, tokens_out, content = _call_openai(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens
            )

        # STEP 4: Calculate cost
        cost_usd = calculate_cost(model, tokens_in, tokens_out)
        duration_ms = int((time.time() - start_time) * 1000)

        # STEP 5: Log to DB
        log_entry = AICostLog(
            tenant_id=tenant_id,
            user_id=user_id,
            feature=feature,
            model=model,
            provider=provider,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            success=1,
            run_label=run_label,
            log_date=date.today(),
        )
        db.add(log_entry)
        db.commit()

        logger.info(
            f"AI call: tenant={tenant_id} feature={feature} model={model} "
            f"cost=${cost_usd:.4f} tokens={tokens_in}+{tokens_out} duration={duration_ms}ms"
        )

        # STEP 6: Return
        return {
            "content": content,
            "model": model,
            "provider": provider,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
        }

    except BudgetExceededError:
        # Log the blocked attempt, then re-raise
        _log_failed_call(db, tenant_id, feature, "budget_exceeded", run_label)
        raise

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        _log_failed_call(db, tenant_id, feature, str(e), run_label, duration_ms)
        logger.error(f"AI call failed: tenant={tenant_id} feature={feature} error={e}")
        raise

    finally:
        db.close()


def _log_failed_call(
    db: Session,
    tenant_id: str,
    feature: str,
    error_msg: str,
    run_label: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> None:
    """Log a failed AI call attempt. Best-effort - don't raise."""
    try:
        log_entry = AICostLog(
            tenant_id=tenant_id,
            feature=feature,
            model="unknown",
            provider="unknown",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            duration_ms=duration_ms,
            success=0,
            error_msg=error_msg[:1000],  # Truncate long errors
            run_label=run_label,
            log_date=date.today(),
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log AI call error to DB: {e}")


# ============================================================
# PROVIDER-SPECIFIC API CALLS
# WHY: Isolated here so only ai_governance.py touches the SDKs.
#      Swap providers by updating these functions only.
# ============================================================

def _call_claude(
    prompt: str,
    system_prompt: Optional[str],
    model: str,
    max_tokens: int
) -> tuple[int, int, str]:
    """
    Call Anthropic Claude API.
    Returns: (tokens_in, tokens_out, content_text)
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)

    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    content = response.content[0].text if response.content else ""

    return tokens_in, tokens_out, content


def _call_openai(
    prompt: str,
    system_prompt: Optional[str],
    model: str,
    max_tokens: int
) -> tuple[int, int, str]:
    """
    Call OpenAI GPT API.
    Returns: (tokens_in, tokens_out, content_text)
    """
    import openai

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )

    tokens_in = response.usage.prompt_tokens
    tokens_out = response.usage.completion_tokens
    content = response.choices[0].message.content or ""

    return tokens_in, tokens_out, content


# ============================================================
# REPORTING HELPERS - for dashboard and admin queries
# ============================================================

def get_cost_summary(
    db: Session,
    tenant_id: Optional[str] = None,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get cost summary for dashboard.

    If tenant_id is None: returns platform-wide summary (admin only)
    If tenant_id is set: returns that tenant's costs

    Returns aggregated data suitable for charting.
    """
    from sqlalchemy import func
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(
        AICostLog.tenant_id,
        AICostLog.feature,
        AICostLog.model,
        AICostLog.log_date,
        func.sum(AICostLog.cost_usd).label("total_cost"),
        func.sum(AICostLog.tokens_in).label("total_tokens_in"),
        func.sum(AICostLog.tokens_out).label("total_tokens_out"),
        func.count(AICostLog.id).label("call_count"),
    ).filter(AICostLog.created_at >= cutoff)

    if tenant_id:
        query = query.filter(AICostLog.tenant_id == tenant_id)

    results = query.group_by(
        AICostLog.tenant_id,
        AICostLog.feature,
        AICostLog.model,
        AICostLog.log_date,
    ).all()

    rows = [
        {
            "tenant_id": r.tenant_id,
            "feature": r.feature,
            "model": r.model,
            "date": str(r.log_date),
            "total_cost_usd": round(float(r.total_cost or 0), 4),
            "call_count": r.call_count,
            "total_tokens_in": r.total_tokens_in,
            "total_tokens_out": r.total_tokens_out,
        }
        for r in results
    ]

    total_cost = sum(r["total_cost_usd"] for r in rows)

    return {
        "tenant_id": tenant_id or "all",
        "days": days,
        "total_cost_usd": round(total_cost, 4),
        "rows": rows,
    }


def migrate_fo_run_log(db: Session, csv_path: str, tenant_id: str = "founderops") -> int:
    """
    One-time migration: import fo_run_log.csv into ai_costs table.

    CSV schema: date, startup, iterations, cost_claude, cost_chatgpt, total_cost
    Returns count of rows imported.
    """
    import csv

    count = 0
    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                log_date = datetime.strptime(row["date"], "%Y-%m-%d").date()

                # Claude costs
                if float(row.get("cost_claude", 0)) > 0:
                    db.add(AICostLog(
                        tenant_id=tenant_id,
                        feature="fo_build",
                        model=AIModel.CLAUDE_SONNET,
                        provider="anthropic",
                        tokens_in=0,  # Not in CSV
                        tokens_out=0,
                        cost_usd=float(row["cost_claude"]),
                        success=1,
                        run_label=row.get("startup"),
                        log_date=log_date,
                        created_at=datetime.combine(log_date, datetime.min.time())
                    ))
                    count += 1

                # ChatGPT costs
                if float(row.get("cost_chatgpt", 0)) > 0:
                    db.add(AICostLog(
                        tenant_id=tenant_id,
                        feature="fo_build",
                        model=AIModel.GPT4O,
                        provider="openai",
                        tokens_in=0,
                        tokens_out=0,
                        cost_usd=float(row["cost_chatgpt"]),
                        success=1,
                        run_label=row.get("startup"),
                        log_date=log_date,
                        created_at=datetime.combine(log_date, datetime.min.time())
                    ))
                    count += 1

        db.commit()
        logger.info(f"Migrated {count} rows from {csv_path} to ai_costs")
        return count

    except FileNotFoundError:
        logger.warning(f"fo_run_log.csv not found at {csv_path} - skipping migration")
        return 0
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
