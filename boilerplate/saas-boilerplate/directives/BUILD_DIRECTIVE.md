# BUILD DIRECTIVE - InboxTamer Example

**READ THIS FIRST: Instructions for Claude Code / FounderOps / AF Scripts**

---

## Overview

This project uses a **plugin architecture**:
- **saas-boilerplate/** = Generic code (DON'T TOUCH)
- **business/** = Your custom code (BUILD HERE)

The boilerplate automatically loads everything from `business/`.

---

## Directory Structure

```
project-root/
├── saas-boilerplate/           # GENERIC - Don't modify
│   ├── backend/core/           # Generic routes (auth, payments, etc)
│   ├── frontend/src/core/      # Generic components
│   └── [infrastructure files]
│
├── business/                   # CUSTOM - Build here
│   ├── backend/routes/         # Add your API endpoints here
│   ├── frontend/pages/         # Add your React pages here
│   └── config/
│       └── business_config.json
│
└── directives/                 # INSTRUCTIONS
    ├── BUILD_DIRECTIVE.md      # This file
    ├── backend_directive.md    # Backend instructions
    └── frontend_directive.md   # Frontend instructions
```

---

## ⚡ ENTITLEMENTS: Generate From INTAKE Schedule

**The INTAKE schedule defines the products and features. You generate the entitlement map.**

### Step 1: Read INTAKE schedule for pricing tiers

The INTAKE output contains a schedule with tier definitions:
```json
{
  "pricing": {
    "tier1": { "name": "Starter", "price": "$9/mo", "features": ["dashboard", "basic_rules"] },
    "tier2": { "name": "Pro",     "price": "$29/mo", "features": ["dashboard", "basic_rules", "ai_sorting"] }
  }
}
```

### Step 2: Generate stripe_products section in business_config.json

```json
{
  "stripe_products": {
    "prod_REPLACE_WITH_STARTER_ID": {
      "name": "Starter",
      "price": "$9/mo",
      "entitlements": ["dashboard", "basic_rules"]
    },
    "prod_REPLACE_WITH_PRO_ID": {
      "name": "Pro",
      "price": "$29/mo",
      "entitlements": ["dashboard", "basic_rules", "ai_sorting"]
    }
  },
  "features": {
    "dashboard":   { "tier": 1, "label": "Dashboard",  "description": "Main app dashboard" },
    "basic_rules": { "tier": 1, "label": "Rules",       "description": "Create email rules" },
    "ai_sorting":  { "tier": 2, "label": "AI Sorting",  "description": "AI email sorting" }
  }
}
```

### Step 3: Generate routes WITH entitlement guards

```python
# business/backend/routes/ai_sort.py
from core.entitlements import require_entitlement

router = APIRouter()

@router.post("/sort")
def ai_sort(user=Depends(require_entitlement("ai_sorting"))):
    # Only Pro+ users reach here
    ...
```

### Step 4: Generate pages WITH EntitlementGate

```jsx
// business/frontend/pages/AISorting.jsx
import EntitlementGate from 'saas-boilerplate/core/EntitlementGate';

export default function AISorting() {
  return (
    <EntitlementGate feature="ai_sorting" planName="Pro">
      <AISortingPanel />
    </EntitlementGate>
  );
}
```

### Hero's Only Job After Build

1. Create products in Stripe matching the names in business_config.json
2. Copy real product IDs into business_config.json (replace prod_REPLACE_WITH_*)
3. Add webhook endpoint in Stripe: `https://domain.com/api/webhooks/stripe`
4. Done - entitlement system is live

---

## ⚡ CRITICAL: Auto-Loader - Zero Integration Required

**THE BOILERPLATE HAS AUTO-LOADER. YOU DO NOT INTEGRATE. YOU JUST DROP FILES.**

### What This Means

Starting in v2.0, the boilerplate **automatically scans and loads** everything in `business/`.

**DO NOT:**
- ❌ Import your routes in main.py
- ❌ Call app.include_router()
- ❌ Edit main.py at all
- ❌ Import your pages in App.js
- ❌ Add <Route> definitions
- ❌ Edit App.js at all

**DO:**
- ✅ Drop files in business/backend/routes/
- ✅ Drop files in business/frontend/pages/
- ✅ Start server
- ✅ Files auto-load

**That's it. No integration. Files appear as endpoints/pages automatically.**

---

## What Gets Auto-Loaded

### Backend: Any file in `business/backend/routes/*.py`

**Requirements:**
- Must have a `router` variable (FastAPI router)
- Router will be automatically mounted to `/api/{filename}`

**Example:** `business/backend/routes/email_rules.py`
```python
from fastapi import APIRouter

router = APIRouter()  # REQUIRED variable name

@router.get("/list")
def list_rules():
    return {"rules": []}
```

**Result:** Endpoint available at `/api/email_rules/list`

**NO IMPORT NEEDED. NO REGISTRATION NEEDED.**

---

### Frontend: Any file in `business/frontend/pages/*.jsx`

**Requirements:**
- Must export default a React component
- Filename determines route path (PascalCase → kebab-case)

**Example:** `business/frontend/pages/EmailDashboard.jsx`
```jsx
export default function EmailDashboard() {
  return <div>Email Dashboard</div>;
}
```

**Result:** Page available at `/dashboard/email-dashboard`

**NO IMPORT NEEDED. NO ROUTE DEFINITION NEEDED.**

---

## Verification (How To Know It Worked)

### Backend
Start server and check logs:
```bash
cd saas-boilerplate/backend
uvicorn main:app --reload

# You should see:
# ✓ Database initialized
# ✓ Loaded: email_rules -> /api/email_rules
# ✓ Loaded: schedule -> /api/schedule
# Successfully loaded 2 business route(s)
```

Test endpoint:
```bash
curl http://localhost:8000/api/email_rules/list
```

### Frontend
Start dev server and check console:
```bash
cd saas-boilerplate/frontend
npm start

# Console shows:
# ✓ Loaded business page: EmailDashboard -> /dashboard/email-dashboard
```

Visit page:
```
http://localhost:3000/dashboard/email-dashboard
```

**If you see these logs, auto-loader is working. You're done.**

---

## Configuration

### Edit `business/config/business_config.json`

This controls ALL text, colors, pricing, features:

```json
{
  "business": {
    "name": "InboxTamer",
    "tagline": "Your tagline here"
  },
  "branding": {
    "primary_color": "#3B82F6"
  },
  "home": {
    "hero": {
      "headline": "Your headline"
    }
  }
}
```

**The boilerplate reads this and applies it everywhere.**

---

## Build Instructions by Role

### For Claude Code:

```
You are building InboxTamer.

1. Read: directives/backend_directive.md for backend requirements
2. Read: directives/frontend_directive.md for frontend requirements
3. Create files in business/ directory ONLY
4. Never modify saas-boilerplate/ directory
5. Use boilerplate's shared libraries (already imported)
6. Test endpoints at http://localhost:8000/api/your-route
```

### For FounderOps:

```
Customer wants: [Business idea from intake]

1. Analyze business requirements
2. Determine what custom logic is needed
3. Check directives/{service}_directive.md for patterns
4. Generate code in business/ directory
5. Update business/config/business_config.json with branding
6. Never touch saas-boilerplate/ - it's infrastructure
```

### For AF Scripts:

```bash
#!/bin/bash
# Automated build for AF portfolio

BUSINESS_NAME=$1
BUSINESS_IDEA=$2

# 1. Copy boilerplate
cp -r saas-boilerplate/ "$BUSINESS_NAME/"

# 2. Read directives
cat directives/BUILD_DIRECTIVE.md

# 3. Generate business logic
# Pass to Claude Code with directive context

# 4. Deploy
cd "$BUSINESS_NAME"
./deploy.sh
```

---

## What Boilerplate Provides (Already Built)

### Backend Routes (DON'T REBUILD):
- ✅ `/api/auth/signup` - User registration
- ✅ `/api/auth/login` - User login (via Auth0)
- ✅ `/api/payments/subscribe` - Create subscription
- ✅ `/api/payments/cancel` - Cancel subscription
- ✅ `/api/webhooks/stripe` - Stripe webhooks
- ✅ `/api/analytics/track` - Track events
- ✅ `/api/contact` - Contact form

### Frontend Pages (DON'T REBUILD):
- ✅ Home page (from config)
- ✅ Pricing page (from config)
- ✅ Login/Signup (Auth0)
- ✅ Generic Dashboard
- ✅ Account Settings
- ✅ Terms/Privacy
- ✅ FAQ
- ✅ Contact

### Components (DON'T REBUILD):
- ✅ Navbar with auth
- ✅ Footer
- ✅ Pricing cards
- ✅ Feature cards
- ✅ Protected routes

### Integrations (ALREADY CONFIGURED):
- ✅ Stripe payments
- ✅ Auth0 authentication
- ✅ MailerLite emails
- ✅ Google Analytics
- ✅ Git operations

---

## What You Need to Build (Business Logic)

### Example: InboxTamer

#### Backend Routes Needed:
```
business/backend/routes/
├── inbox.py          # Connect Gmail/Outlook via OAuth
├── rules.py          # Email rule CRUD
├── ai_sorting.py     # AI categorization
└── analytics.py      # Email analytics (custom)
```

#### Frontend Pages Needed:
```
business/frontend/pages/
├── InboxDashboard.jsx    # Main email view
├── RulesEditor.jsx       # Create/edit rules
├── EmailAnalytics.jsx    # Charts and insights
└── Settings.jsx          # InboxTamer-specific settings
```

#### Config Updates:
```json
{
  "business": {"name": "InboxTamer"},
  "home": {
    "hero": {"headline": "Tame Your Inbox in Minutes"}
  },
  "pricing": {
    "plans": [
      {"name": "Pro", "price_monthly": 49}
    ]
  }
}
```

---

## Example: CourtDominion

#### Backend Routes Needed:
```
business/backend/routes/
├── nba_data.py       # Fetch NBA stats
├── projections.py    # ML player projections
├── lineup.py         # Lineup optimizer
└── leagues.py        # User leagues CRUD
```

#### Frontend Pages Needed:
```
business/frontend/pages/
├── PlayerDashboard.jsx   # Player stats and projections
├── LineupBuilder.jsx     # Drag-drop lineup tool
├── Projections.jsx       # Projection engine
└── Leagues.jsx           # Manage leagues
```

---

## File Naming Conventions

### Backend:
- **Route files:** snake_case (e.g., `email_rules.py`)
- **Classes:** PascalCase (e.g., `EmailRule`)
- **Functions:** snake_case (e.g., `get_rules()`)

### Frontend:
- **Components:** PascalCase (e.g., `EmailDashboard.jsx`)
- **Files:** PascalCase (e.g., `RulesEditor.jsx`)
- **Functions:** camelCase (e.g., `handleSubmit()`)

---

## Using Boilerplate Services

### In Backend Routes:

```python
# business/backend/routes/your_route.py
from fastapi import APIRouter, Depends
from saas_boilerplate.core.auth import get_current_user
from saas_boilerplate.core.analytics import track_event

router = APIRouter()

@router.post("/your-endpoint")
async def your_endpoint(user = Depends(get_current_user)):
    # Use shared analytics
    track_event("feature_used", user_id=user.id)
    
    # Your business logic here
    return {"success": True}
```

### In Frontend Pages:

```jsx
// business/frontend/pages/YourPage.jsx
import { useAuth } from 'saas-boilerplate/core/hooks';
import { Navbar, Footer } from 'saas-boilerplate/core/components';

export default function YourPage() {
  const { user } = useAuth();
  
  return (
    <>
      <Navbar />
      <div>Your custom content</div>
      <Footer />
    </>
  );
}
```

---

## Testing Your Custom Code

### Backend:
```bash
cd saas-boilerplate/backend
uvicorn main:app --reload

# Test your custom endpoint
curl http://localhost:8000/api/your-route/your-endpoint
```

### Frontend:
```bash
cd saas-boilerplate/frontend
npm start

# Visit your custom page
open http://localhost:3000/dashboard/your-page
```

---

## Deployment

### What Gets Deployed:

1. **Boilerplate (infrastructure)** - generic code
2. **Business directory** - your custom logic
3. **Config** - your branding/content

### Deploy Command:
```bash
./deploy.sh --business=inboxtamer
```

This deploys both layers as one application.

---

## Common Patterns

### Pattern 1: CRUD API
```python
# business/backend/routes/items.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_items(): return []

@router.post("/")
def create_item(item: dict): return item

@router.get("/{id}")
def get_item(id: str): return {}

@router.put("/{id}")
def update_item(id: str, item: dict): return item

@router.delete("/{id}")
def delete_item(id: str): return {"deleted": True}
```

### Pattern 2: React Data Table
```jsx
// business/frontend/pages/ItemsList.jsx
import { useState, useEffect } from 'react';
import api from 'saas-boilerplate/utils/api';

export default function ItemsList() {
  const [items, setItems] = useState([]);
  
  useEffect(() => {
    api.get('/items').then(r => setItems(r.data));
  }, []);
  
  return (
    <table>
      {items.map(item => <tr key={item.id}>{item.name}</tr>)}
    </table>
  );
}
```

---

## Error Handling

### Backend:
```python
from fastapi import HTTPException

@router.get("/risky")
def risky_operation():
    try:
        # Your logic
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend:
```jsx
async function handleAction() {
  try {
    await api.post('/your-endpoint');
  } catch (error) {
    alert('Error: ' + error.message);
  }
}
```

---

## Security Notes

### Authentication (Already Handled):
- All routes under `/api/*` can use `Depends(get_current_user)`
- All frontend pages can use `useAuth()` hook
- Protected routes auto-redirect to login

### Authorization (You Build):
```python
@router.get("/admin-only")
def admin_only(user = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403)
    return {"data": "secret"}
```

---

## Checklist

Before marking business logic "complete":

### Backend:
- [ ] All custom routes in `business/backend/routes/`
- [ ] Routes have proper error handling
- [ ] Routes use shared auth if needed
- [ ] API tested with curl/Postman
- [ ] Analytics events tracked

### Frontend:
- [ ] All custom pages in `business/frontend/pages/`
- [ ] Pages use shared components (Navbar, Footer)
- [ ] Pages handle loading/error states
- [ ] Mobile responsive
- [ ] Analytics tracked

### Config:
- [ ] business_config.json updated with all content
- [ ] Pricing plans have correct Stripe IDs
- [ ] All text/colors customized
- [ ] Logo replaced

### Testing:
- [ ] Backend responds at localhost:8000
- [ ] Frontend loads at localhost:3000
- [ ] Custom pages accessible
- [ ] Auth flow works
- [ ] Payment flow works

---

## Getting Help

### Documentation:
- Backend patterns: `directives/backend_directive.md`
- Frontend patterns: `directives/frontend_directive.md`
- Boilerplate API: `saas-boilerplate/API.md`

### Examples:
- See `business/` directory for starter examples
- Each directive has code snippets

---

## Summary

**You are building business logic ONLY.**

✅ Auth, payments, emails, analytics → Already done  
✅ Generic pages (Home, Pricing, etc) → Already done  
✅ All infrastructure → Already done  

❌ DON'T touch `saas-boilerplate/`  
✅ DO build in `business/`  
✅ DO update `business/config/business_config.json`  

**The boilerplate auto-loads everything from `business/`.**

---

**Ready to build? Start with:**
1. Read `directives/backend_directive.md`
2. Read `directives/frontend_directive.md`
3. Create your first route in `business/backend/routes/`
4. Create your first page in `business/frontend/pages/`
5. Test locally
6. Deploy

**Go build. 🚀**
