"""
SaaS Boilerplate - FastAPI Backend (with Auto-Loader & Database)
=================================================================

Main application with:
- Auto-loading of business routes
- Database integration
- All library integrations
- P0 Kernel: multi-tenancy, AI governance, RBAC, error tracking,
  usage limits, capability registry

Usage:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
import json
import os
import logging

# Import shared libraries
import sys
sys.path.append('../libs')

from stripe_lib import load_stripe_lib
from mailerlite_lib import load_mailerlite_lib
from auth0_lib import load_auth0_lib
from analytics_lib import load_analytics_lib

# Import core modules
from core.loader import load_business_routes, get_loaded_business_routes
from core.database import init_db, get_db

# Import P0 kernel modules
# NOTE: Models must be imported BEFORE init_db() so SQLAlchemy creates their tables.
from core.tenancy import tenant_middleware, Tenant
from core.monitoring import init_monitoring, monitoring_middleware
from core.capability_loader import load_capabilities, validate_p0_capabilities
from core.ai_governance import AICostLog
from core.usage_limits import UsageCounter
from core.expense_tracking import ExpenseLog, log_expense, get_expense_summary, get_pl_summary
from core.rbac import require_role, get_current_user
from core.listings import (
    Listing, LISTING_STATUSES,
    create_listing, get_listing, list_listings, update_listing,
    delete_listing, listing_to_search_doc,
)
from core.purchase_delivery import (
    PurchaseRecord, deliver_purchase, has_purchased, get_purchases_for_buyer,
)
from core.entitlements import UserEntitlement

# P1 Lifecycle modules (must be imported before init_db for table creation)
from core.onboarding import OnboardingState, get_or_create_onboarding, mark_step_complete, is_onboarding_complete
from core.trial import TrialRecord, start_trial, get_trial, is_trial_active, mark_trial_converted, mark_trial_expired
from core.activation import ActivationEvent, record_activation, is_activated, get_activation_events
from core.offboarding import OffboardingRecord, initiate_offboarding, complete_offboarding, get_offboarding_record
from core.account_closure import AccountClosure, initiate_closure, cancel_closure, get_closure_request, get_pending_purges, execute_purge

# P1 Legal Consent modules (must be imported before init_db for table creation)
from core.legal_consent import (
    LegalDocVersion, UserConsent, ConsentAuditLog,
    set_current_version, get_current_version,
    record_consent, get_user_consent,
    requires_reacceptance, get_consent_status,
    require_fresh_consent, get_audit_log,
    DOC_TYPE_TERMS, DOC_TYPE_PRIVACY,
)

# P1 Fraud & Abuse modules (must be imported before init_db for table creation)
from core.fraud import (
    FraudEvent, AccountLockout,
    record_fraud_event, get_fraud_events, resolve_fraud_event,
    lock_account, unlock_account, is_account_locked,
    detect_ai_abuse, detect_api_abuse, detect_self_referral,
    FRAUD_EVENT_TYPES, FRAUD_SEVERITIES,
)
from core.ip_throttle import IPThrottleMiddleware, auth_rate_limit_dependency
from core.financial_governance import (
    StripeTransactionRecord, ReconciliationRecord,
    record_stripe_transaction, get_stripe_fee_summary,
    get_gross_margin, reconcile_period, get_reconciliation,
    list_reconciliations, export_accounting_csv,
    TRANSACTION_TYPES, RECONCILIATION_STATUSES,
)
from core.data_retention import (
    RetentionPolicy, ArchivedRecord, DataDeletionRequest,
    set_retention_policy, get_retention_days, list_retention_policies,
    purge_expired_logs, apply_retention_rules,
    archive_tenant_data, list_archives,
    request_data_deletion, complete_deletion,
    get_overdue_deletions, get_deletion_request, list_deletion_requests,
    RETENTION_DEFAULTS, DELETION_SLA_DAYS, LOG_DATA_TYPES, COMPLIANCE_DATA_TYPES,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

# Load business config
with open('config/business_config.json', 'r') as f:
    BUSINESS_CONFIG = json.load(f)

# Initialize libraries
stripe = load_stripe_lib('config/stripe_config.json')
mailer = load_mailerlite_lib('config/mailerlite_config.json')
auth0 = load_auth0_lib('config/auth0_config.json')
analytics = load_analytics_lib('config/analytics_config.json')

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title=BUSINESS_CONFIG["business"]["name"],
    description=BUSINESS_CONFIG["business"]["description"],
    version="2.0.0"
)

# CORS middleware — explicit origin, method, and header whitelist (never use ["*"] in production)
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# P1 IP throttle + bot filter (BaseHTTPMiddleware — registered via add_middleware)
app.add_middleware(IPThrottleMiddleware, limit=100, window=60)

# P0 Kernel middleware
# Registration order matters: last registered = outermost = runs first.
# monitoring_middleware must be registered first so tenant_middleware runs before it.
app.middleware("http")(monitoring_middleware)  # runs second: sets Sentry context from tenant
app.middleware("http")(tenant_middleware)       # runs first: extracts tenant_id from JWT/header

# ============================================================
# MODELS
# ============================================================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

class SubscribeRequest(BaseModel):
    price_id: str
    user_id: str

class EventTrackRequest(BaseModel):
    event_name: str
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    event_params: Optional[Dict[str, Any]] = None

class ExpenseRequest(BaseModel):
    tenant_id: str
    category: str
    amount_usd: float
    source: str
    description: Optional[str] = None
    product_name: Optional[str] = None
    is_recurring: bool = False

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    business_routes = get_loaded_business_routes(app)
    
    return {
        "status": "healthy",
        "business": BUSINESS_CONFIG["business"]["name"],
        "version": "2.0.0",
        "features": {
            "auto_loader": True,
            "database": True,
            "business_routes_loaded": len(business_routes)
        }
    }

# ============================================================
# CONFIGURATION ENDPOINTS
# ============================================================

@app.get("/api/config")
async def get_config():
    """Get client-safe configuration"""
    return {
        "business": BUSINESS_CONFIG["business"],
        "branding": BUSINESS_CONFIG["branding"],
        "home": BUSINESS_CONFIG["home"],
        "pricing": {
            "headline": BUSINESS_CONFIG["pricing"]["headline"],
            "subheadline": BUSINESS_CONFIG["pricing"]["subheadline"],
            "plans": BUSINESS_CONFIG["pricing"]["plans"],
            "faq": BUSINESS_CONFIG["pricing"]["faq"]
        },
        "faq": BUSINESS_CONFIG["faq"],
        "footer": BUSINESS_CONFIG["footer"],
        "metadata": BUSINESS_CONFIG["metadata"]
    }

@app.get("/api/config/{page}")
async def get_page_config(page: str):
    """Get configuration for specific page"""
    if page in BUSINESS_CONFIG:
        return BUSINESS_CONFIG[page]
    raise HTTPException(status_code=404, detail=f"Page '{page}' not found")

# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/api/auth/signup")
async def signup(request: SignupRequest, _rl=Depends(auth_rate_limit_dependency), _csrf=Depends(require_ajax_header)):
    """Create new user account via Auth0"""
    try:
        user_result = auth0.create_user(
            email=request.email,
            password=request.password,
            user_metadata={"name": request.name}
        )
        
        if not user_result["success"]:
            raise HTTPException(
                status_code=400,
                detail="Failed to create account"
            )
        
        user_id = user_result["data"]["user_id"]
        
        mailer.add_subscriber(
            email=request.email,
            fields={"name": request.name}
        )
        
        analytics.track_signup(
            user_id=user_id,
            signup_method="email",
            user_properties={"plan": "free"}
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "Account created successfully"
        }
    
    except Exception as e:
        logger.error(f"Internal error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/auth/send-verification")
async def send_verification(user_id: str, _rl=Depends(auth_rate_limit_dependency), _csrf=Depends(require_ajax_header), _consent=Depends(require_fresh_consent)):
    """Send email verification to user"""
    result = auth0.send_verification_email(user_id=user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail="Request failed")
    
    return {"success": True, "message": "Verification email sent"}

@app.post("/api/auth/password-reset")
async def password_reset(email: EmailStr, _rl=Depends(auth_rate_limit_dependency), _csrf=Depends(require_ajax_header), _consent=Depends(require_fresh_consent)):
    """Trigger password reset flow"""
    result = auth0.send_password_reset_email(email=email)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail="Request failed")
    
    return {"success": True, "message": "Password reset email sent"}

# ============================================================
# SUBSCRIPTION ENDPOINTS
# ============================================================

@app.post("/api/subscribe")
async def create_subscription(request: SubscribeRequest):
    """Create Stripe checkout session for subscription"""
    try:
        plan = None
        for p in BUSINESS_CONFIG["pricing"]["plans"]:
            if p.get("stripe_price_id_monthly") == request.price_id or \
               p.get("stripe_price_id_annual") == request.price_id:
                plan = p
                break
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        analytics.track_begin_checkout(
            value=plan["price_monthly"],
            user_id=request.user_id
        )
        
        return {
            "success": True,
            "payment_link": f"https://checkout.stripe.com/pay/{request.price_id}",
            "message": "Redirecting to checkout..."
        }
    
    except Exception as e:
        logger.error(f"Internal error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/cancel-subscription")
async def cancel_subscription(subscription_id: str, user_id: str):
    """Cancel user's subscription"""
    try:
        result = stripe.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=True
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail="Request failed")
        
        analytics.track_subscription_cancel(
            subscription_id=subscription_id,
            plan_name="Unknown",
            user_id=user_id
        )
        
        return {
            "success": True,
            "message": "Subscription will cancel at period end"
        }
    
    except Exception as e:
        logger.error(f"Internal error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================
# STRIPE WEBHOOK
# ============================================================

@app.post("/api/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db=Depends(get_db),
):
    """Handle Stripe webhooks for payment events"""
    try:
        body = await request.body()

        verify_result = stripe.verify_webhook_signature(
            payload=body,
            signature_header=stripe_signature
        )

        if not verify_result["success"]:
            raise HTTPException(status_code=400, detail="Invalid signature")

        event = verify_result["event"]

        analytics.track_stripe_webhook(
            event_type=event["type"],
            stripe_event=event
        )

        if event["type"] == "customer.subscription.created":
            subscription = event["data"]["object"]
            stripe_customer_id = subscription.get("customer")
            user_id = subscription.get("metadata", {}).get("user_id")
            if user_id and stripe_customer_id:
                logger.info(f"Webhook sub.created: customer={stripe_customer_id} user={user_id}")
                auth0.update_user(
                    user_id=user_id,
                    app_metadata={"subscription_status": "active", "stripe_customer_id": stripe_customer_id}
                )
            elif not user_id:
                logger.warning(f"Webhook sub.created missing user_id: customer={stripe_customer_id}")

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            stripe_customer_id = subscription.get("customer")
            user_id = subscription.get("metadata", {}).get("user_id")
            if user_id and stripe_customer_id:
                logger.info(f"Webhook sub.deleted: customer={stripe_customer_id} user={user_id}")
                auth0.update_user(
                    user_id=user_id,
                    app_metadata={"subscription_status": "cancelled"}
                )
            elif not user_id:
                logger.warning(f"Webhook sub.deleted missing user_id: customer={stripe_customer_id}")
            # Mark trial expired if subscription was in trial
            if subscription.get("trial_end") and user_id:
                try:
                    mark_trial_expired(db, user_id)
                except Exception as e:
                    logger.error(f"mark_trial_expired failed: {e}")

        elif event["type"] == "customer.subscription.trial_will_end":
            subscription = event["data"]["object"]
            logger.warning(
                f"Trial ending soon: sub={subscription.get('id')} "
                f"customer={subscription.get('customer')}"
            )

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            stripe_customer_id = subscription.get("customer")
            previous = event["data"].get("previous_attributes", {})
            # Detect trialing → active conversion
            if (previous.get("status") == "trialing"
                    and subscription.get("status") == "active"):
                user_id = subscription.get("metadata", {}).get("user_id")
                if user_id and stripe_customer_id:
                    logger.info(f"Webhook sub.converted: customer={stripe_customer_id} user={user_id}")
                    try:
                        mark_trial_converted(db, user_id)
                    except Exception as e:
                        logger.error(f"mark_trial_converted failed: {e}")

        elif event["type"] == "charge.dispute.created":
            dispute = event["data"]["object"]
            user_id = dispute.get("metadata", {}).get("user_id")
            try:
                record_fraud_event(
                    db=db,
                    auth0_user_id=user_id,
                    tenant_id=user_id,
                    event_type="stripe_dispute",
                    severity="high",
                    source="stripe",
                    detail={
                        "dispute_id": dispute.get("id"),
                        "charge": dispute.get("charge"),
                        "amount": dispute.get("amount"),
                        "reason": dispute.get("reason"),
                    },
                )
                logger.warning(f"Stripe dispute recorded: {dispute.get('id')}")
            except Exception as e:
                logger.error(f"Failed to record stripe dispute: {e}")

        elif event["type"] == "charge.succeeded":
            # #37: Record Stripe fee attribution per charge.
            # balance_transaction is an object if expanded in webhook settings, else just an ID.
            charge = event["data"]["object"]
            tenant_id = charge.get("metadata", {}).get("tenant_id")
            if tenant_id:
                try:
                    gross = charge.get("amount", 0) / 100.0
                    btxn = charge.get("balance_transaction")
                    fee = (btxn.get("fee", 0) / 100.0) if isinstance(btxn, dict) else 0.0
                    record_stripe_transaction(
                        db=db,
                        tenant_id=tenant_id,
                        gross_usd=gross,
                        fee_usd=fee,
                        transaction_type="charge",
                        stripe_charge_id=charge.get("id"),
                        stripe_payment_intent_id=charge.get("payment_intent"),
                        stripe_balance_txn_id=btxn.get("id") if isinstance(btxn, dict) else btxn,
                        description=charge.get("description"),
                    )
                    logger.info(f"Stripe charge recorded: {charge.get('id')} gross={gross} fee={fee}")
                except Exception as e:
                    logger.error(f"Failed to record Stripe charge: {e}")

        elif event["type"] == "radar.early_fraud_warning.created":
            warning = event["data"]["object"]
            user_id = warning.get("metadata", {}).get("user_id")
            try:
                record_fraud_event(
                    db=db,
                    auth0_user_id=user_id,
                    tenant_id=user_id,
                    event_type="stripe_early_fraud_warning",
                    severity="critical",
                    source="stripe",
                    detail={
                        "warning_id": warning.get("id"),
                        "charge": warning.get("charge"),
                        "fraud_type": warning.get("fraud_type"),
                    },
                )
                logger.warning(f"Stripe fraud warning recorded: {warning.get('id')}")
            except Exception as e:
                logger.error(f"Failed to record stripe fraud warning: {e}")

        return {"success": True}

    except Exception as e:
        logger.error(f"Internal error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================
# ANALYTICS ENDPOINTS
# ============================================================

@app.post("/api/analytics/track")
async def track_event(request: EventTrackRequest):
    """Track custom analytics event"""
    try:
        result = analytics.track_event(
            event_name=request.event_name,
            client_id=request.client_id,
            user_id=request.user_id,
            event_params=request.event_params
        )
        
        if not result["success"]:
            logger.warning(f"Analytics error: {result.get('error')}")
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"Analytics exception: {str(e)}")
        return {"success": True}

@app.post("/api/analytics/page-view")
async def track_page_view(
    page_path: str,
    page_title: Optional[str] = None,
    user_id: Optional[str] = None,
    client_id: Optional[str] = None
):
    """Track page view"""
    try:
        analytics.track_page_view(
            page_path=page_path,
            page_title=page_title,
            client_id=client_id,
            user_id=user_id
        )
        return {"success": True}
    except:
        return {"success": True}

# ============================================================
# CONTACT FORM
# ============================================================

@app.post("/api/contact")
async def contact_form(request: ContactRequest):
    """Handle contact form submission"""
    try:
        mailer.add_subscriber(
            email=request.email,
            fields={
                "name": request.name,
                "contact_subject": request.subject
            }
        )
        
        analytics.track_event(
            event_name="contact_form_submit",
            event_params={
                "subject": request.subject
            }
        )
        
        return {
            "success": True,
            "message": "Thanks! We'll get back to you within 24 hours."
        }
    
    except Exception as e:
        logger.error(f"Internal error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================
# USER MANAGEMENT
# ============================================================

async def require_ajax_header(request: Request) -> None:
    """Require X-Requested-With header on state-changing requests — blocks naive cross-origin form posts."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if not request.headers.get("x-requested-with"):
            raise HTTPException(status_code=403, detail="Missing X-Requested-With header")


def _assert_self_or_admin(caller: dict, user_id: str) -> None:
    """Raise 403 unless the caller is the target user or has the admin role."""
    is_admin = "admin" in caller.get("roles", set())
    is_self = caller.get("sub") == user_id
    if not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied")


@app.get("/api/user/{user_id}")
async def get_user(user_id: str, caller: dict = Depends(get_current_user)):
    """Get user details. Users may only fetch their own record; admins may fetch any."""
    _assert_self_or_admin(caller, user_id)
    result = auth0.get_user(user_id=user_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="User not found")
    return result["data"]

@app.put("/api/user/{user_id}")
async def update_user(user_id: str, user_metadata: Dict[str, Any], caller: dict = Depends(get_current_user)):
    """Update user metadata. Users may only update their own record; admins may update any."""
    _assert_self_or_admin(caller, user_id)
    result = auth0.update_user(user_id=user_id, user_metadata=user_metadata)
    if not result["success"]:
        raise HTTPException(status_code=400, detail="Update failed")
    return {"success": True, "data": result["data"]}

@app.delete("/api/user/{user_id}")
async def delete_user(user_id: str, caller: dict = Depends(get_current_user)):
    """Delete user account. Users may only delete their own account; admins may delete any."""
    _assert_self_or_admin(caller, user_id)
    result = auth0.delete_user(user_id=user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail="Delete failed")
    analytics.track_event(event_name="account_deleted", user_id=user_id)
    return {"success": True, "message": "Account deleted"}

# ============================================================
# ADMIN ENDPOINTS (require admin role)
# All routes prefixed /api/admin — protected via require_role("admin")
# ============================================================

@app.get("/api/admin/users")
async def admin_list_users(
    limit: int = 50,
    _user=Depends(require_role("admin")),
):
    """List all Auth0 users. Admin-only."""
    result = auth0.list_users(per_page=limit)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail="Service unavailable")
    return {"users": result.get("data", []), "total": len(result.get("data", []))}


@app.get("/api/admin/tenants")
async def admin_list_tenants(
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """List all tenants with basic usage summary. Admin-only."""
    tenants = db.query(Tenant).all()
    result = []
    for tenant in tenants:
        usage = db.query(UsageCounter).filter(
            UsageCounter.tenant_id == tenant.tenant_id
        ).all()
        result.append({
            "tenant_id": tenant.tenant_id,
            "plan_tier": tenant.plan_tier,
            "is_active": tenant.is_active,
            "created_at": str(tenant.created_at),
            "usage": [
                {"feature": u.feature, "count": u.count, "period_key": u.period_key}
                for u in usage
            ],
        })
    return {"tenants": result, "total": len(result)}


@app.get("/api/admin/billing/subscriptions")
async def admin_list_subscriptions(
    limit: int = 100,
    _user=Depends(require_role("admin")),
):
    """List active Stripe subscriptions. Admin-only."""
    try:
        import stripe as stripe_module
        subs = stripe_module.Subscription.list(limit=limit, status="active")
        return {
            "subscriptions": [s for s in subs.auto_paging_iter()],
            "total": len(subs.data),
        }
    except Exception as e:
        logger.error(f"Stripe error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail="Payment processing error")


@app.get("/api/admin/expenses")
async def admin_get_expenses(
    month: Optional[str] = None,
    tenant_id: Optional[str] = None,
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Get expense summary. Filter by month (YYYY-MM) and/or tenant_id. Admin-only."""
    summary = get_expense_summary(db, month_key=month, tenant_id=tenant_id)
    return summary


@app.post("/api/admin/expenses")
async def admin_log_expense(
    request: ExpenseRequest,
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Manually log an operational expense. Admin-only."""
    try:
        entry = log_expense(
            db=db,
            tenant_id=request.tenant_id,
            category=request.category,
            amount_usd=request.amount_usd,
            source=request.source,
            description=request.description,
            product_name=request.product_name,
            is_recurring=request.is_recurring,
        )
        return {
            "success": True,
            "id": entry.id,
            "month_key": entry.month_key,
            "amount_usd": entry.amount_usd,
        }
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")


@app.get("/api/admin/pl")
async def admin_pl_summary(
    month: str,
    tenant_id: str,
    revenue_usd: float = 0.0,
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Get P&L summary for a tenant for a specific month. Admin-only."""
    summary = get_pl_summary(db, tenant_id=tenant_id, month_key=month, revenue_usd=revenue_usd)
    return summary


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# ============================================================
# STARTUP & SHUTDOWN
# ============================================================

# ============================================================
# LISTING CRUD ENDPOINTS
# ============================================================

class ListingRequest(BaseModel):
    title: str
    price_usd: float
    description: Optional[str] = None
    category: Optional[str] = None
    images: Optional[List[str]] = None
    status: str = "draft"
    tenant_id: str  # caller supplies their tenant


class ListingUpdateRequest(BaseModel):
    title: Optional[str] = None
    price_usd: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    images: Optional[List[str]] = None
    status: Optional[str] = None


def _listing_to_dict(listing: Listing) -> Dict[str, Any]:
    return {
        "id": listing.id,
        "tenant_id": listing.tenant_id,
        "seller_id": listing.seller_id,
        "title": listing.title,
        "description": listing.description,
        "price_usd": listing.price_usd,
        "category": listing.category,
        "images": listing.images_list(),
        "status": listing.status,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "updated_at": listing.updated_at.isoformat() if listing.updated_at else None,
    }


@app.post("/api/listings", tags=["listings"])
async def create_listing_endpoint(
    req: ListingRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Create a new marketplace listing."""
    try:
        listing = create_listing(
            db=db,
            tenant_id=req.tenant_id,
            seller_id=user.get("sub", "unknown"),
            title=req.title,
            price_usd=req.price_usd,
            description=req.description,
            category=req.category,
            images=req.images,
            status=req.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Index in MeiliSearch (non-blocking — failure must not break CRUD)
    try:
        from meilisearch_lib import load_meilisearch_lib
        ms = load_meilisearch_lib()
        ms.add_documents("listings", [listing_to_search_doc(listing)])
    except Exception:
        pass

    return _listing_to_dict(listing)


@app.get("/api/listings", tags=["listings"])
async def list_listings_endpoint(
    tenant_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db),
):
    """List marketplace listings with optional filters."""
    rows = list_listings(
        db=db,
        tenant_id=tenant_id,
        category=category,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"listings": [_listing_to_dict(r) for r in rows], "count": len(rows)}


@app.get("/api/listings/search", tags=["listings"])
async def search_listings_endpoint(
    q: str = "",
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Full-text search listings via MeiliSearch. Gracefully falls back to empty results if unconfigured."""
    try:
        import re as _re
        if category and not _re.match(r"^[a-zA-Z0-9_\- ]{1,64}$", category):
            raise HTTPException(status_code=400, detail="Invalid category value")
        from meilisearch_lib import load_meilisearch_lib
        ms = load_meilisearch_lib()
        filters = None
        if category:
            filters = f"category = '{category}'"
        result = ms.search("listings", q, filters=filters, limit=limit, offset=offset)
        if result["success"]:
            data = result["data"]
            return {
                "hits": data.get("hits", []),
                "estimated_total": data.get("estimatedTotalHits", 0),
                "query": q,
            }
        # MeiliSearch not configured — return empty
        return {"hits": [], "estimated_total": 0, "query": q, "note": result.get("error")}
    except Exception as exc:
        return {"hits": [], "estimated_total": 0, "query": q, "note": str(exc)}


@app.get("/api/listings/{listing_id}", tags=["listings"])
async def get_listing_endpoint(
    listing_id: int,
    tenant_id: Optional[str] = None,
    db=Depends(get_db),
):
    """Get a single listing by ID (public)."""
    listing = get_listing(db, listing_id, tenant_id=tenant_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_to_dict(listing)


@app.put("/api/listings/{listing_id}", tags=["listings"])
async def update_listing_endpoint(
    listing_id: int,
    req: ListingUpdateRequest,
    tenant_id: str,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Update a listing (seller or admin only)."""
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        listing = update_listing(db, listing_id, tenant_id=tenant_id, **fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Re-index in MeiliSearch
    try:
        from meilisearch_lib import load_meilisearch_lib
        ms = load_meilisearch_lib()
        ms.update_document("listings", listing_to_search_doc(listing))
    except Exception:
        pass

    return _listing_to_dict(listing)


@app.delete("/api/listings/{listing_id}", tags=["listings"])
async def delete_listing_endpoint(
    listing_id: int,
    tenant_id: str,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Delete a listing (seller or admin only)."""
    try:
        delete_listing(db, listing_id, tenant_id=tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Remove from MeiliSearch index
    try:
        from meilisearch_lib import load_meilisearch_lib
        ms = load_meilisearch_lib()
        ms.delete_document("listings", listing_id)
    except Exception:
        pass

    return {"deleted": True, "listing_id": listing_id}


# ============================================================
# PURCHASE DELIVERY ENDPOINTS
# ============================================================

class PurchaseRequest(BaseModel):
    listing_id: int
    tenant_id: str
    stripe_payment_intent_id: Optional[str] = None


@app.post("/api/purchases", tags=["purchases"])
async def create_purchase_endpoint(
    req: PurchaseRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Deliver a purchase — grants entitlement to the buyer."""
    buyer_id = user.get("sub", "unknown")
    try:
        record = deliver_purchase(
            db=db,
            buyer_auth0_id=buyer_id,
            listing_id=req.listing_id,
            tenant_id=req.tenant_id,
            stripe_payment_intent_id=req.stripe_payment_intent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": record.id,
        "listing_id": record.listing_id,
        "entitlement_key": record.entitlement_key,
        "delivered_at": record.delivered_at.isoformat() if record.delivered_at else None,
    }


@app.get("/api/purchases/my", tags=["purchases"])
async def my_purchases_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Return all purchases made by the authenticated user."""
    buyer_id = user.get("sub", "unknown")
    records = get_purchases_for_buyer(db, buyer_id)
    return {
        "purchases": [
            {
                "id": r.id,
                "listing_id": r.listing_id,
                "tenant_id": r.tenant_id,
                "entitlement_key": r.entitlement_key,
                "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@app.get("/api/purchases/{listing_id}/access", tags=["purchases"])
async def check_purchase_access_endpoint(
    listing_id: int,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Check whether the authenticated user has purchased a listing."""
    buyer_id = user.get("sub", "unknown")
    purchased = has_purchased(db, buyer_id, listing_id)
    return {"listing_id": listing_id, "has_access": purchased}


# ============================================================
# P1 LIFECYCLE ENDPOINTS
# ============================================================

class TrialStartRequest(BaseModel):
    price_id: str
    trial_days: int = 14

class ActivationEventRequest(BaseModel):
    event_name: str
    metadata: Optional[Dict[str, Any]] = None

class OffboardingInitiateRequest(BaseModel):
    reason: str
    feedback: Optional[str] = None
    cancel_at_period_end: bool = True

class AccountCloseRequest(BaseModel):
    reason: Optional[str] = None

class ConsentAcceptRequest(BaseModel):
    doc_type: str
    version: str

class AdminSetVersionRequest(BaseModel):
    doc_type: str
    version: str

class FraudLockoutRequest(BaseModel):
    auth0_user_id: str
    reason: str

class FraudEventResolveRequest(BaseModel):
    event_id: int


# ---- Onboarding ----

@app.get("/api/onboarding", tags=["lifecycle"])
async def get_onboarding_state_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
    _consent=Depends(require_fresh_consent),
):
    """Get or create onboarding state for the authenticated user."""
    auth0_user_id = user["sub"]
    tenant_id = user.get("tenant_id", auth0_user_id)
    state = get_or_create_onboarding(db, auth0_user_id, tenant_id)
    return {
        "auth0_user_id": state.auth0_user_id,
        "completed_steps": state.get_steps(),
        "is_complete": state.is_complete,
        "completed_at": state.completed_at.isoformat() if state.completed_at else None,
    }


@app.post("/api/onboarding/step/{step}", tags=["lifecycle"])
async def complete_onboarding_step_endpoint(
    step: str,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Mark an onboarding step complete."""
    auth0_user_id = user["sub"]
    tenant_id = user.get("tenant_id", auth0_user_id)
    get_or_create_onboarding(db, auth0_user_id, tenant_id)
    try:
        state = mark_step_complete(db, auth0_user_id, step)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {
        "completed_steps": state.get_steps(),
        "is_complete": state.is_complete,
    }


# ---- Trial ----

@app.post("/api/trial/start", tags=["lifecycle"])
async def start_trial_endpoint(
    request: TrialStartRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Start a free trial. Creates Stripe subscription with trial_period_days if customer_id available."""
    auth0_user_id = user["sub"]
    tenant_id = user.get("tenant_id", auth0_user_id)
    stripe_sub_id = None
    # In production, retrieve customer_id from Auth0 user_metadata or local users table.
    # Skip Stripe if no customer_id is available yet.
    try:
        record = start_trial(
            db, auth0_user_id, tenant_id,
            trial_days=request.trial_days,
            stripe_subscription_id=stripe_sub_id,
        )
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {
        "status": record.status,
        "trial_end_at": record.trial_end_at.isoformat(),
        "trial_days": record.trial_days,
    }


@app.get("/api/trial/status", tags=["lifecycle"])
async def get_trial_status_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Get trial status for the authenticated user."""
    auth0_user_id = user["sub"]
    record = get_trial(db, auth0_user_id)
    if not record:
        return {"trial_exists": False, "is_active": False}
    return {
        "trial_exists": True,
        "is_active": is_trial_active(db, auth0_user_id),
        "status": record.status,
        "trial_end_at": record.trial_end_at.isoformat(),
    }


# ---- Activation ----

@app.post("/api/activation/event", tags=["lifecycle"])
async def record_activation_event_endpoint(
    request: ActivationEventRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
    _consent=Depends(require_fresh_consent),
):
    """Record an activation event (idempotent — first occurrence only)."""
    auth0_user_id = user["sub"]
    tenant_id = user.get("tenant_id", auth0_user_id)
    event = record_activation(db, auth0_user_id, tenant_id, request.event_name, request.metadata)
    return {
        "event_name": event.event_name,
        "occurred_at": event.occurred_at.isoformat(),
    }


@app.get("/api/activation/status", tags=["lifecycle"])
async def get_activation_status_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Check whether the authenticated user has activated."""
    auth0_user_id = user["sub"]
    events = get_activation_events(db, auth0_user_id)
    return {
        "is_activated": is_activated(db, auth0_user_id),
        "event_count": len(events),
        "events": [
            {"name": e.event_name, "occurred_at": e.occurred_at.isoformat()}
            for e in events
        ],
    }


# ---- Offboarding ----

@app.post("/api/offboarding/initiate", tags=["lifecycle"])
async def initiate_offboarding_endpoint(
    request: OffboardingInitiateRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Initiate cancellation flow: record reason, cancel Stripe, send email."""
    auth0_user_id = user["sub"]
    tenant_id = user.get("tenant_id", auth0_user_id)
    try:
        record = initiate_offboarding(
            db, auth0_user_id, tenant_id,
            reason=request.reason,
            feedback=request.feedback,
            cancel_at_period_end=request.cancel_at_period_end,
        )
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")

    # Side effects (non-blocking)
    if record.stripe_subscription_id:
        try:
            stripe.cancel_subscription(
                record.stripe_subscription_id,
                at_period_end=record.cancel_at_period_end,
            )
        except Exception:
            pass
    try:
        email = user.get("email", "")
        if email:
            mailer.send_subscription_cancelled(email=email, name=email)
    except Exception:
        pass

    return {
        "reason": record.cancellation_reason,
        "initiated_at": record.initiated_at.isoformat(),
        "cancel_at_period_end": record.cancel_at_period_end,
    }


@app.get("/api/offboarding/status", tags=["lifecycle"])
async def get_offboarding_status_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Get offboarding status for the authenticated user."""
    auth0_user_id = user["sub"]
    record = get_offboarding_record(db, auth0_user_id)
    if not record:
        return {"offboarding_exists": False}
    return {
        "offboarding_exists": True,
        "reason": record.cancellation_reason,
        "initiated_at": record.initiated_at.isoformat(),
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }


# ---- Account Closure ----

@app.post("/api/account/close", tags=["lifecycle"])
async def close_account_endpoint(
    request: AccountCloseRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Initiate account closure (soft delete + 30-day purge window)."""
    auth0_user_id = user["sub"]
    tenant_id = user.get("tenant_id", auth0_user_id)
    try:
        closure = initiate_closure(db, auth0_user_id, tenant_id, reason=request.reason)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {
        "status": closure.status,
        "purge_at": closure.purge_at.isoformat(),
    }


@app.delete("/api/account/close", tags=["lifecycle"])
async def cancel_account_closure_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Cancel a pending account closure and reactivate the account."""
    auth0_user_id = user["sub"]
    cancelled = cancel_closure(db, auth0_user_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="No pending account closure found")
    return {"cancelled": True}


@app.get("/api/account/close/status", tags=["lifecycle"])
async def get_closure_status_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Get account closure status for the authenticated user."""
    auth0_user_id = user["sub"]
    closure = get_closure_request(db, auth0_user_id)
    if not closure:
        return {"closure_exists": False}
    return {
        "closure_exists": True,
        "status": closure.status,
        "purge_at": closure.purge_at.isoformat(),
        "purged_at": closure.purged_at.isoformat() if closure.purged_at else None,
    }


@app.post("/api/account/purge/{user_id}", tags=["lifecycle"])
async def admin_execute_purge_endpoint(
    user_id: str,
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Admin: hard-delete all data for a user whose purge window has elapsed."""
    summary = execute_purge(db, user_id)
    return {"purged": True, "summary": summary}


# ============================================================
# P1 LEGAL CONSENT ENDPOINTS
# ============================================================

@app.get("/api/legal/versions", tags=["legal"])
async def get_legal_versions_endpoint(db=Depends(get_db)):
    """Public: return current legal document versions for Terms and Privacy."""
    tos = get_current_version(db, DOC_TYPE_TERMS)
    priv = get_current_version(db, DOC_TYPE_PRIVACY)
    return {
        "terms": {
            "version": tos.version,
            "effective_at": tos.effective_at.isoformat(),
        } if tos else None,
        "privacy": {
            "version": priv.version,
            "effective_at": priv.effective_at.isoformat(),
        } if priv else None,
    }


@app.get("/api/legal/consent/status", tags=["legal"])
async def get_consent_status_endpoint(
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Auth: check if user has accepted current legal versions. No consent gate applied."""
    auth0_user_id = user["sub"]
    return get_consent_status(db, auth0_user_id)


@app.post("/api/legal/consent", tags=["legal"])
async def record_consent_endpoint(
    http_request: Request,
    body: ConsentAcceptRequest,
    db=Depends(get_db),
    user=Depends(require_role("user")),
):
    """Auth: record consent for a legal document version. Writes UserConsent + audit log."""
    auth0_user_id = user["sub"]

    if body.doc_type not in (DOC_TYPE_TERMS, DOC_TYPE_PRIVACY):
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {body.doc_type}")

    current = get_current_version(db, body.doc_type)
    if not current:
        raise HTTPException(status_code=400, detail=f"No current version configured for {body.doc_type}")
    if current.version != body.version:
        raise HTTPException(
            status_code=400,
            detail=f"Version mismatch: submitted '{body.version}', current is '{current.version}'",
        )

    client_ip = http_request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip:
        client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent", "")[:512]

    record_consent(db, auth0_user_id, body.doc_type, body.version, client_ip, user_agent)
    return get_consent_status(db, auth0_user_id)


@app.post("/api/admin/legal/version", tags=["legal"])
async def admin_set_legal_version_endpoint(
    body: AdminSetVersionRequest,
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Admin: set the current version for a legal document. Triggers re-acceptance for all users."""
    try:
        doc_version = set_current_version(db, body.doc_type, body.version)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {
        "doc_type": doc_version.doc_type,
        "version": doc_version.version,
        "effective_at": doc_version.effective_at.isoformat(),
    }


@app.get("/api/admin/legal/consent/{user_id}/log", tags=["legal"])
async def admin_get_consent_log_endpoint(
    user_id: str,
    db=Depends(get_db),
    _user=Depends(require_role("admin")),
):
    """Admin: return full consent audit log for a user (IP, timestamp, user-agent)."""
    logs = get_audit_log(db, user_id)
    return {
        "user_id": user_id,
        "count": len(logs),
        "entries": [
            {
                "doc_type": entry.doc_type,
                "version": entry.version,
                "client_ip": entry.client_ip,
                "user_agent": entry.user_agent,
                "occurred_at": entry.occurred_at.isoformat(),
            }
            for entry in logs
        ],
    }


# ============================================================
# P1 FRAUD & ABUSE ENDPOINTS (#30-36)
# ============================================================

@app.get("/api/admin/fraud/events", tags=["fraud"])
async def list_fraud_events(
    tenant_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db),
    user=Depends(require_role("admin")),
):
    """List unresolved fraud events. Filter by tenant_id and/or event_type."""
    events = get_fraud_events(
        db, tenant_id=tenant_id, event_type=event_type, resolved=False, limit=limit
    )
    return {
        "events": [
            {
                "id": e.id,
                "auth0_user_id": e.auth0_user_id,
                "tenant_id": e.tenant_id,
                "event_type": e.event_type,
                "severity": e.severity,
                "source": e.source,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "is_resolved": e.is_resolved,
            }
            for e in events
        ]
    }


@app.post("/api/admin/fraud/lockout", tags=["fraud"])
async def lockout_account(
    body: FraudLockoutRequest,
    db=Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Lock an account in DB and block it in Auth0."""
    admin_id = user["sub"]
    tenant_id = body.auth0_user_id  # tenant_id defaults to user_id for self-tenanted accounts
    try:
        lockout = lock_account(
            db,
            auth0_user_id=body.auth0_user_id,
            tenant_id=tenant_id,
            reason=body.reason,
            locked_by=admin_id,
        )
    except ValueError as e:
        logger.error(f"Conflict error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=409, detail="Conflict")

    try:
        auth0.update_user(user_id=body.auth0_user_id, blocked=True)
    except Exception as e:
        logger.error(f"Auth0 block failed for {body.auth0_user_id}: {e}")
        # DB lockout is source of truth; Auth0 failure is non-fatal

    return {"locked": True, "lockout_id": lockout.id}


@app.delete("/api/admin/fraud/lockout/{user_id}", tags=["fraud"])
async def unlock_account_endpoint(
    user_id: str,
    db=Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """Unlock an account in DB and unblock it in Auth0."""
    success = unlock_account(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="No active lockout found")

    try:
        auth0.update_user(user_id=user_id, blocked=False)
    except Exception as e:
        logger.error(f"Auth0 unblock failed for {user_id}: {e}")

    return {"unlocked": True}


@app.get("/api/admin/fraud/lockout/{user_id}", tags=["fraud"])
async def get_lockout_status(
    user_id: str,
    db=Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """Check whether an account is currently locked."""
    return {"is_locked": is_account_locked(db, user_id)}


# ============================================================
# FINANCIAL GOVERNANCE ENDPOINTS (#37-40)
# ============================================================

@app.post("/api/admin/financial/transactions", tags=["financial"])
async def create_stripe_transaction(
    request: Request,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#37: Manually record a Stripe transaction with fee attribution."""
    body = await request.json()
    try:
        txn = record_stripe_transaction(
            db=db,
            tenant_id=body["tenant_id"],
            gross_usd=float(body["gross_usd"]),
            fee_usd=float(body.get("fee_usd", 0.0)),
            transaction_type=body.get("transaction_type", "charge"),
            stripe_balance_txn_id=body.get("stripe_balance_txn_id"),
            stripe_charge_id=body.get("stripe_charge_id"),
            stripe_payment_intent_id=body.get("stripe_payment_intent_id"),
            description=body.get("description"),
        )
        return {
            "id": txn.id,
            "tenant_id": txn.tenant_id,
            "transaction_type": txn.transaction_type,
            "gross_usd": txn.gross_usd,
            "fee_usd": txn.fee_usd,
            "net_usd": txn.net_usd,
            "period_key": txn.period_key,
            "occurred_at": txn.occurred_at.isoformat(),
        }
    except (KeyError, ValueError) as e:
        logger.error(f"Validation error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=422, detail="Validation error")


@app.get("/api/admin/financial/fees", tags=["financial"])
async def get_fee_summary(
    tenant_id: Optional[str] = None,
    period_key: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#37: Get aggregated Stripe fee summary. Filter by tenant_id and/or period_key (YYYY-MM)."""
    return get_stripe_fee_summary(db, tenant_id=tenant_id, period_key=period_key)


@app.get("/api/admin/financial/margin", tags=["financial"])
async def get_margin_report(
    tenant_id: str,
    period_key: str,
    revenue_usd: float = 0.0,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#38: Full gross + net margin report for a tenant/period. Pass revenue_usd manually."""
    return get_gross_margin(db, tenant_id=tenant_id, period_key=period_key, revenue_usd=revenue_usd)


@app.post("/api/admin/financial/reconcile", tags=["financial"])
async def submit_reconciliation(
    request: Request,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#39: Submit bank statement total for a period. Computes variance vs Stripe net deposits."""
    body = await request.json()
    try:
        rec = reconcile_period(
            db=db,
            tenant_id=body["tenant_id"],
            period_key=body["period_key"],
            bank_total_usd=float(body["bank_total_usd"]),
            notes=body.get("notes"),
        )
        return {
            "id": rec.id,
            "tenant_id": rec.tenant_id,
            "period_key": rec.period_key,
            "stripe_total_usd": rec.stripe_total_usd,
            "bank_total_usd": rec.bank_total_usd,
            "variance_usd": rec.variance_usd,
            "status": rec.status,
            "notes": rec.notes,
            "reconciled_at": rec.reconciled_at.isoformat(),
        }
    except (KeyError, ValueError) as e:
        logger.error(f"Validation error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=422, detail="Validation error")


@app.get("/api/admin/financial/reconcile", tags=["financial"])
async def list_reconciliation_records(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#39: List reconciliation records. Filter by tenant_id and/or status."""
    try:
        records = list_reconciliations(db, tenant_id=tenant_id, status=status)
    except ValueError as e:
        logger.error(f"Validation error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=422, detail="Validation error")
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "period_key": r.period_key,
            "stripe_total_usd": r.stripe_total_usd,
            "bank_total_usd": r.bank_total_usd,
            "variance_usd": r.variance_usd,
            "status": r.status,
            "reconciled_at": r.reconciled_at.isoformat(),
        }
        for r in records
    ]


@app.get("/api/admin/financial/reconcile/{period_key}", tags=["financial"])
async def get_reconciliation_record(
    period_key: str,
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#39: Get a single reconciliation record for a tenant/period."""
    rec = get_reconciliation(db, tenant_id=tenant_id, period_key=period_key)
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation record not found")
    return {
        "id": rec.id,
        "tenant_id": rec.tenant_id,
        "period_key": rec.period_key,
        "stripe_total_usd": rec.stripe_total_usd,
        "bank_total_usd": rec.bank_total_usd,
        "variance_usd": rec.variance_usd,
        "status": rec.status,
        "notes": rec.notes,
        "reconciled_at": rec.reconciled_at.isoformat(),
    }


@app.get("/api/admin/financial/export/csv", tags=["financial"])
async def export_csv(
    tenant_id: Optional[str] = None,
    period_key: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#40: Download QuickBooks-compatible CSV of revenue + expenses for a tenant/period."""
    from fastapi.responses import Response
    csv_data = export_accounting_csv(db, tenant_id=tenant_id, period_key=period_key)
    filename = f"accounting_{tenant_id or 'all'}_{period_key or 'all'}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── #41/#42: Retention Policy Admin Routes ──────────────────────────────────

@app.get("/api/admin/retention/policies", tags=["retention"])
async def list_policies(
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#41/#42: List all configured retention policies."""
    rows = list_retention_policies(db)
    # Merge DB rows with defaults so every type is always visible
    merged = dict(RETENTION_DEFAULTS)
    for r in rows:
        merged[r.data_type] = r.retention_days
    return {"policies": merged, "log_types": list(LOG_DATA_TYPES), "compliance_types": list(COMPLIANCE_DATA_TYPES)}


@app.put("/api/admin/retention/policies/{data_type}", tags=["retention"])
async def set_policy(
    data_type: str,
    retention_days: int,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#41/#42: Set retention_days for a data_type."""
    try:
        policy = set_retention_policy(db, data_type, retention_days, description)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {"data_type": policy.data_type, "retention_days": policy.retention_days}


@app.post("/api/admin/retention/purge", tags=["retention"])
async def run_purge(
    scope: str = "logs",   # "logs" | "compliance" | "all"
    data_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#41/#42: Run retention purge for logs, compliance data, or all."""
    try:
        if data_type:
            if data_type in LOG_DATA_TYPES:
                result = purge_expired_logs(db, data_type=data_type)
            else:
                result = apply_retention_rules(db, data_type=data_type)
        elif scope == "compliance":
            result = apply_retention_rules(db)
        elif scope == "all":
            result = {**purge_expired_logs(db), **apply_retention_rules(db)}
        else:
            result = purge_expired_logs(db)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {"deleted": result}


# ─── #43: Archival Strategy Admin Routes ──────────────────────────────────────

@app.post("/api/admin/retention/archive/{tenant_id}", tags=["retention"])
async def run_archive(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#43: Archive all tenant data to cold storage (ArchivedRecord)."""
    counts = archive_tenant_data(db, tenant_id)
    return {"tenant_id": tenant_id, "archived": counts, "total": sum(counts.values())}


@app.get("/api/admin/retention/archives", tags=["retention"])
async def get_archives(
    tenant_id: Optional[str] = None,
    data_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#43: List ArchivedRecord rows with optional filters."""
    rows = list_archives(db, tenant_id=tenant_id, data_type=data_type)
    return {
        "count": len(rows),
        "archives": [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "data_type": r.data_type,
                "source_id": r.source_id,
                "archived_at": r.archived_at.isoformat() if r.archived_at else None,
            }
            for r in rows
        ],
    }


# ─── #44: Data Deletion SLA Admin Routes ──────────────────────────────────────

@app.post("/api/admin/data-deletion/request", tags=["deletion"])
async def create_deletion_request(
    tenant_id: str,
    requested_by: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#44: Create a GDPR deletion request (30-day SLA)."""
    req = request_data_deletion(db, tenant_id, requested_by, notes)
    return {
        "id": req.id,
        "tenant_id": req.tenant_id,
        "sla_deadline": req.sla_deadline.isoformat(),
        "status": req.status,
    }


@app.post("/api/admin/data-deletion/{request_id}/complete", tags=["deletion"])
async def fulfill_deletion(
    request_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#44: Archive + purge tenant data and mark deletion request completed."""
    try:
        req = complete_deletion(db, request_id)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {
        "id": req.id,
        "status": req.status,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "data_types_deleted": req.data_types_deleted,
    }


@app.get("/api/admin/data-deletion/overdue", tags=["deletion"])
async def overdue_deletions(
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#44: List deletion requests past their 30-day SLA deadline."""
    rows = get_overdue_deletions(db)
    return {
        "count": len(rows),
        "overdue": [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "requested_at": r.requested_at.isoformat(),
                "sla_deadline": r.sla_deadline.isoformat(),
                "status": r.status,
                "days_overdue": (
                    __import__("datetime").datetime.utcnow() - r.sla_deadline
                ).days,
            }
            for r in rows
        ],
    }


@app.get("/api/admin/data-deletion", tags=["deletion"])
async def list_deletions(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_role("admin")),
):
    """#44: List data deletion requests with optional filters."""
    try:
        rows = list_deletion_requests(db, tenant_id=tenant_id, status=status)
    except ValueError as e:
        logger.error(f"Request error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="Bad request")
    return {
        "count": len(rows),
        "requests": [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "requested_by": r.requested_by,
                "sla_deadline": r.sla_deadline.isoformat(),
                "status": r.status,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ],
    }


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 60)
    logger.info(f"Starting {BUSINESS_CONFIG['business']['name']} API v2.0")
    logger.info("=" * 60)
    
    # Initialize Sentry error tracking (P0)
    sentry_active = init_monitoring(app)
    if sentry_active:
        logger.info("✓ Sentry error tracking initialized")
    else:
        logger.warning("⚠ Sentry not configured (set SENTRY_DSN for production)")

    # Load capability registry and validate P0 setup (P0)
    load_capabilities()
    p0_status = validate_p0_capabilities()
    if p0_status["ready_for_production"]:
        logger.info("✓ All P0 capabilities configured")
    else:
        for warning in p0_status["warnings"]:
            logger.warning(f"⚠ {warning}")

    # Initialize database (creates tables for all imported models)
    # Tenant, AICostLog, UsageCounter tables created here alongside existing tables
    try:
        init_db()
        logger.info("✓ Database initialized (all P0 tables ready)")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

    # Auto-load business routes
    try:
        loaded_count = load_business_routes(app)
        logger.info(f"✓ Loaded {loaded_count} business route(s)")
    except Exception as e:
        logger.error(f"Failed to load business routes: {e}")
    
    logger.info("=" * 60)
    logger.info(f"API ready at: http://localhost:8000")
    logger.info(f"Docs available at: http://localhost:8000/docs")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
