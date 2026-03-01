# Claude Build Directive — Teebu SaaS Platform v4.0

**READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE.**

This directive tells you exactly what the platform already provides, where to put new business code, which imports to use, and what to never touch.

---

## The One Rule

> **Build in `business/`. Never touch `saas-boilerplate/`.**

The platform is a kernel. It is complete. Your job is to drop business logic into the right folders and it auto-loads. No wiring. No registration. No editing `main.py` or `App.js`.

---

## Platform State (What Is Already Built)

The following are **complete and production-ready**. Do not rebuild them.

### Infrastructure (never rebuild)
- Multi-tenancy with `X-Tenant-ID` header scoping
- JWT authentication via Auth0
- Role-based access (admin / user / viewer)
- Per-IP rate limiting (100 req/60s) + bot UA filtering
- Sentry error tracking on every request
- SQLAlchemy ORM with 23 tables auto-created on startup
- Business config loaded from `config/business_config.json`
- Capability registry at `config/capabilities.json`

### Business Features (never rebuild)
- Stripe subscriptions, webhooks, entitlements
- Usage quota enforcement by plan tier
- AI cost tracking, budget enforcement, model routing
- Expense logging + P&L summary
- Marketplace listing CRUD + MeiliSearch
- Purchase delivery + buyer access
- User onboarding flow
- Trial management (start, convert, expire)
- Activation event tracking
- Offboarding + account closure (GDPR)
- Legal consent (ToS/Privacy versioning + audit log)
- Fraud detection (payment fraud, lockouts, API abuse, AI abuse, IP throttle, referral fraud)
- Stripe fee attribution, gross margin P&L, bank reconciliation, QuickBooks CSV export
- Data retention policies, cold-storage archival, GDPR deletion SLA (30-day)

### Already-Wired API Endpoints (never rebuild)
Auth, signup, subscriptions, webhooks, listings, purchases, onboarding, trial,
activation, offboarding, account closure, legal consent, fraud admin, financial
admin, retention admin, analytics, contact, user management.

Full list: `GET http://localhost:8000/docs` after starting the server.

---

## Directory Map — Where Code Lives

```
teebu-saas-platform/
│
├── saas-boilerplate/
│   ├── backend/
│   │   ├── main.py                ❌  DO NOT EDIT
│   │   ├── core/                  ❌  DO NOT EDIT (25 capability modules)
│   │   ├── config/
│   │   │   ├── business_config.json   ✅  EDIT — branding, pricing, copy
│   │   │   └── capabilities.json      ✅  EDIT — register new capabilities
│   │   └── tests/
│   │       └── test_p0_capabilities.py  ✅  APPEND tests here
│   │
│   └── frontend/
│       ├── src/App.js             ❌  DO NOT EDIT
│       └── src/pages/             ❌  DO NOT EDIT (generic pages)
│
└── business/                      ✅  ALL YOUR CODE GOES HERE
    ├── backend/
    │   ├── routes/                ✅  Add .py files here (auto-loaded)
    │   ├── models/                ✅  Add SQLAlchemy models here
    │   └── tests/                 ✅  Add business-specific tests here
    └── frontend/
        └── pages/                 ✅  Add .jsx files here (auto-loaded)
```

---

## Auto-Loader Rules

### Backend Routes

Every `.py` file in `business/backend/routes/` is automatically mounted.

```python
# business/backend/routes/my_feature.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from core.database import get_db
from core.rbac import get_current_user, require_role
from core.tenancy import get_current_tenant

router = APIRouter()   # ← REQUIRED. Must be named exactly 'router'.

class MyItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

@router.get("/list")
def list_items(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"items": [], "user": user["sub"]}

@router.post("/create")
def create_item(data: MyItemCreate, db: Session = Depends(get_db)):
    return {"created": True, "name": data.name}
```

**Result:** `GET /api/my_feature/list` and `POST /api/my_feature/create` are live on next restart.

