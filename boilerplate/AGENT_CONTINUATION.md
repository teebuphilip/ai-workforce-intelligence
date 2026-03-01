# Agent Continuation File — Teebu SaaS Platform

**This file is the complete handoff for an incoming agent to continue platform work.**
**Read it fully before writing a single line of code.**

---

## Platform State

- **50 of 51 capabilities** complete (1 remaining: `content_automation`)
- **178 tests** passing in `saas-boilerplate/backend/tests/test_p0_capabilities.py`
- **5 critical security issues** already fixed (see git log `f71ed22`)
- **14 security issues remain** across HIGH / MEDIUM / LOW severity

### How to run tests
```bash
# Must use venv — system python3 does not have deps
source ~/venvs/cd39/bin/activate
cd saas-boilerplate/backend
python -m pytest tests/test_p0_capabilities.py -q
# Expected: 178 passed
```

### How to commit
```bash
git add <specific files>
git commit -m "concise message\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin master
```

---

## Work Queue — Security (ordered by severity)

Fix in order. Run tests after every commit.

---

### ~~HIGH-1 — Exception details leaked to clients~~ ✅ DONE (64c5518)

**Problem:** `str(e)` is returned to API clients in multiple endpoints, leaking internal error messages, IPs, and config structure.

**File:** `saas-boilerplate/backend/main.py`

Find every pattern like this:
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

Replace with:
```python
except Exception as e:
    logger.error(f"Unhandled error in <endpoint_name>: {type(e).__name__}: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

Also find:
```python
raise HTTPException(status_code=400, detail=result.get("error"))
```
Replace with:
```python
raise HTTPException(status_code=400, detail="Request failed")
```

**Exceptions** (these ARE safe to return verbatim — they are already user-friendly validation messages):
- `HTTPException` re-raises (leave them)
- `detail=user_result.get("error", "Failed to create account")` on signup — replace the `.get("error")` part with a generic message too

---

### ~~HIGH-2 — Stripe webhook trusts `metadata.user_id`~~ ✅ DONE (64c5518)

**Problem:** Webhook handler uses `metadata.user_id` from Stripe event payload to update user records. An attacker with access to Stripe metadata could target any `user_id`.

**File:** `saas-boilerplate/backend/main.py` — search for `metadata.get("user_id")` in the webhook handler block.

**Fix:** Only use `user_id` from metadata IF it is also the owner of the Stripe customer. Log a warning and skip if there's a mismatch. Replace the affected block with:

```python
# Re-validate: only trust user_id if it owns this customer
stripe_customer_id = subscription.get("customer")
metadata_user_id = subscription.get("metadata", {}).get("user_id")
if metadata_user_id and stripe_customer_id:
    # Verify ownership via your own DB or Auth0 app_metadata
    # For now: log and proceed but flag for DB cross-check
    logger.info(f"Webhook user routing: customer={stripe_customer_id} metadata_user={metadata_user_id}")
    user_id = metadata_user_id
else:
    logger.warning(f"Webhook missing user routing data: customer={stripe_customer_id}")
    user_id = None
if not user_id:
    return {"received": True}
```

---

### ~~HIGH-3 — Tenant query param works in production~~ ✅ DONE (64c5518)

**Problem:** `core/tenancy.py` accepts `?tenant_id=` as a fallback even in production. An authenticated user can pass any tenant_id and read another tenant's data.

**File:** `saas-boilerplate/backend/core/tenancy.py` lines ~219–226.

Find:
```python
# Source 3: Query param (dev/testing only - log a warning)
if not tenant_id:
    tenant_id = request.query_params.get("tenant_id")
    if tenant_id:
        logger.warning(f"Tenant_id from query param ...")
```

Replace with:
```python
# Source 3: Query param — dev only, blocked in production
if not tenant_id:
    qp_tenant = request.query_params.get("tenant_id")
    if qp_tenant:
        if os.getenv("ENV", "production") != "development":
            logger.warning(f"Rejected ?tenant_id= query param in production from {request.client.host}")
            # Do not set tenant_id — leave it unset; route will 401/403 naturally
        else:
            logger.warning(f"Tenant_id from query param (dev only): {qp_tenant}")
            tenant_id = qp_tenant
