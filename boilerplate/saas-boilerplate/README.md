# SaaS Boilerplate — Developer Reference

**FastAPI + React + SQLAlchemy + Auth0 + Stripe.**
**44 capabilities. 79 API endpoints. 178 tests.**

For full platform docs see the [root README](../README.md).

---

## Architecture Overview

```
saas-boilerplate/
├── backend/
│   ├── main.py              # Single entry point — all routes registered here
│   ├── core/                # 25 capability modules (do not modify for business logic)
│   ├── config/              # business_config.json + capabilities.json
│   ├── tests/               # test_p0_capabilities.py (178 tests)
│   └── .env.example         # All required environment variables
│
├── frontend/
│   └── src/
│       ├── App.js           # Router + Auth0Provider
│       ├── pages/           # Generic pages (Home, Pricing, Dashboard, etc.)
│       └── components/      # Navbar, Footer, ConsentGate, etc.
│
└── business/                # YOUR CODE — auto-loaded, never touches main.py
    ├── backend/routes/      # .py files auto-prefixed as /api/<filename>
    └── frontend/pages/      # .jsx files auto-routed as /dashboard/<page>
```

---

## Core Modules (`backend/core/`)

### Infrastructure

| Module | Capability | Key Exports |
|---|---|---|
| `database.py` | SQLAlchemy setup | `Base`, `get_db`, `init_db` |
| `tenancy.py` | Multi-tenancy | `Tenant`, `tenant_middleware`, `TenantScopedSession` |
| `rbac.py` | Auth + RBAC | `get_current_user`, `require_role`, `has_role` |
| `monitoring.py` | Sentry | `init_monitoring`, `monitoring_middleware` |
| `capability_loader.py` | Feature registry | `is_capability_enabled`, `load_capabilities` |
| `loader.py` | Auto-loader | Scans `business/backend/routes/` on startup |

### Access Control

| Module | Capability | Key Exports |
|---|---|---|
| `entitlements.py` | Stripe → features | `UserEntitlement`, `get_entitlements` |
| `usage_limits.py` | Quotas | `check_limit`, `increment_usage`, `check_and_increment`, `UsageLimitExceeded` |

### AI Governance

| Module | Capability | Key Exports |
|---|---|---|
| `ai_governance.py` | Cost, budget, routing | `calculate_cost`, `check_budget`, `route_model`, `AICostLog`, `BudgetExceededError` |

### Financial

| Module | Capability | Key Exports |
|---|---|---|
| `expense_tracking.py` | Expense logging | `log_expense`, `get_expense_summary`, `get_pl_summary`, `ExpenseLog` |
| `financial_governance.py` | Stripe fees, margin, reconciliation | `record_stripe_transaction`, `get_gross_margin`, `reconcile_period`, `export_accounting_csv` |

### User Lifecycle

| Module | Capability | Key Exports |
|---|---|---|
| `onboarding.py` | Onboarding flow | `get_or_create_onboarding`, `mark_step_complete`, `is_onboarding_complete` |
| `trial.py` | Trial management | `start_trial`, `get_trial`, `is_trial_active`, `mark_trial_converted` |
| `activation.py` | Activation tracking | `record_activation`, `is_activated`, `get_activation_events` |
| `offboarding.py` | Cancellation | `initiate_offboarding`, `complete_offboarding` |
| `account_closure.py` | GDPR deletion | `initiate_closure`, `execute_purge`, `get_pending_purges` |

### Legal & Compliance

| Module | Capability | Key Exports |
|---|---|---|
| `legal_consent.py` | Consent management | `record_consent`, `requires_reacceptance`, `require_fresh_consent`, `set_current_version` |
| `data_retention.py` | Retention + archival + GDPR SLA | `set_retention_policy`, `purge_expired_logs`, `apply_retention_rules`, `archive_tenant_data`, `request_data_deletion`, `complete_deletion` |

### Fraud & Security

| Module | Capability | Key Exports |
|---|---|---|
| `fraud.py` | Fraud events, lockouts | `record_fraud_event`, `lock_account`, `detect_api_abuse`, `detect_ai_abuse`, `detect_self_referral` |
| `ip_throttle.py` | Rate limiting + bot UA filter | `IPThrottleMiddleware`, `IPThrottleCounter` |

### Marketplace

| Module | Capability | Key Exports |
|---|---|---|
| `listings.py` | Listing CRUD + search | `create_listing`, `list_listings`, `update_listing`, `listing_to_search_doc` |
| `purchase_delivery.py` | Buyer access | `deliver_purchase`, `has_purchased` |

---

## Middleware Stack