- File name → URL prefix: `my_feature.py` → `/api/my_feature/`
- No import in `main.py`. No `app.include_router()`. Just drop the file.
- Use `tags=["my-feature"]` on the router for grouping in `/docs`

### Frontend Pages

Every `.jsx` file in `business/frontend/pages/` is automatically routed and wrapped in `ProtectedRoute` + `ConsentGate`. **Always use `DashboardLayout` from `../platform` to match the boilerplate look and feel.**

```jsx
// business/frontend/pages/MyFeature.jsx

import { useEffect, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import DashboardLayout, { useConfig, useAnalytics } from '../platform';

export default function MyFeature() {   // ← REQUIRED: default export
  const { getAccessTokenSilently } = useAuth0();
  const { branding } = useConfig();
  const analytics = useAnalytics();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analytics.trackPageView('/dashboard/my-feature', 'My Feature');
    async function load() {
      try {
        const token = await getAccessTokenSilently();
        const res = await fetch('/api/my_feature/list', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setItems(data.items);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getAccessTokenSilently, analytics]);

  if (loading) return <DashboardLayout.Loading />;
  if (error)   return <DashboardLayout.Error message={error} />;

  return (
    <DashboardLayout
      title="My Feature"
      subtitle="Manage your items here"
      action={
        <DashboardLayout.Button onClick={() => alert('create')}>
          + New Item
        </DashboardLayout.Button>
      }
    >
      {items.length === 0 ? (
        <DashboardLayout.Empty
          message="No items yet."
          cta="Create your first item"
          onCta={() => alert('create')}
        />
      ) : (
        <DashboardLayout.Card title="Items">
          <div className="space-y-3">
            {items.map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                <span className="font-medium">{item.name}</span>
                <span className="text-sm text-gray-500">{item.value}</span>
              </div>
            ))}
          </div>
        </DashboardLayout.Card>
      )}
    </DashboardLayout>
  );
}
```

**Result:** `http://localhost:3000/dashboard/my-feature` is live on next restart.

- File name → route: `MyFeature.jsx` → `/dashboard/my-feature`
- Navbar, Footer, auth guard, consent gate — all applied automatically
- No import in `App.js`. No `<Route>`. Just drop the file.

**`../platform` re-exports:**

| Import | What it is |
|---|---|
| `default` / `DashboardLayout` | Page wrapper — bg, max-width, title bar |
| `DashboardLayout.Card` | White card with optional title |
| `DashboardLayout.Stat` | Branded stat tile (matches Dashboard.jsx) |
| `DashboardLayout.Button` | Primary/outline button using brand color |
| `DashboardLayout.Empty` | Empty state with optional CTA |
| `DashboardLayout.Loading` | Full-screen loading state |
| `DashboardLayout.Error` | Full-screen error state |
| `useConfig` | Returns `business_config.json` — access `branding.primary_color`, `business.name`, etc. |
| `useAnalytics` | `analytics.trackEvent()` / `analytics.trackPageView()` |

---

## Using Platform Capabilities

Import from `core.*`. These are the correct paths for v4.0.

### Authentication & RBAC

```python
from core.rbac import get_current_user, require_role, has_role

# Any authenticated user
@router.get("/data")
def get_data(user=Depends(get_current_user)):
    user_id = user["sub"]       # Auth0 user ID string
    email   = user.get("email")
    roles   = user.get("https://teebu.io/roles", [])
    return {"user_id": user_id}

# Admin only — returns HTTP 403 if not admin
@router.delete("/admin-only")
def admin_action(_admin=Depends(require_role("admin"))):
    return {"deleted": True}

# Check role programmatically
if has_role(user, "admin"):
    ...
```

### Multi-Tenancy

