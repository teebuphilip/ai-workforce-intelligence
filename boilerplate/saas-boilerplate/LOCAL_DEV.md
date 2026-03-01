# Local Development Cheatsheet

Run the platform locally for development and testing before deploying.

---

## Start the Backend

```bash
cd saas-boilerplate/backend
source venv/bin/activate      # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Expected startup output:
```
============================================================
Starting YourBusinessName API v2.0
============================================================
✓ Sentry error tracking initialized
✓ All P0 capabilities configured
✓ Database initialized (all tables ready)
✓ Loaded 0 business route(s)
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Missing Auth0/Stripe/Sentry vars log warnings — not crashes. That's fine for local dev.

---

## Start the Frontend

In a second terminal:

```bash
cd saas-boilerplate/frontend
npm start
```

Opens `http://localhost:3000` automatically.

---

## Local Environment Variables

Minimum `.env` to run without any external services:

```env
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000
```

Frontend `.env.local`:
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_AUTH0_DOMAIN=your-tenant.auth0.com
REACT_APP_AUTH0_CLIENT_ID=your_client_id_here
```

---

## Auth0 — Add Local URLs

Your Auth0 application needs local URLs alongside production ones.
Go to Auth0 → Applications → your app → Settings and add to each field:

| Field | Add |
|---|---|
| Allowed Callback URLs | `http://localhost:3000` |
| Allowed Logout URLs | `http://localhost:3000` |
| Allowed Web Origins | `http://localhost:3000` |

Both `https://yourdomain.com` and `http://localhost:3000` can coexist in the same field (comma-separated).

---

## Stripe Webhooks Locally

Stripe can't reach `localhost` directly. Use the Stripe CLI to forward webhooks:

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

The CLI prints a webhook signing secret — paste it into `.env` as `STRIPE_WEBHOOK_SECRET` for local dev.

---

## Sanity Check URLs

```bash
# Backend health
curl http://localhost:8000/health
# → {"status": "healthy", ...}

# Config loaded
curl http://localhost:8000/api/config
# → your business_config.json contents

# Interactive API docs (browser)
open http://localhost:8000/docs
```

Frontend checklist:
- [ ] `http://localhost:3000` — home page with your branding
- [ ] `http://localhost:3000/pricing` — pricing plans appear
- [ ] `http://localhost:3000/login` — redirects to Auth0
- [ ] `http://localhost:3000/dashboard` — redirects to login if not authenticated
- [ ] `http://localhost:3000/admin` — admin panel (requires admin role assigned in Auth0)

---

## Admin Panel Locally

After assigning yourself the `admin` role in Auth0 (see [QUICKSTART.md Step 6](./QUICKSTART.md#step-6-give-yourself-admin-access)):

1. Log out at `http://localhost:3000`
2. Log back in — new token includes the role
3. Open `http://localhost:3000/admin`

To verify the token includes your role:
```bash
# Get a token from the browser (Network tab → any /api call → Authorization header)
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
# → {"users": [...]}  means admin role is working
# → {"detail": "Insufficient permissions"}  means role not in token yet — log out and back in
```

---

## Run Tests

```bash
cd saas-boilerplate/backend
source venv/bin/activate
pytest tests/test_p0_capabilities.py -v
```

Run a single test class:
```bash
pytest tests/test_p0_capabilities.py::TestMultiTenancy -v
```

All tests use SQLite in-memory — no database or external services needed.

---

## Common Local Issues

### `Module not found` / `ImportError`
```bash
pip install -r requirements.txt
```

### `CORS error` in browser
Check `.env`:
```env
CORS_ORIGINS=http://localhost:3000
```
Confirm backend is actually running on port 8000.

### Auth0 callback error
Check Auth0 application settings include `http://localhost:3000` in all three URL fields (see Auth0 section above).

### Stripe webhook signature error
Use Stripe CLI (see Stripe section above) — don't paste the production `whsec_` into your local `.env`.

### Tests failing
```bash
which python          # confirm correct Python
python --version      # should be 3.9+
pip install -r requirements.txt
```

### Port already in use
```bash
lsof -i :8000         # find what's using port 8000
kill -9 <PID>
```