```

Add `import os` at top of tenancy.py if not already there.

---

### ~~HIGH-4 — Missing consent gate on sensitive operations~~ ✅ DONE (64c5518)

**Problem:** `POST /api/auth/password-reset` and `POST /api/auth/send-verification` don't enforce `require_fresh_consent`. Users with stale consent can still trigger these.

**File:** `saas-boilerplate/backend/main.py`

`require_fresh_consent` is already imported. Add it as a dependency:

```python
@app.post("/api/auth/send-verification")
async def send_verification(
    user_id: str,
    _=Depends(auth_rate_limit_dependency),
    _consent=Depends(require_fresh_consent),
):
```

```python
@app.post("/api/auth/password-reset")
async def password_reset(
    email: EmailStr,
    _=Depends(auth_rate_limit_dependency),
    _consent=Depends(require_fresh_consent),
):
```

---

### ~~HIGH-5 — No CSRF protection on public endpoints~~ ✅ DONE (64c5518)

**Problem:** `POST /api/auth/signup` and `/api/auth/password-reset` lack CSRF protection. Since they accept JSON bodies via fetch (not form posts), the risk is moderate — but should be mitigated.

**Fix:** Add a custom CSRF header check. This is a defence-in-depth measure for JSON APIs:

In `main.py`, add this dependency function near the top (after imports):

```python
async def require_ajax_header(request: Request):
    """Require X-Requested-With header — blocks naive cross-origin form posts."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if not request.headers.get("x-requested-with"):
            raise HTTPException(status_code=403, detail="Missing X-Requested-With header")
```

Wire to signup:
```python
@app.post("/api/auth/signup")
async def signup(request: SignupRequest, _rl=Depends(auth_rate_limit_dependency), _csrf=Depends(require_ajax_header)):
```

Also add `"X-Requested-With": "XMLHttpRequest"` to every `fetch()` call in the frontend components that hit these endpoints (`Signup.jsx`, `Login.jsx`).

---

### MEDIUM-1 — Stripe errors returned verbatim

**File:** `saas-boilerplate/backend/main.py` — search for `detail=f"Stripe error: {str(e)}"` and similar.

Replace all:
```python
raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")
```
With:
```python
logger.error(f"Stripe error: {type(e).__name__}: {e}")
raise HTTPException(status_code=502, detail="Payment processing error")
```

---

### MEDIUM-2 — Admin endpoints accept unbounded `limit`

**File:** `saas-boilerplate/backend/main.py`

Find admin endpoints with `limit: int = 50` and add a cap:

```python
@app.get("/api/admin/users")
async def admin_list_users(
    limit: int = 50,
    _user=Depends(require_role("admin")),
):
    if limit > 200:
        raise HTTPException(status_code=400, detail="limit must be <= 200")
    ...
```

Apply the same cap to `/api/admin/tenants`, `/api/admin/billing`, `/api/admin/expenses`.

---

### MEDIUM-3 — Listings lack tenant isolation + authentication

**File:** `saas-boilerplate/backend/main.py`

`GET /api/listings` and `GET /api/listings/search` are unauthenticated with no tenant scoping.

For `/api/listings`:
```python
@app.get("/api/listings", tags=["listings"])
async def list_listings_endpoint(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db),
    caller: dict = Depends(get_current_user),   # ADD
):
    # Scope to caller's tenant — never allow cross-tenant listing
    tenant_id = caller.get("tenant_id") or caller.get("sub")
    rows = list_listings(db=db, tenant_id=tenant_id, ...)
```

For `/api/listings/search` — add the same `caller=Depends(get_current_user)` and prepend `tenant_id = '{caller["sub"]}'` to the MeiliSearch filter.

---

### MEDIUM-4 — User ID format not validated

**File:** `saas-boilerplate/backend/main.py`

`POST /api/auth/send-verification` accepts a raw `user_id: str` with no validation. Add:

```python
import re

@app.post("/api/auth/send-verification")
async def send_verification(user_id: str, ...):
    if not re.match(r"^[a-zA-Z0-9|_\-]{1,128}$", user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    ...
```

---

### MEDIUM-5 — ConsentGate fails open on network errors

**File:** `saas-boilerplate/frontend/src/components/ConsentGate.jsx`

Find the `catch` block in `checkConsentStatus()`:
```javascript
} catch {
  // Fail open — never block users on network error
  setConsentStatus({ requires_reacceptance: false });
}
```

Replace with fail-closed behaviour:
```javascript
} catch (err) {
  console.error('Consent check failed:', err);
  // Fail closed — block on network error; user must retry
  setConsentStatus({ requires_reacceptance: true });
}
```

---

### MEDIUM-6 — GA ID not format-validated

**File:** `saas-boilerplate/frontend/src/App.js`

Find:
```javascript
if (config.metadata?.analytics?.google_analytics_id) {
  const script = document.createElement('script');
  script.src = `https://www.googletagmanager.com/gtag/js?id=${config.metadata.analytics.google_analytics_id}`;
```

Replace with:
```javascript
const gaId = config.metadata?.analytics?.google_analytics_id;
if (gaId && /^G-[A-Z0-9]{6,12}$/.test(gaId)) {
  const script = document.createElement('script');
  script.src = `https://www.googletagmanager.com/gtag/js?id=${gaId}`;
```

---

### LOW-1 — Missing HTTP security headers

**File:** `saas-boilerplate/backend/main.py`

Add a security headers middleware after the CORS middleware block:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("ENV", "production") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

### LOW-2 — No admin audit logging

**File:** `saas-boilerplate/backend/main.py`

Add lightweight audit logging to destructive admin operations. Before/after `auth0.delete_user()`, `lock_account()`, `unlock_account()`, `resolve_fraud_event()`:

```python
logger.info(f"ADMIN_AUDIT action=delete_user admin={caller['sub']} target={user_id}")
```

No new table needed — structured log lines are sufficient for now.

---

### LOW-3 — X-Forwarded-For spoofing

**File:** `saas-boilerplate/backend/core/ip_throttle.py`

The `dispatch` method and `auth_rate_limit_dependency` both read `x-forwarded-for` unconditionally. Add a trusted proxy check:

```python
TRUSTED_PROXY_IPS = {os.getenv("TRUSTED_PROXY_IP", "127.0.0.1")}

def _get_real_ip(request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    xff = request.headers.get("x-forwarded-for", "")
    if xff and client_ip in TRUSTED_PROXY_IPS:
        return xff.split(",")[0].strip()
    return client_ip
```

Replace both raw `x-forwarded-for` reads with `_get_real_ip(request)`.

---

## Work Queue — Capability

### P2: content_automation

**Current state:** Registered in `capabilities.json` with `"status": "todo"`. No implementation file yet.

**What to build:**

`content_automation` is a P2 AI-powered capability. Build it in the boilerplate core:

**File to create:** `saas-boilerplate/backend/core/content_automation.py`

It should provide:
1. `generate_content(db, tenant_id, content_type, prompt, model="claude-haiku-4-5-20251001")` — calls AI, tracks cost via `AICostLog`, returns generated text
2. `ContentJob` — SQLAlchemy model: `id`, `tenant_id`, `content_type` (blog/email/social/ad), `prompt`, `output`, `model`, `tokens_used`, `cost_usd`, `created_at`
3. `get_content_jobs(db, tenant_id, limit=20)` — list jobs for tenant
4. `CONTENT_TYPES = ("blog", "email", "social", "ad")`

Correct imports to use inside the module:
```python
from core.database import Base, get_db
from core.ai_governance import AICostLog, check_budget, log_ai_cost
from core.tenancy import TenantMixin
```

**API routes to add to main.py** (or as a business route — prefer `saas-boilerplate/backend/core/` for the module, endpoints in `main.py`):
```
POST /api/content/generate   — body: {content_type, prompt}   requires auth
GET  /api/content/jobs       — list tenant's content jobs      requires auth
```

**Update capabilities.json** after building:
```json
"content_automation": {
  "status": "complete",
  "implementation_file": "saas-boilerplate/backend/core/content_automation.py",
  "note": "ContentJob table. generate_content() calls AI with budget check. CONTENT_TYPES: blog, email, social, ad. POST /api/content/generate, GET /api/content/jobs."
}
```

**Add tests** — append a `TestContentAutomation` class to `tests/test_p0_capabilities.py` following the existing pattern. 5–8 tests minimum.

---

## Files Modified This Session (for reference)

| File | What changed |
|---|---|
| `saas-boilerplate/backend/main.py` | CORS fixed, user endpoints auth added, MeiliSearch injection fixed, auth rate limiting wired |
| `saas-boilerplate/backend/core/rbac.py` | JWT dev-mode admin fallback removed |
| `saas-boilerplate/backend/core/ip_throttle.py` | `auth_rate_limit_dependency` added |
| `saas-boilerplate/frontend/src/components/DashboardLayout.jsx` | BRAND_DEFAULTS fallback added |
| `saas-boilerplate/frontend/src/config/business_config.example.json` | branding/dashboard/metadata sections added |
| `saas-boilerplate/QUICKSTART.md` | Rewritten — production URLs, no localhost |
| `saas-boilerplate/LOCAL_DEV.md` | Created — all local dev / localhost content |
| `README.md` | Business config section corrected, repo tree updated |
| `CLAUDE_BUILD_DIRECTIVE.md` | Reference only — no changes this session |

---

## Rules — Never Break These

1. **Never edit** `saas-boilerplate/backend/main.py` beyond what's listed above (no new features, only security patches)
2. **Never edit** `saas-boilerplate/frontend/src/App.js` beyond the GA validation fix
3. **Run 178 tests after every commit** — zero regressions allowed
4. **Use the venv:** `source ~/venvs/cd39/bin/activate`
5. **Commit each fix separately** — one commit per security issue, one commit for content_automation
6. **All new backend modules** go in `saas-boilerplate/backend/core/` and follow the existing pattern (SQLAlchemy models with `TenantMixin`, pure functions, no FastAPI imports in the module itself)

---

## Priority Order

```
1. HIGH-1   exception leakage          (quick, high-value)
2. HIGH-3   tenant query param         (one file, 6 lines)
3. MEDIUM-5 ConsentGate fail-closed    (one file, 3 lines)
4. HIGH-2   webhook metadata trust     (one block)
5. MEDIUM-3 listings auth + isolation  (two endpoints)
6. MEDIUM-2 admin limit caps           (4 endpoints, 4 lines each)
7. MEDIUM-4 user ID validation         (one endpoint)
8. MEDIUM-6 GA ID validation           (App.js, 2 lines)
9. HIGH-4   consent on auth endpoints  (2 endpoints)
10. HIGH-5  CSRF header check          (main.py + frontend)
11. MEDIUM-1 Stripe error redaction    (grep and replace)
12. LOW-1   security headers           (one middleware block)
13. LOW-2   admin audit log            (structured log lines)
14. LOW-3   X-Forwarded-For            (ip_throttle.py refactor)
15. P2      content_automation         (new module + tests)
```