```python
from core.tenancy import get_current_tenant

# Tenant is set from X-Tenant-ID header by middleware
tenant = get_current_tenant()
tenant_id   = tenant.id
tenant_tier = tenant.tier   # "basic" | "pro" | "enterprise"
ai_budget   = tenant.monthly_ai_budget_usd
```

### Database

```python
from core.database import Base, get_db
from sqlalchemy import Column, String, Integer, DateTime, Float
from sqlalchemy.orm import Session
from datetime import datetime

# Define model (inherits from Base — auto-created on startup)
class MyRecord(Base):
    __tablename__ = "my_records"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id  = Column(String(64), nullable=False, index=True)
    user_id    = Column(String(128), nullable=False, index=True)
    value      = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# In route
@router.post("/record")
def save_record(value: float, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    rec = MyRecord(tenant_id=get_current_tenant().id,
                   user_id=user["sub"], value=value)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id}
```

**Important:** Import your model in `main.py` so `Base.metadata.create_all()` picks it up on startup. Add a single import line at the bottom of the imports block:
```python
# Add to main.py imports (the ONE exception to the "don't touch main.py" rule):
from business.backend.models.my_feature import MyRecord
```

### Usage Limits (Quota Enforcement)

```python
from core.usage_limits import check_and_increment, UsageLimitExceeded

# Raises HTTP 429 if tenant is over their plan quota
# Plan limits: basic=1000, pro=10000, enterprise=unlimited
try:
    check_and_increment(db, tenant_id=tenant.id, feature="my_feature_calls")
except UsageLimitExceeded as e:
    raise HTTPException(status_code=429, detail=str(e))
```

### AI Governance (Cost Tracking + Budget)

```python
from core.ai_governance import calculate_cost, check_budget, route_model, AICostLog, BudgetExceededError

# 1. Check budget before calling AI (raises HTTP 402 at 100%)
try:
    check_budget(db, tenant_id=tenant.id)
except BudgetExceededError as e:
    raise HTTPException(status_code=402, detail=str(e))

# 2. Route to correct model based on tenant tier
model = route_model(task_type="generation", tier=tenant.tier)
# basic → claude-haiku-4-5 | pro → claude-sonnet-4-6 | enterprise → claude-opus-4-6

# 3. Call your AI API here (anthropic SDK, openai, etc.)
# tokens_in, tokens_out = result.usage.input_tokens, result.usage.output_tokens

# 4. Log the cost
cost = calculate_cost(model=model, tokens_in=tokens_in, tokens_out=tokens_out)
db.add(AICostLog(
    tenant_id=tenant.id,
    feature="my_feature",
    model=model,
    tokens_in=tokens_in,
    tokens_out=tokens_out,
    cost_usd=cost,
    duration_ms=elapsed_ms,
))
db.commit()
```

### Entitlements (Feature Gating by Plan)

```python
from core.entitlements import UserEntitlement

# Check if user has a feature entitlement (granted via Stripe webhook)
entitlement = db.query(UserEntitlement).filter(
    UserEntitlement.auth0_user_id == user["sub"],
    UserEntitlement.feature == "premium_feature",
    UserEntitlement.is_active == True,
).first()

if not entitlement:
    raise HTTPException(status_code=403, detail="Upgrade to Pro to use this feature")
```

Frontend gate:
```jsx
import EntitlementGate from '../../components/EntitlementGate';  // or path to shared component

<EntitlementGate feature="premium_feature" planName="Pro">
  <PremiumComponent />
</EntitlementGate>
```

### Legal Consent Enforcement

```python
from core.legal_consent import require_fresh_consent

# Add as Depends to any route that requires current ToS + Privacy acceptance
# Returns HTTP 451 if user hasn't accepted the current version
@router.post("/sensitive-action")
async def sensitive_action(
    user=Depends(get_current_user),
    _consent=Depends(require_fresh_consent),
    db=Depends(get_db),
):
    ...
```

### Fraud Detection