Registered in `main.py` in this order (outermost first):

```python
app.add_middleware(IPThrottleMiddleware, limit=100, window=60)  # #31 #35
app.add_middleware(BaseHTTPMiddleware, dispatch=monitoring_middleware) # #11
app.add_middleware(BaseHTTPMiddleware, dispatch=tenant_middleware)     # #7
```

- **IP throttle** — 100 req/60s per IP, blocks known scanner UAs (sqlmap, nikto, nuclei…)
- **Monitoring** — Sentry breadcrumbs on every request
- **Tenant** — Extracts `X-Tenant-ID` header, sets thread-local context

Excluded from throttle: `/health`, `/api/webhooks/stripe`

---

## Database Models

All models inherit from `Base` (`core/database.py`). Tables are auto-created on startup.

| Table | Module | Description |
|---|---|---|
| `tenants` | `tenancy.py` | Tenant registry with tier + AI budget |
| `ai_cost_logs` | `ai_governance.py` | Per-request AI token + cost log |
| `ai_budget_configs` | `ai_governance.py` | Per-tenant monthly AI budget |
| `usage_counters` | `usage_limits.py` | Rolling call counters by feature |
| `user_entitlements` | `entitlements.py` | Stripe purchase → feature grants |
| `listings` | `listings.py` | Marketplace listings |
| `purchase_records` | `purchase_delivery.py` | Buyer access records |
| `onboarding_states` | `onboarding.py` | Per-user step completion |
| `trial_records` | `trial.py` | Trial periods with expiry |
| `activation_events` | `activation.py` | Activation milestones |
| `offboarding_records` | `offboarding.py` | Cancellation records |
| `account_closures` | `account_closure.py` | GDPR deletion requests |
| `legal_doc_versions` | `legal_consent.py` | ToS / Privacy version history |
| `user_consents` | `legal_consent.py` | Current accepted version per user |
| `consent_audit_logs` | `legal_consent.py` | Immutable consent audit trail |
| `fraud_events` | `fraud.py` | Fraud event log |
| `account_lockouts` | `fraud.py` | Locked accounts |
| `expense_logs` | `expense_tracking.py` | Operational expenses by category |
| `stripe_transaction_records` | `financial_governance.py` | Stripe gross/fee/net per charge |
| `reconciliation_records` | `financial_governance.py` | Stripe vs bank reconciliation |
| `retention_policies` | `data_retention.py` | Configurable TTL per data type |
| `archived_records` | `data_retention.py` | JSON cold storage before purge |
| `data_deletion_requests` | `data_retention.py` | GDPR 30-day SLA tracker |

---

## Configuration

### `config/business_config.json`

Controls all business-specific content — name, branding, pricing plans, page copy. Edit this file to re-skin the platform for a new business without touching any code.

**Key fields:**

```json
{
  "business": {
    "name": "YourBusiness",
    "tagline": "...",
    "domain": "yourdomain.com",
    "support_email": "support@yourdomain.com"
  },
  "branding": {
    "primary_color": "#3B82F6",
    "secondary_color": "#1E40AF"
  },
  "pricing": {
    "plans": [
      {
        "id": "basic",
        "name": "Basic",
        "price_monthly": 19,
        "stripe_price_id_monthly": "price_xxx",
        "features": ["..."],
        "popular": false
      }
    ]
  },
  "metadata": {
    "auth0_domain": "xxx.auth0.com",
    "auth0_client_id": "xxx"
  }
}
```

### `config/capabilities.json`

The central registry for all 44 built capabilities. Each entry has:

```json
{
  "fraud_detection": {
    "id": "fraud_detection",
    "name": "Payment Fraud Monitoring",
    "priority": "P1",
    "status": "complete",
    "enabled_by_default": true,
    "tier_availability": ["pro", "enterprise"],
    "implementation_file": "core/fraud.py"
  }
}
```

Check at runtime:
```python
from core.capability_loader import is_capability_enabled
if is_capability_enabled("fraud_detection"):
    ...
```

---

## Key Patterns

### Protecting Routes

```python
from core.rbac import require_role, get_current_user

# Admin only
@app.get("/api/admin/something")
async def admin_route(_admin=Depends(require_role("admin"))):
    ...

# Any authenticated user
@app.get("/api/my-data")
async def user_route(user=Depends(get_current_user), db=Depends(get_db)):
    user_id = user["sub"]  # Auth0 user ID
    ...
```

### Using Tenant Context

```python
from core.tenancy import get_current_tenant

tenant = get_current_tenant()  # Returns Tenant object from X-Tenant-ID header
# Use tenant.id, tenant.tier, tenant.monthly_ai_budget_usd
```

