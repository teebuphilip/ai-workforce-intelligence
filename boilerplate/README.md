# Teebu SaaS Platform

**Production-grade SaaS boilerplate. 44 of 53 capabilities built. 178 tests passing.**

**Version:** 4.0
**Repo:** [github.com/teebuphilip/SaaSPlatformLibrary](https://github.com/teebuphilip/SaaSPlatformLibrary) (private)

---

## What This Is

A complete, opinionated SaaS platform library designed to spin up new software businesses in minutes — not months. Every capability is production-tested, registered in a central capability registry, and wired into a single FastAPI backend.

**Stack:** FastAPI + SQLAlchemy + React 18 + Auth0 + Stripe + Sentry

---

## Current State

| Layer | Built | Remaining |
|---|---|---|
| P0 — Core Kernel | 13 / 13 | 0 |
| P1 — Product Extensions | 27 / 27 | 0 |
| P2 — Advanced Ops | 4 / 13 | 9 |
| **Total** | **44 / 53** | **9** |

**178 tests passing.** Run with: `pytest tests/test_p0_capabilities.py -v`

---

## Capability Matrix

### P0 — Core Kernel (13/13 complete)

| # | Domain | Capability | File |
|---|---|---|---|
| 1 | Identity | Authentication | `teebu-shared-libs/lib/auth0_lib.py` |
| 2 | Identity | Role-Based Access | `core/rbac.py` |
| 3 | Identity | Session Management | `core/rbac.py` |
| 4 | Revenue | Billing | `teebu-shared-libs/lib/stripe_lib.py` |
| 5 | Access | Entitlements | `core/entitlements.py` |
| 6 | Access | Usage Limits | `core/usage_limits.py` |
| 7 | Architecture | Multi-Tenancy | `core/tenancy.py` |
| 8 | AI Governance | Cost Tracking | `core/ai_governance.py` |
| 9 | AI Governance | Budget Enforcement | `core/ai_governance.py` |
| 10 | AI Governance | Model Routing | `core/ai_governance.py` |
| 11 | Observability | Error Tracking (Sentry) | `core/monitoring.py` |
| 12 | Data | Backups & Recovery | `docs/BACKUP_RECOVERY.md` |
| 13 | Config | Capability Registry | `core/capability_loader.py` |

### P1 — Product Extensions (27/27 complete)

| # | Domain | Capability | File |
|---|---|---|---|
| 14 | Revenue | Billing Extensions (coupons, usage metering, refunds) | `core/tenancy.py` + Stripe |
| 15 | Communication | Transactional Email | `teebu-shared-libs/lib/mailerlite_lib.py` |
| 16 | Communication | Marketing Email | `teebu-shared-libs/lib/mailerlite_lib.py` |
| 17 | Observability | Uptime Monitoring | `core/monitoring.py` (BetterUptime) |
| 18 | Financial Ops | Expense Tracking | `core/expense_tracking.py` |
| 19 | Admin | Admin Dashboard | `main.py` `/api/admin/*` routes |
| 20 | Analytics | GA4 Analytics | `teebu-shared-libs/lib/analytics_lib.py` |
| 21 | Lifecycle | User Onboarding | `core/onboarding.py` |
| 22 | Lifecycle | Trial Management | `core/trial.py` |
| 23 | Lifecycle | Activation Tracking | `core/activation.py` |
| 24 | Lifecycle | Offboarding | `core/offboarding.py` |
| 25 | Lifecycle | Account Closure | `core/account_closure.py` |
| 26 | Legal | Terms Version Tracking | `core/legal_consent.py` |
| 27 | Legal | Privacy Consent Logging | `core/legal_consent.py` |
| 28 | Legal | Re-Acceptance Enforcement | `core/legal_consent.py` |
| 29 | Legal | Consent Audit Log | `core/legal_consent.py` |
| 30 | Fraud | Payment Fraud Monitoring | `core/fraud.py` |
| 31 | Fraud | Bot UA Filtering | `core/ip_throttle.py` |
| 32 | Fraud | Account Lockouts | `core/fraud.py` |
| 33 | Fraud | API Abuse Detection | `core/fraud.py` |
| 34 | Fraud | AI Abuse Detection | `core/fraud.py` |
| 35 | Fraud | IP Rate Limiting | `core/ip_throttle.py` |
| 36 | Fraud | Referral Fraud Detection | `core/fraud.py` |
| 37 | Financial | Stripe Fee Attribution | `core/financial_governance.py` |
| 38 | Financial | Gross Margin Calculation | `core/financial_governance.py` |
| 39 | Financial | Multi-Source Reconciliation | `core/financial_governance.py` |
| 40 | Financial | Accounting Export (CSV) | `core/financial_governance.py` |

### P2 — Advanced Ops (4/13 complete)

| # | Domain | Capability | Status | File |
|---|---|---|---|---|
| 41 | Data | Log Retention Policy | ✅ Complete | `core/data_retention.py` |
| 42 | Data | Data Retention Rules | ✅ Complete | `core/data_retention.py` |
| 43 | Data | Archival Strategy | ✅ Complete | `core/data_retention.py` |
| 44 | Data | Data Deletion SLA | ✅ Complete | `core/data_retention.py` |
| 45 | API | Rate Limiting (API) | 🔲 Todo | — |
| 46 | API | API Versioning | 🔲 Todo | — |
| 47 | API | API Key Management | 🔲 Todo | — |
| 48 | API | Webhook Delivery | 🔲 Todo | — |
| 49 | Ops | Feature Flags | 🔲 Todo | — |
| 50 | Ops | Audit Logging | 🔲 Todo | — |
| 51 | Ops | Multi-Region | 🔲 Todo | — |
| 52 | Ops | SLA Reporting | 🔲 Todo | — |
| 53 | Ops | Disaster Recovery | 🔲 Todo | — |

---

## Repository Structure

```
teebu-saas-platform/
│
├── README.md                           # This file
├── PLATFORM_CAPABILITIES.md           # Capability agreement / spec
├── P0_KERNEL_BUILD_DIRECTIVE.md       # Build directives for Claude
│
├── teebu-shared-libs/                 # 5 production shared libraries
│   ├── lib/
│   │   ├── stripe_lib.py              # Payments, subscriptions, webhooks (828 lines)
│   │   ├── mailerlite_lib.py          # Email campaigns + transactional (680 lines)
│   │   ├── auth0_lib.py               # Auth, users, roles (750 lines)
│   │   ├── git_lib.py                 # Git/GitHub operations (720 lines)
│   │   └── analytics_lib.py           # GA4 event tracking (650 lines)
│   ├── tests/                         # 74 library tests
│   └── config/                        # Config templates (9 files)
│
├── saas-boilerplate/
│   ├── backend/
│   │   ├── main.py                    # FastAPI app — ALL routes wired here
│   │   ├── requirements.txt
│   │   ├── .env.example               # All environment variables
│   │   ├── core/                      # 25 capability modules
│   │   │   ├── database.py            # SQLAlchemy + Base + get_db
│   │   │   ├── tenancy.py             # Multi-tenancy, tenant middleware
│   │   │   ├── rbac.py                # RBAC, JWT, session management
│   │   │   ├── ai_governance.py       # AI cost tracking, budget, model routing
│   │   │   ├── monitoring.py          # Sentry error tracking
│   │   │   ├── capability_loader.py   # Capability registry loader
│   │   │   ├── entitlements.py        # Stripe → feature gates
│   │   │   ├── usage_limits.py        # Per-plan quota enforcement
│   │   │   ├── expense_tracking.py    # Expense logging + P&L
│   │   │   ├── listings.py            # Marketplace listing CRUD
│   │   │   ├── purchase_delivery.py   # Buyer access delivery
│   │   │   ├── onboarding.py          # User onboarding flow
│   │   │   ├── trial.py               # Trial management
│   │   │   ├── activation.py          # Activation event tracking
│   │   │   ├── offboarding.py         # Subscription cancellation
│   │   │   ├── account_closure.py     # GDPR account deletion
│   │   │   ├── legal_consent.py       # ToS/Privacy consent + audit log
│   │   │   ├── fraud.py               # Fraud events, lockouts, abuse detection
│   │   │   ├── ip_throttle.py         # IP rate limiting + bot filtering
│   │   │   ├── financial_governance.py # Stripe fees, margin, reconciliation, CSV export
│   │   │   ├── data_retention.py      # Retention policies, archival, GDPR deletion SLA
│   │   │   ├── loader.py              # Auto-loads business routes
│   │   │   ├── posting.py             # Social media posting (Tier 3)
│   │   │   ├── webhook_entitlements.py # Stripe webhook → entitlement grants
│   │   │   └── loader.py              # Business route auto-loader
│   │   ├── config/
│   │   │   ├── business_config.json   # Business name, branding, pricing
│   │   │   └── capabilities.json      # Central capability registry (44 entries)
│   │   └── tests/
│   │       └── test_p0_capabilities.py  # 178 tests for all P0–P2 capabilities
│   │
│   ├── frontend/
│   │   └── src/
│   │       ├── App.js                 # React router + Auth0 provider
│   │       ├── pages/                 # 10 generic pages + 5 admin pages
│   │       ├── components/
│   │       │   ├── DashboardLayout.jsx  # Shared layout; reads branding from config
│   │       │   └── ConsentGate.jsx    # Legal consent enforcement
│   │       └── config/
│   │           ├── business_config.json         # gitignored — fill in locally
│   │           └── business_config.example.json # tracked template
│   │
│   ├── business/                      # YOUR BUSINESS CODE GOES HERE
│   │   ├── backend/routes/            # Drop .py files → auto-loaded
│   │   ├── frontend/pages/            # Drop .jsx files → auto-loaded
│   │   └── frontend/platform.js      # Barrel import for DashboardLayout + hooks
│   │
│   ├── directives/                    # Claude build instructions
│   └── docs/
│       └── BACKUP_RECOVERY.md
│
└── scripts/
    ├── generate_ideas.sh
    ├── run_intake.sh
    └── fo_build_executor.sh
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- A virtual environment (e.g. `python -m venv venv && source venv/bin/activate`)

### 1. Install

```bash
# Backend
cd saas-boilerplate/backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configure Environment

```bash
cp saas-boilerplate/backend/.env.example saas-boilerplate/backend/.env
# Edit .env with your credentials — see Environment Variables section below
```

### 3. Run Tests (confirm everything works)

```bash
cd saas-boilerplate/backend
pytest tests/test_p0_capabilities.py -v
# Expected: 178 passed
```

### 4. Start the Backend

```bash
cd saas-boilerplate/backend
uvicorn main:app --reload --port 8000
```

Startup log confirms all systems:
```
✓ Sentry error tracking initialized
✓ All P0 capabilities configured
✓ Database initialized (all tables ready)
✓ Loaded 0 business route(s)
API ready at http://localhost:8000
```

### 5. Start the Frontend

```bash
cd saas-boilerplate/frontend
npm start
# Opens http://localhost:3000
```

---

## Environment Variables

Copy `.env.example` to `.env` in `saas-boilerplate/backend/`.

### Required — Core

| Variable | Description | Where to get it |
|---|---|---|
| `PORT` | API port (default: 8000) | Set to `8000` |
| `ENVIRONMENT` | `development` or `production` | Set manually |
| `CORS_ORIGINS` | Allowed frontend origins | e.g. `http://localhost:3000` |

### Required — Auth0

| Variable | Description | Where to get it |
|---|---|---|
| `AUTH0_DOMAIN` | Your Auth0 tenant | Auth0 dashboard → Settings |
| `AUTH0_CLIENT_ID` | Application client ID | Auth0 dashboard → Applications |
| `AUTH0_CLIENT_SECRET` | Application secret | Auth0 dashboard → Applications |
| `AUTH0_AUDIENCE` | API identifier | Auth0 dashboard → APIs |

Auth0 setup:
1. Create a **Single Page Application** (for the React frontend)
2. Create an **API** (for the FastAPI backend)
3. Set Allowed Callback URLs: `http://localhost:3000`
4. Set Allowed Logout URLs: `http://localhost:3000`
5. Set Allowed Web Origins: `http://localhost:3000`

### Required — Stripe

| Variable | Description | Where to get it |
|---|---|---|
| `STRIPE_SECRET_KEY` | Secret key (`sk_test_...`) | Stripe → Developers → API Keys |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret (`whsec_...`) | Stripe → Developers → Webhooks |

Stripe webhook setup:
1. Create a webhook endpoint pointing to `https://yourdomain.com/api/webhooks/stripe`
2. Listen for: `charge.succeeded`, `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `charge.dispute.created`, `radar.early_fraud_warning.created`

### Required — Observability

| Variable | Description | Where to get it |
|---|---|---|
| `SENTRY_DSN` | Sentry project DSN | Sentry → Project → Settings → DSN |
| `ENV` | Sentry environment tag | `development` / `production` |
| `APP_VERSION` | Release tag for Sentry | e.g. `4.0.0` |
| `SENTRY_TRACES_SAMPLE_RATE` | Performance trace rate (default: `0.1`) | Optional, 0.0–1.0 |

### Optional — Email

| Variable | Description |
|---|---|
| `MAILERLITE_API_KEY` | MailerLite API key for transactional + campaign email |

### Optional — Analytics

| Variable | Description |
|---|---|
| `GA4_MEASUREMENT_ID` | Google Analytics 4 measurement ID (`G-XXXXX`) |
| `GA4_API_SECRET` | GA4 Measurement Protocol API secret |

### Optional — Git

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (for git_lib) |

### Frontend Environment

Create `saas-boilerplate/frontend/.env.local`:
```
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_AUTH0_DOMAIN=your-tenant.auth0.com
REACT_APP_AUTH0_CLIENT_ID=your_client_id
```

---

## Business Configuration

Copy the template and fill it in:

```bash
cp saas-boilerplate/frontend/src/config/business_config.example.json \
   saas-boilerplate/frontend/src/config/business_config.json
```

The file is gitignored — real credentials stay local. The sections and what they control:

| Section | Controls |
|---|---|
| `business` | Name, tagline, support email |
| `branding` | `primary_color` drives every branded button, stat tile, and CTA automatically |
| `dashboard` | Theme, nav items, upgrade banner, support/docs links |
| `metadata` | GA4 analytics (auto-loads when set), SEO title/description |
| `stripe_products` | Pricing plans — pricing page grid renders and adapts automatically |
| `auth0` | Auth credentials (mirror of `.env`) |
| `mailerlite` | Email list credentials |

**Key principle:** change `branding.primary_color` once and every brand-colored element in the app updates — no component edits needed.

```json
"branding": {
  "primary_color": "#4F46E5",
  "logo_url":      "",
  "company_name":  "YourBusiness"
},
"dashboard": {
  "theme":               "light",
  "show_upgrade_banner": true,
  "nav_items": [
    { "label": "Dashboard", "path": "/dashboard", "icon": "grid" },
    { "label": "Settings",  "path": "/settings",  "icon": "cog"  }
  ]
},
"metadata": {
  "analytics": { "google_analytics_id": "G-XXXXXXXXXX" }
}
```

See [`QUICKSTART.md`](./QUICKSTART.md#step-3-configure-your-business) for the full config reference with all fields documented.

---

## Adding Business Logic

The auto-loader means you never touch `main.py` or `App.js`.

### Add a Backend Route

```python
# saas-boilerplate/business/backend/routes/my_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.rbac import get_current_user

router = APIRouter()  # Must be named 'router'

@router.get("/list")
def list_items(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"items": []}

@router.post("/create")
def create_item(data: dict, db: Session = Depends(get_db)):
    return {"created": True}
```

Restart backend → `GET /api/my_feature/list` is live. Zero imports needed.

### Add a Frontend Page

```jsx
// saas-boilerplate/business/frontend/pages/MyFeature.jsx
export default function MyFeature() {
  return <div>My Feature Page</div>;
}
```

Restart frontend → `/dashboard/my-feature` is live. Zero registration needed.

### Use Core Capabilities in Business Logic

```python
# AI cost tracking
from core.ai_governance import calculate_cost, check_budget, AICostLog

# Log an AI call
cost = calculate_cost(model="claude-haiku-4-5", tokens_in=500, tokens_out=200)
log = AICostLog(tenant_id=tenant_id, feature="my_feature", model="claude-haiku-4-5",
                tokens_in=500, tokens_out=200, cost_usd=cost, duration_ms=340)
db.add(log); db.commit()

# Check budget before calling AI
check_budget(db, tenant_id)  # Raises BudgetExceededError at 100%

# Usage limits
from core.usage_limits import check_and_increment
check_and_increment(db, tenant_id, "api_calls")  # Raises UsageLimitExceeded

# Multi-tenant data scoping
from core.tenancy import get_current_tenant
tenant = get_current_tenant()  # Set automatically by middleware

# Fraud detection
from core.fraud import detect_api_abuse, record_fraud_event
detect_api_abuse(db, user_id, tenant_id)  # Raises if velocity threshold exceeded

# Legal consent enforcement
from core.legal_consent import require_fresh_consent
# Use as FastAPI dependency — raises HTTP 451 if consent outdated
```

---

## Running Tests

```bash
cd saas-boilerplate/backend
source ~/venvs/cd39/bin/activate   # or your venv
pytest tests/test_p0_capabilities.py -v
```

Output: `178 passed, 1 warning`

### Test Coverage by Capability Area

| Area | Tests |
|---|---|
| Multi-Tenancy | 5 |
| AI Governance (cost/budget/routing) | 12 |
| Usage Limits | 8 |
| RBAC | 6 |
| Capability Registry | 4 |
| Expense Tracking + P&L | 9 |
| Listings CRUD | 7 |
| Purchase Delivery | 5 |
| Onboarding | 5 |
| Trial Management | 7 |
| Activation Tracking | 5 |
| Offboarding | 5 |
| Account Closure | 6 |
| Legal Consent | 12 |
| Fraud & Abuse | 15 |
| IP Throttling | 4 |
| Financial Governance | 21 |
| Data Retention & Deletion | 25 |

---

## API Reference

Full interactive docs at `http://localhost:8000/docs` when the backend is running.

### Core

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Full client-safe business config |
| `GET` | `/api/config/{page}` | Page-specific config |

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Create user (Auth0 + email + analytics) |
| `POST` | `/api/auth/send-verification` | Resend verification email |
| `POST` | `/api/auth/password-reset` | Trigger password reset |

### Subscriptions & Billing

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/subscribe` | Create Stripe checkout session |
| `POST` | `/api/cancel-subscription` | Cancel subscription |
| `POST` | `/api/webhooks/stripe` | Stripe webhook receiver |

### Marketplace

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/listings` | Create listing |
| `GET` | `/api/listings` | List all listings |
| `GET` | `/api/listings/search` | MeiliSearch full-text search |
| `GET` | `/api/listings/{id}` | Get single listing |
| `PUT` | `/api/listings/{id}` | Update listing |
| `DELETE` | `/api/listings/{id}` | Delete listing |
| `POST` | `/api/purchases` | Purchase a listing |
| `GET` | `/api/purchases/my` | My purchases |
| `GET` | `/api/purchases/{id}/access` | Check access |

### User Lifecycle

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/onboarding` | Get onboarding state |
| `POST` | `/api/onboarding/step/{step}` | Mark step complete |
| `POST` | `/api/trial/start` | Start free trial |
| `GET` | `/api/trial/status` | Trial status + days remaining |
| `POST` | `/api/activation/event` | Record activation event |
| `GET` | `/api/activation/status` | Activation status |
| `POST` | `/api/offboarding/initiate` | Initiate cancellation |
| `GET` | `/api/offboarding/status` | Offboarding status |
| `POST` | `/api/account/close` | Request account closure |
| `DELETE` | `/api/account/close` | Cancel closure request |
| `GET` | `/api/account/close/status` | Closure status |

### Legal Consent

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/legal/versions` | Current ToS + Privacy versions |
| `GET` | `/api/legal/consent/status` | User consent status |
| `POST` | `/api/legal/consent` | Record user consent |

### Analytics

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analytics/track` | Track custom event |
| `POST` | `/api/analytics/page-view` | Track page view |
| `POST` | `/api/contact` | Submit contact form |

### User Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/user/{user_id}` | Get user |
| `PUT` | `/api/user/{user_id}` | Update user |
| `DELETE` | `/api/user/{user_id}` | Delete account |

### Admin — General

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/users` | List all users |
| `GET` | `/api/admin/tenants` | List all tenants |
| `GET` | `/api/admin/billing/subscriptions` | All subscriptions |
| `GET` | `/api/admin/expenses` | Expense log |
| `POST` | `/api/admin/expenses` | Log an expense |
| `GET` | `/api/admin/pl` | P&L summary |

### Admin — Legal

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/admin/legal/version` | Bump ToS or Privacy version |
| `GET` | `/api/admin/legal/consent/{user_id}/log` | User consent audit log |
| `POST` | `/api/account/purge/{user_id}` | Execute GDPR purge |

### Admin — Fraud

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/fraud/events` | List fraud events |
| `POST` | `/api/admin/fraud/lockout` | Lock an account |
| `DELETE` | `/api/admin/fraud/lockout/{user_id}` | Unlock account |
| `GET` | `/api/admin/fraud/lockout/{user_id}` | Lockout status |

### Admin — Financial Governance

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/admin/financial/transactions` | Record Stripe transaction |
| `GET` | `/api/admin/financial/fees` | Stripe fee summary |
| `GET` | `/api/admin/financial/margin` | Gross + net margin P&L |
| `POST` | `/api/admin/financial/reconcile` | Run bank reconciliation |
| `GET` | `/api/admin/financial/reconcile` | List reconciliations |
| `GET` | `/api/admin/financial/reconcile/{period}` | Single period reconciliation |
| `GET` | `/api/admin/financial/export/csv` | QuickBooks CSV export |

### Admin — Data Retention

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/retention/policies` | All retention policies |
| `PUT` | `/api/admin/retention/policies/{type}` | Set retention days |
| `POST` | `/api/admin/retention/purge` | Run purge (logs/compliance/all) |
| `POST` | `/api/admin/retention/archive/{tenant_id}` | Archive tenant data |
| `GET` | `/api/admin/retention/archives` | List archived records |
| `POST` | `/api/admin/data-deletion/request` | Create GDPR deletion request |
| `POST` | `/api/admin/data-deletion/{id}/complete` | Complete deletion |
| `GET` | `/api/admin/data-deletion/overdue` | Overdue deletion requests |
| `GET` | `/api/admin/data-deletion` | All deletion requests |

---

## Shared Libraries

| Library | Purpose | Key Functions |
|---|---|---|
| `stripe_lib.py` | Payments | `create_subscription`, `create_checkout_session`, `handle_webhook`, `create_coupon` |
| `mailerlite_lib.py` | Email | `add_subscriber`, `send_transactional`, `create_campaign` |
| `auth0_lib.py` | Auth | `get_user`, `assign_role`, `delete_user`, `send_verification` |
| `git_lib.py` | Git ops | `create_repo`, `commit_file`, `create_pr` |
| `analytics_lib.py` | GA4 | `track_event`, `track_page_view`, `track_conversion` |

Run library tests:
```bash
cd teebu-shared-libs
python run_all_tests.py
# Expected: 74 passed
```

---

## Architecture

### Request Flow

```
Browser → React (port 3000)
            ↓ fetch /api/*
FastAPI (port 8000)
  ├── IPThrottleMiddleware    (bot filtering + rate limit)
  ├── tenant_middleware       (sets current tenant context)
  ├── monitoring_middleware   (Sentry breadcrumbs)
  ├── require_role("admin")  (RBAC on admin routes)
  ├── require_fresh_consent  (HTTP 451 if stale ToS)
  └── route handler
        ├── check_budget()   (AI governance)
        ├── check_limit()    (usage quotas)
        └── db (SQLAlchemy, scoped per request)
```

### Database

SQLAlchemy ORM. All models auto-create on startup via `Base.metadata.create_all()`.

**Tables created:**
`tenants`, `ai_cost_logs`, `usage_counters`, `ai_budget_configs`,
`listings`, `purchase_records`, `user_entitlements`,
`onboarding_states`, `trial_records`, `activation_events`,
`offboarding_records`, `account_closures`,
`legal_doc_versions`, `user_consents`, `consent_audit_logs`,
`fraud_events`, `account_lockouts`,
`expense_logs`, `stripe_transaction_records`, `reconciliation_records`,
`retention_policies`, `archived_records`, `data_deletion_requests`

### Auto-Loader

```
business/backend/routes/*.py  →  prefix /api/<filename>
business/frontend/pages/*.jsx →  route /dashboard/<page-name>
```

No imports. No registration. Drop the file, restart, done.

### Capability Registry

`config/capabilities.json` is the source of truth for what's enabled. Check at runtime:

```python
from core.capability_loader import is_capability_enabled

if is_capability_enabled("fraud_detection"):
    detect_api_abuse(db, user_id, tenant_id)
```

---

## Deploying a New Business

```bash
# 1. Copy the boilerplate
cp -r saas-boilerplate/ ~/projects/my-new-business/
cd ~/projects/my-new-business/

# 2. Configure
cp backend/.env.example backend/.env
vi backend/.env                                                    # Add your API keys
cp frontend/src/config/business_config.example.json \
   frontend/src/config/business_config.json
vi frontend/src/config/business_config.json                        # Brand it

# 3. Replace logo
cp ~/my-logo.svg frontend/public/logo.svg

# 4. Drop in business logic
# backend: business/backend/routes/my_feature.py
# frontend: business/frontend/pages/MyFeature.jsx

# 5. Test
cd backend && pytest tests/ -v

# 6. Deploy backend to Railway
railway up

# 7. Deploy frontend to Vercel
cd ../frontend && vercel --prod
```

**Time to launch:** ~14 minutes for Tier 1+2, ~22 minutes with Tier 3 marketing.

---

## Project Stats

| Metric | Value |
|---|---|
| Capabilities built | 44 / 53 |
| Tests passing | 178 |
| Core modules | 25 |
| Shared libraries | 5 |
| API endpoints | 79 |
| DB tables | 23 |
| Library lines of code | 3,628 |
| Time to new business | ~14 min |