```python
from core.fraud import detect_api_abuse, detect_ai_abuse, record_fraud_event

# Auto-detect and record API abuse (raises if velocity threshold exceeded)
detect_api_abuse(db, user_id=user["sub"], tenant_id=tenant.id)

# Auto-detect AI abuse (raises if AI call rate is anomalous)
detect_ai_abuse(db, user_id=user["sub"], tenant_id=tenant.id)

# Manually record a custom fraud event
record_fraud_event(db,
    event_type="referral_fraud",   # Must be in FRAUD_EVENT_TYPES
    severity="medium",             # low | medium | high | critical
    source="custom",
    auth0_user_id=user["sub"],
    tenant_id=tenant.id,
    detail={"reason": "duplicate IP on referral"},
)
```

### Expense Tracking

```python
from core.expense_tracking import log_expense

# Categories: ai_api | infra | stripe_fee | email | domain | misc
log_expense(db,
    tenant_id=tenant.id,
    category="ai_api",
    amount_usd=0.045,
    source="anthropic",
    description="claude-sonnet call for my_feature",
)
```

### Onboarding Integration

```python
from core.onboarding import mark_step_complete, is_onboarding_complete, ONBOARDING_STEPS

# Mark a step done when user completes an action
# ONBOARDING_STEPS = ("account_created", "profile_completed", "first_action", "subscription_started")
mark_step_complete(db, user_id=user["sub"], step="first_action")

# Check if all steps done
if is_onboarding_complete(db, user_id=user["sub"]):
    # Show "you're all set" UI
    ...
```

### Activation Tracking

```python
from core.activation import record_activation

# Record a meaningful activation milestone
record_activation(db,
    auth0_user_id=user["sub"],
    tenant_id=tenant.id,
    event_name="first_feature_used",  # Free-form string
)
```

---

## Business Config (`config/business_config.json`)

Update this file to brand the business. The frontend reads it automatically.

```json
{
  "business": {
    "name": "YourBusinessName",
    "tagline": "One-line sell",
    "description": "Two-sentence description.",
    "domain": "yourdomain.com",
    "support_email": "support@yourdomain.com"
  },
  "branding": {
    "primary_color": "#3B82F6",
    "secondary_color": "#1E40AF",
    "logo_url": "/logo.svg"
  },
  "home": {
    "hero": {
      "headline": "Main headline on home page",
      "subheadline": "Supporting text",
      "cta_primary": "Get Started Free"
    },
    "features": [
      { "icon": "🚀", "title": "Feature 1", "description": "What it does" }
    ],
    "social_proof": {
      "testimonials": [
        { "quote": "This saved me hours.", "author": "Jane D.", "title": "Founder" }
      ]
    }
  },
  "pricing": {
    "headline": "Simple, Transparent Pricing",
    "plans": [
      {
        "id": "basic",
        "name": "Basic",
        "price_monthly": 19,
        "price_annual": 190,
        "stripe_price_id_monthly": "price_REPLACE_AFTER_CREATING_IN_STRIPE",
        "stripe_price_id_annual":  "price_REPLACE_AFTER_CREATING_IN_STRIPE",
        "features": ["Core feature 1", "Up to 1,000 calls/mo"],
        "popular": false,
        "cta_text": "Get Started"
      },
      {
        "id": "pro",
        "name": "Pro",
        "price_monthly": 49,
        "price_annual": 490,
        "stripe_price_id_monthly": "price_REPLACE_AFTER_CREATING_IN_STRIPE",
        "stripe_price_id_annual":  "price_REPLACE_AFTER_CREATING_IN_STRIPE",
        "features": ["Everything in Basic", "Up to 10,000 calls/mo", "Priority support"],
        "popular": true,
        "cta_text": "Start Free Trial"
      }
    ]
  },
  "metadata": {
    "auth0_domain": "your-tenant.auth0.com",
    "auth0_client_id": "your_client_id_here"
  }
}
```