### Checking Usage Limits

```python
from core.usage_limits import check_and_increment

# Raises UsageLimitExceeded (HTTP 429) if over plan quota
check_and_increment(db, tenant_id="acme", feature="api_calls")
```

### Logging AI Costs

```python
from core.ai_governance import calculate_cost, check_budget

# Guard first
check_budget(db, tenant_id)  # Raises BudgetExceededError at 100%

# Call your AI API, then log
cost = calculate_cost(model="claude-sonnet-4-6", tokens_in=1000, tokens_out=500)
db.add(AICostLog(
    tenant_id=tenant_id,
    feature="my_feature",
    model="claude-sonnet-4-6",
    tokens_in=1000,
    tokens_out=500,
    cost_usd=cost,
    duration_ms=820,
))
db.commit()
```

### Enforcing Legal Consent

```python
from core.legal_consent import require_fresh_consent

# Add as a Depends — raises HTTP 451 if user hasn't accepted current ToS/Privacy
@app.get("/api/premium-feature")
async def premium(
    user=Depends(get_current_user),
    _consent=Depends(require_fresh_consent),
    db=Depends(get_db),
):
    ...
```

### Recording Fraud Events

```python
from core.fraud import record_fraud_event, detect_api_abuse

# Auto-detect (raises if over threshold)
detect_api_abuse(db, user_id=user["sub"], tenant_id=tenant_id)

# Manual log
record_fraud_event(db,
    event_type="referral_fraud",
    severity="medium",
    source="custom",
    auth0_user_id=user["sub"],
    tenant_id=tenant_id,
    detail={"referral_code": code},
)
```

---

## Stripe Webhook Events

The webhook handler at `POST /api/webhooks/stripe` processes:

| Event | Action |
|---|---|
| `charge.succeeded` | Records `StripeTransactionRecord` with fee attribution |
| `customer.subscription.created` | Grants entitlements |
| `customer.subscription.deleted` | Revokes entitlements |
| `invoice.payment_succeeded` | Updates subscription status |
| `charge.dispute.created` | Creates `FraudEvent` (type: `stripe_dispute`) |
| `radar.early_fraud_warning.created` | Creates `FraudEvent` (type: `stripe_early_fraud_warning`) |

Stripe must be configured to send these events to `https://yourdomain.com/api/webhooks/stripe`.

---

## Retention Defaults

| Data Type | Default Retention | Rationale |
|---|---|---|
| `ai_cost_log` | 90 days | Operational log |
| `fraud_event` | 365 days | Security audit |
| `activation_event` | 365 days | Analytics |
| `consent_audit` | 2,555 days (7yr) | GDPR compliance |
| `expense_log` | 2,555 days (7yr) | Accounting |
| `stripe_transaction` | 2,555 days (7yr) | Financial audit |

Override via admin API:
```
PUT /api/admin/retention/policies/ai_cost_log?retention_days=180
```

---

## Running Tests

```bash
cd backend
source ~/venvs/cd39/bin/activate   # or your venv
pytest tests/test_p0_capabilities.py -v
# 178 passed, 1 warning
```

Tests use SQLite in-memory — no external services needed. All AI calls are mocked.

---

## Deployment

### Backend (Railway)

```bash
# Add to repo root:
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Set environment variables in Railway dashboard
# Deploy: railway up (or connect GitHub for auto-deploy)
```

### Frontend (Vercel)

```bash
cd frontend
npm run build

# Set env vars in Vercel dashboard:
# REACT_APP_API_URL=https://your-api.railway.app/api
# REACT_APP_AUTH0_DOMAIN=xxx.auth0.com
# REACT_APP_AUTH0_CLIENT_ID=xxx

vercel --prod
```

### Stripe Webhook (Production)

After deploying, register the webhook in Stripe:
1. Stripe Dashboard → Developers → Webhooks → Add endpoint
2. URL: `https://your-api.railway.app/api/webhooks/stripe`
3. Events: `charge.succeeded`, `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `charge.dispute.created`, `radar.early_fraud_warning.created`
4. Copy signing secret → set `STRIPE_WEBHOOK_SECRET` in Railway

---

## Adding a New Capability Module

1. Create `core/my_module.py` with SQLAlchemy models inheriting from `Base`
2. Import the model in `main.py` (so `Base.metadata.create_all` picks it up)
3. Add routes to `main.py` or a business route file
4. Add an entry to `config/capabilities.json`
5. Add tests to `tests/test_p0_capabilities.py`
6. Run `pytest` — all 178 + your new tests should pass
