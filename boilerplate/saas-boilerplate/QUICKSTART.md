# Quick Start Guide

Configure and deploy a new SaaS business on this platform.

> **Running locally?** See [LOCAL_DEV.md](./LOCAL_DEV.md) for venv setup, local servers, and test commands.

---

## Prerequisites

- Python 3.9+
- Node.js 18+
- Git

---

## Step 1: Install Dependencies

```bash
# Backend
cd saas-boilerplate/backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

---

## Step 2: Set Up Environment Variables

```bash
cd saas-boilerplate/backend
cp .env.example .env
```

Open `.env` and fill in the values below.

### Auth0 (authentication)

1. Sign up at [auth0.com](https://auth0.com)
2. Create a **Single Page Application**
3. Under Settings, add your production domain to:
   - Allowed Callback URLs: `https://yourdomain.com`
   - Allowed Logout URLs: `https://yourdomain.com`
   - Allowed Web Origins: `https://yourdomain.com`
4. Create an **API** (for backend JWT validation)

```env
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_client_id_here
AUTH0_CLIENT_SECRET=your_client_secret_here
AUTH0_AUDIENCE=https://your-tenant.auth0.com/api/v2/
```

Create `saas-boilerplate/frontend/.env.local` (gitignored):
```env
REACT_APP_API_URL=https://api.yourdomain.com/api
REACT_APP_AUTH0_DOMAIN=your-tenant.auth0.com
REACT_APP_AUTH0_CLIENT_ID=your_client_id_here
```

> For local dev, add `https://yourdomain.com` **and** your local URLs in Auth0 — see [LOCAL_DEV.md](./LOCAL_DEV.md).

### Stripe (payments)