**After creating Stripe products:** Replace the `price_REPLACE_*` strings with real Stripe Price IDs from your Stripe dashboard. The entitlement system activates automatically via webhook.

**Replace logo:** `cp your-logo.svg saas-boilerplate/frontend/public/logo.svg`

---

## Capability Registry (`config/capabilities.json`)

Register every new capability you add. This is how the platform tracks what's built.

```json
{
  "capabilities": {
    "my_new_feature": {
      "id": "my_new_feature",
      "name": "My New Feature",
      "priority": "P2",
      "tool": "Custom",
      "enabled_by_default": true,
      "required_for_production": false,
      "implementation_file": "business/backend/routes/my_feature.py",
      "status": "complete",
      "note": "Brief description of what this does and which admin routes expose it.",
      "tier_availability": ["pro", "enterprise"]
    }
  }
}
```

---

## Adding Tests

Append a new test class to the bottom of:
`saas-boilerplate/backend/tests/test_p0_capabilities.py`

```python
class TestMyFeature:
    """Tests for my_feature — capability #XX."""

    def test_create_record_succeeds(self, db):
        """Creating a record persists it to the DB."""
        from business.backend.models.my_feature import MyRecord

        rec = MyRecord(tenant_id="test-tenant", user_id="auth0|123", value=42.0)
        db.add(rec)
        db.commit()

        fetched = db.query(MyRecord).filter(MyRecord.tenant_id == "test-tenant").first()
        assert fetched is not None
        assert fetched.value == 42.0

    def test_create_record_rejects_missing_tenant(self, db):
        """tenant_id is required."""
        from business.backend.models.my_feature import MyRecord
        from sqlalchemy.exc import IntegrityError

        with pytest.raises((IntegrityError, Exception)):
            db.add(MyRecord(tenant_id=None, user_id="auth0|1", value=1.0))
            db.commit()
```

Run tests:
```bash
cd saas-boilerplate/backend
source venv/bin/activate
pytest tests/test_p0_capabilities.py -v
# Must show: N passed, 0 failed
```

**Do not submit the build until all tests pass.**

---

## Patterns Reference

### Pattern: Full CRUD Route File

```python
# business/backend/routes/widgets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import Base, get_db
from core.rbac import get_current_user
from core.tenancy import get_current_tenant
from core.usage_limits import check_and_increment
from sqlalchemy import Column, Integer, String, Float, DateTime

class Widget(Base):
    __tablename__ = "widgets"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id  = Column(String(64), nullable=False, index=True)
    user_id    = Column(String(128), nullable=False, index=True)
    name       = Column(String(256), nullable=False)
    value      = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class WidgetCreate(BaseModel):
    name: str
    value: Optional[float] = 0.0

router = APIRouter(tags=["widgets"])

@router.post("/")
def create_widget(data: WidgetCreate, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    tenant = get_current_tenant()
    check_and_increment(db, tenant_id=tenant.id, feature="widget_creates")
    w = Widget(tenant_id=tenant.id, user_id=user["sub"],
               name=data.name, value=data.value)
    db.add(w); db.commit(); db.refresh(w)
    return {"id": w.id, "name": w.name}

@router.get("/")
def list_widgets(db: Session = Depends(get_db), user=Depends(get_current_user)):
    tenant = get_current_tenant()
    rows = db.query(Widget).filter(
        Widget.tenant_id == tenant.id,
        Widget.user_id == user["sub"],
    ).all()
    return {"widgets": [{"id": r.id, "name": r.name, "value": r.value} for r in rows]}

@router.get("/{widget_id}")
def get_widget(widget_id: int, db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    tenant = get_current_tenant()
    w = db.query(Widget).filter(
        Widget.id == widget_id, Widget.tenant_id == tenant.id
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    return {"id": w.id, "name": w.name, "value": w.value}

@router.put("/{widget_id}")
def update_widget(widget_id: int, data: WidgetCreate,
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    tenant = get_current_tenant()
    w = db.query(Widget).filter(
        Widget.id == widget_id, Widget.tenant_id == tenant.id
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    w.name = data.name; w.value = data.value
    db.commit(); db.refresh(w)
    return {"id": w.id, "name": w.name}

@router.delete("/{widget_id}")
def delete_widget(widget_id: int, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    tenant = get_current_tenant()
    w = db.query(Widget).filter(
        Widget.id == widget_id, Widget.tenant_id == tenant.id
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Widget not found")
    db.delete(w); db.commit()
    return {"deleted": True}
```

### Pattern: AI-Powered Route

```python
# business/backend/routes/ai_summary.py
import time
import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.rbac import get_current_user
from core.tenancy import get_current_tenant
from core.ai_governance import check_budget, route_model, calculate_cost, AICostLog, BudgetExceededError
from core.expense_tracking import log_expense

router = APIRouter(tags=["ai-summary"])

@router.post("/summarize")
def summarize_text(text: str, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    tenant = get_current_tenant()

    # Guard: check AI budget
    try:
        check_budget(db, tenant_id=tenant.id)
    except BudgetExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # Route model by tier
    model = route_model(task_type="summarization", tier=tenant.tier)

    # Call AI
    start = time.time()
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": f"Summarize this:\n\n{text}"}],
    )
    elapsed_ms = int((time.time() - start) * 1000)

    tokens_in  = message.usage.input_tokens
    tokens_out = message.usage.output_tokens
    cost       = calculate_cost(model=model, tokens_in=tokens_in, tokens_out=tokens_out)

    # Log AI cost
    db.add(AICostLog(
        tenant_id=tenant.id, feature="ai_summary", model=model,
        tokens_in=tokens_in, tokens_out=tokens_out,
        cost_usd=cost, duration_ms=elapsed_ms,
    ))

    # Log operational expense
    log_expense(db, tenant_id=tenant.id, category="ai_api",
                amount_usd=cost, source="anthropic",
                description=f"ai_summary — {model}")
    db.commit()

    return {
        "summary": message.content[0].text,
        "model": model,
        "cost_usd": round(cost, 6),
    }
```

### Pattern: External API Integration

```python
# business/backend/routes/weather.py
import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["weather"])

@router.get("/current")
async def get_weather(city: str):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Weather API not configured")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Weather API error")
    data = resp.json()
    return {"city": city, "temp_c": data["main"]["temp"], "description": data["weather"][0]["description"]}
```

### Pattern: React Page with Data Fetch

```jsx
// business/frontend/pages/Widgets.jsx
import { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import DashboardLayout, { useAnalytics } from '../platform';

export default function Widgets() {
  const { getAccessTokenSilently } = useAuth0();
  const analytics = useAnalytics();
  const [widgets, setWidgets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    analytics.trackPageView('/dashboard/widgets', 'Widgets');
    async function load() {
      try {
        const token = await getAccessTokenSilently();
        const res = await fetch('/api/widgets/', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setWidgets(data.widgets);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getAccessTokenSilently, analytics]);

  if (loading) return <DashboardLayout.Loading />;
  if (error)   return <DashboardLayout.Error message={error} />;

  return (
    <DashboardLayout title="Widgets" subtitle="All your widgets in one place">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {widgets.map(w => (
          <DashboardLayout.Card key={w.id}>
            <p className="font-semibold text-gray-900">{w.name}</p>
            <p className="text-gray-500 text-sm mt-1">{w.value}</p>
          </DashboardLayout.Card>
        ))}
      </div>
    </DashboardLayout>
  );
}
```

---

## Build Checklist

Complete all items before the build is considered done.