1. Sign up at [stripe.com](https://stripe.com)
2. Go to Developers → API Keys → copy the **Secret key**
3. Go to Developers → Webhooks → Add endpoint
   - URL: `https://api.yourdomain.com/api/webhooks/stripe`
   - Events to listen for:
     - `charge.succeeded`
     - `customer.subscription.created`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `charge.dispute.created`
     - `radar.early_fraud_warning.created`
4. Copy the **Signing secret**

```env
STRIPE_SECRET_KEY=sk_live_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here
```

### Sentry (error tracking)

1. Sign up at [sentry.io](https://sentry.io)
2. Create a **Python** project
3. Copy the DSN from Settings → Client Keys

```env
SENTRY_DSN=https://xxxxx@oyyy.ingest.sentry.io/zzzz
ENV=production
APP_VERSION=4.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### MailerLite (email — optional)

1. Sign up at [mailerlite.com](https://mailerlite.com)
2. Go to Integrations → API

```env
MAILERLITE_API_KEY=your_api_key_here
```

### Google Analytics (optional)

1. Create a GA4 property at [analytics.google.com](https://analytics.google.com)
2. Go to Data Streams → your stream → Measurement Protocol API secrets

```env
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
GA4_API_SECRET=your_secret_here
```

---

## Step 3: Configure Your Business

Copy the template and fill it in:

```bash
cp saas-boilerplate/frontend/src/config/business_config.example.json \
   saas-boilerplate/frontend/src/config/business_config.json
```

Open `business_config.json` and update each section:

---

### `business` — identity
```json
"business": {
  "name": "YourBusiness",
  "tagline": "One-line sell",
  "url": "https://yourdomain.com",
  "support_email": "support@yourdomain.com"
}
```

---

### `branding` — visual identity
Controls **every brand-colored element** in the app automatically — buttons, stat tiles, CTA links. Change `primary_color` once and the whole UI rebrands.

```json
"branding": {
  "primary_color": "#4F46E5",
  "logo_url": "",
  "favicon_url": "",
  "company_name": "YourBusiness"
}
```

Replace the logo file:
```bash
cp ~/your-logo.svg saas-boilerplate/frontend/public/logo.svg
```

---

### `dashboard` — inner-app UX
Configures what users see inside the authenticated app. `nav_items` controls the dashboard navigation links.

```json
"dashboard": {
  "theme": "light",
  "show_upgrade_banner": true,
  "nav_items": [
    { "label": "Dashboard", "path": "/dashboard", "icon": "grid" },
    { "label": "Settings",  "path": "/settings",  "icon": "cog"  }
  ],
  "hero_support_url": "https://yourdomain.com/support",
  "hero_docs_url":    "https://docs.yourdomain.com"
}
```

---

### `metadata` — analytics and SEO
Set `google_analytics_id` and GA4 loads automatically on every page. No code change needed.

```json
"metadata": {
  "analytics": {
    "google_analytics_id": "G-XXXXXXXXXX"
  },
  "seo": {
    "title": "YourBusiness — your tagline",
    "description": "Two-sentence description for search engines."
  }
}
```

---

### `stripe_products` — pricing plans
Each key is a Stripe Product ID. The pricing page renders these automatically — add/remove plans here and the grid adapts.

```json
"stripe_products": {
  "prod_YOUR_STARTER_ID": {
    "name": "Starter",
    "price_monthly": 9,
    "price_annual": 86,
    "popular": false,
    "cta_text": "Get Started",
    "stripe_price_id_monthly": "price_REPLACE_ME",
    "stripe_price_id_annual":  "price_REPLACE_ME",
    "features": ["Feature one", "Feature two", "Email support"],
    "entitlements": ["dashboard", "feature_one"]
  }
}
```

**Create Stripe products and get price IDs** (run once from your venv):

```python
import sys; sys.path.insert(0, 'teebu-shared-libs/lib')
from stripe_lib import load_stripe_lib

stripe = load_stripe_lib({'api_key': 'sk_live_your_key'})
result = stripe.create_complete_subscription_product(
    business_name="YourBusiness",
    monthly_price_dollars=9.00,
    annual_price_dollars=86.00,
)
print(result["monthly_price_id"])  # → paste as stripe_price_id_monthly
print(result["annual_price_id"])   # → paste as stripe_price_id_annual
```

---

### `auth0` and `mailerlite`
Paste in the credentials you set in `.env`:

```json
"auth0": {
  "domain":        "your-tenant.auth0.com",
  "client_id":     "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "audience":      "https://your-tenant.auth0.com/api/v2/"
},
"mailerlite": {
  "api_key":  "YOUR_API_KEY",
  "group_id": "YOUR_GROUP_ID"
}
```

---

## Step 4: Run the Tests

Confirm everything is wired correctly before deploying:

```bash
cd saas-boilerplate/backend
source venv/bin/activate
pytest tests/test_p0_capabilities.py -v
```

Expected output:
```
...
178 passed, 1 warning in 6.5s
```

All tests use SQLite in-memory — no external services needed.

---

## Step 5: Deploy

**Backend → Railway**
1. Push to GitHub
2. Connect repo at [railway.app](https://railway.app)
3. Set all `.env` vars in the Railway dashboard
4. Railway auto-deploys on every push

**Frontend → Vercel**
1. Connect repo at [vercel.com](https://vercel.com)
2. Set `REACT_APP_*` environment variables in Vercel dashboard
3. Vercel auto-deploys on every push

**Stripe webhook**
After backend deploys, update your Stripe webhook URL to:
`https://api.yourdomain.com/api/webhooks/stripe`

---

## Step 6: Give Yourself Admin Access

The admin panel (`/admin`) is protected by two layers — Auth0 login + an `admin` role check on every backend endpoint. You must assign the `admin` role to yourself in Auth0. This is a one-time step per deployment.

### 1. Create the `admin` role in Auth0

1. Log in to [manage.auth0.com](https://manage.auth0.com)
2. In the left sidebar go to **User Management → Roles**
3. Click **+ Create Role**
4. Name: `admin` — Description: `Full access to admin panel and API`
5. Click **Create**

### 2. Assign yourself the role

1. Sign up at `https://yourdomain.com/signup`
2. In Auth0 go to **User Management → Users** → find your account
3. Click your user → go to the **Roles** tab
4. Click **Assign Roles** → select `admin` → **Assign**

### 3. Configure Auth0 to include roles in the JWT

Auth0 does **not** include roles in the token by default. Add an Action to inject them.

1. In the left sidebar go to **Actions → Library**
2. Click **+ Build Custom** → name it `Add roles to token` → Runtime: `Node 18`
3. Paste this code:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://teebu.com/roles';
  const roles = event.authorization?.roles || [];
  api.idToken.setCustomClaim(namespace, roles);
  api.accessToken.setCustomClaim(namespace, roles);
};
```

4. Click **Deploy**
5. Go to **Actions → Flows → Login**
6. Drag `Add roles to token` into the flow between **Start** and **Complete**
7. Click **Apply**

### 4. Verify

Log out and log back in (new token with your role is issued on next login).

Open `https://yourdomain.com/admin` — if you see the dashboard, you're in.

> **Note:** The namespace `https://teebu.com/roles` is hardcoded in the frontend admin pages and in `core/rbac.py`. Do not change it unless you update both.

---

## Step 7: Add Your Business Logic

The auto-loader means zero integration overhead.

### Add a backend feature:

```python
# business/backend/routes/my_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db

router = APIRouter()

@router.get("/list")
def list_items(db: Session = Depends(get_db)):
    return {"items": []}
```

Redeploy → `GET https://api.yourdomain.com/api/my_feature/list` is live.

### Add a frontend page:

```jsx
// business/frontend/pages/MyFeature.jsx
import DashboardLayout from '../platform';

export default function MyFeature() {
  return (
    <DashboardLayout title="My Feature">
      <DashboardLayout.Card>Your content here</DashboardLayout.Card>
    </DashboardLayout>
  );
}
```

Redeploy → `https://yourdomain.com/dashboard/my-feature` is live.

---

## Next

- Full capability reference: [README.md](./README.md)
- Build directive for Claude: [CLAUDE_BUILD_DIRECTIVE.md](../CLAUDE_BUILD_DIRECTIVE.md)
- Local dev and testing: [LOCAL_DEV.md](./LOCAL_DEV.md)