### Backend
- [ ] All route files in `business/backend/routes/`
- [ ] Every route uses `Depends(get_current_user)` where auth is needed
- [ ] Every route scopes DB queries by `tenant_id` (multi-tenancy)
- [ ] AI routes call `check_budget()` before invoking AI
- [ ] AI routes log cost via `AICostLog` after invoking AI
- [ ] AI routes log operational cost via `log_expense()` with category `ai_api`
- [ ] Usage-limited routes call `check_and_increment()`
- [ ] No secrets hardcoded — all from `os.getenv()`
- [ ] No `main.py` edits (except one model import line if adding DB tables)
- [ ] Backend starts clean: `uvicorn main:app --reload`
- [ ] All routes appear in `/docs`

### Frontend
- [ ] All page files in `business/frontend/pages/`
- [ ] All pages are default exports
- [ ] Auth token attached to all API calls requiring auth
- [ ] Loading and error states handled
- [ ] Responsive layout (use Tailwind)
- [ ] No `App.js` edits

### Configuration
- [ ] `config/business_config.json` — name, tagline, branding, pricing plans
- [ ] Logo replaced: `frontend/public/logo.svg`
- [ ] `config/capabilities.json` — new capabilities registered
- [ ] Stripe Price IDs filled in (or documented as TODO for hero)

### Tests
- [ ] Test class appended to `tests/test_p0_capabilities.py`
- [ ] `pytest tests/test_p0_capabilities.py -v` — 0 failures

### Verification
- [ ] `curl http://localhost:8000/health` → `{"status": "healthy"}`
- [ ] `curl http://localhost:8000/api/{your_route}/` → expected response
- [ ] `http://localhost:3000/dashboard/{your-page}` loads in browser

---

## What the Hero Does After the Build

The only manual steps left for the human operator:

1. **Create Stripe Products** in [Stripe Dashboard](https://dashboard.stripe.com/products)
   - One product per pricing plan
   - Copy the Price IDs into `config/business_config.json`

2. **Register the Stripe Webhook**
   - URL: `https://your-api-domain.com/api/webhooks/stripe`
   - Events: `charge.succeeded`, `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `charge.dispute.created`, `radar.early_fraud_warning.created`
   - Copy signing secret → set `STRIPE_WEBHOOK_SECRET` in Railway

3. **Set environment variables** in Railway (backend) and Vercel (frontend)
   - See `saas-boilerplate/backend/.env.example` for full list

4. **Deploy**
   ```bash
   railway up      # backend
   vercel --prod   # frontend
   ```

---

## Quick Reference — Correct Imports (v4.0)

```python
# Database
from core.database import Base, get_db

# Auth & RBAC
from core.rbac import get_current_user, require_role, has_role

# Multi-tenancy
from core.tenancy import get_current_tenant, Tenant

# AI governance
from core.ai_governance import calculate_cost, check_budget, route_model, AICostLog, BudgetExceededError

# Usage limits
from core.usage_limits import check_and_increment, check_limit, increment_usage, UsageLimitExceeded

# Entitlements
from core.entitlements import UserEntitlement

# Expense tracking
from core.expense_tracking import log_expense, get_expense_summary

# Onboarding
from core.onboarding import get_or_create_onboarding, mark_step_complete, is_onboarding_complete

# Trial
from core.trial import start_trial, get_trial, is_trial_active, mark_trial_converted

# Activation
from core.activation import record_activation, is_activated

# Legal consent
from core.legal_consent import require_fresh_consent, record_consent, requires_reacceptance

# Fraud
from core.fraud import record_fraud_event, detect_api_abuse, detect_ai_abuse, lock_account

# Financial
from core.financial_governance import record_stripe_transaction, get_gross_margin

# Data retention
from core.data_retention import request_data_deletion, archive_tenant_data

# Listings
from core.listings import create_listing, list_listings, update_listing, delete_listing

# Purchases
from core.purchase_delivery import deliver_purchase, has_purchased

# Capability check
from core.capability_loader import is_capability_enabled
```

---

**Platform version:** 4.0 | **Capabilities built:** 44/53 | **Tests:** 178 passing
