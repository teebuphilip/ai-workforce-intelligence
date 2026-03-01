# P0 Kernel Build Directive
## For: Claude Instance #2 (Platform Builder)

**Mission:** Build the missing P0 capabilities into teebu-saas-platform to complete the production-ready kernel.

**Context:** There is a parallel track where another Claude instance is shipping products (CD, AFH, FO). Your job is to build the foundational platform capabilities they'll all need.

---

## Your Inputs

You have been given:

1. **PLATFORM_CAPABILITIES.md** - The canonical spec defining all 20 core capabilities (13 P0, 7 P1)
2. **teebu-saas-platform/** - Existing codebase with 7 capabilities already built (~4,300 lines)
3. **This directive** - Your marching orders

---

## Your Mission

**Build the 10 missing P0 capabilities** so the platform is production-ready.

You are NOT building products (CD, AFH, FO). You are building the **reusable kernel** they will all run on.

---

## What's Already Built (Don't Rebuild)

From teebu-saas-platform codebase:

| Capability | File | Status |
|-----------|------|--------|
| Authentication | `teebu-shared-libs/lib/auth0_lib.py` (750 lines) | ✅ Done |
| Billing | `teebu-shared-libs/lib/stripe_lib.py` (828 lines) | ✅ Done |
| Marketing Email | `teebu-shared-libs/lib/mailerlite_lib.py` (680 lines) | ✅ Done |
| Entitlements | `saas-boilerplate/backend/core/entitlements.py` | ✅ Done |
| Social Posting | `saas-boilerplate/backend/core/posting.py` | ✅ Done |
| Git Operations | `teebu-shared-libs/lib/git_lib.py` (720 lines) | ✅ Done |
| Analytics | `teebu-shared-libs/lib/analytics_lib.py` (650 lines) | ✅ Done |

**Do not touch these. They work.**

---

## What You Must Build (10 P0 Gaps)

Build these in priority order:

### Priority 1: Infrastructure (Week 1-2)

#### 1. Multi-Tenancy (8-10 hours) 🔴 P0
**File:** `saas-boilerplate/backend/core/tenancy.py`

**What it does:**
- Adds `tenant_id` column to all tables
- Middleware that automatically scopes all queries to current tenant
- Prevents cross-tenant data leaks

**Implementation approach:**
```python
# Middleware that injects tenant_id into all DB queries
# Every request must have tenant context
# All SQLAlchemy queries auto-filtered by tenant_id
```

**Validation:**
- [ ] Create 2 test tenants
- [ ] Insert data for tenant A
- [ ] Query as tenant B
- [ ] Verify tenant B cannot see tenant A's data

---

#### 2. AI Cost Tracking Dashboard (6-8 hours) 🔴 P0
**Files:** 
- `saas-boilerplate/backend/core/ai_governance.py` (wrapper layer)
- `saas-boilerplate/frontend/src/pages/CostDashboard.jsx` (UI)

**What it does:**
- Wraps all Claude/ChatGPT API calls
- Logs: timestamp, tenant_id, model, tokens_in, tokens_out, cost
- Dashboard shows: cost per tenant, cost per feature, daily/weekly/monthly trends

**Implementation approach:**
```python
# All AI calls go through this wrapper
def call_ai(prompt, model="sonnet", tenant_id=None, feature=None):
    # Log request
    # Call API
    # Log response + cost
    # Store in costs table
    return response
```

**Data from existing:**
- `fo_run_log.csv` has the schema (date, startup, iterations, cost_claude, cost_chatgpt, total_cost)
- Migrate this to DB table: `ai_costs`

**Validation:**
- [ ] Make 10 AI calls through wrapper
- [ ] Verify all logged to DB
- [ ] Dashboard shows costs per tenant
- [ ] Export to CSV works

---

#### 3. AI Budget Enforcement (4-6 hours) 🔴 P0
**File:** `saas-boilerplate/backend/core/ai_governance.py` (extend)

**What it does:**
- Set budget limits per tenant (e.g., $500/month)
- Check current spend before each AI call
- If at 90% → alert admin
- If at 100% → block AI calls until next month OR charge overage

**Implementation approach:**
```python
def check_budget(tenant_id):
    monthly_spend = get_monthly_spend(tenant_id)
    budget = get_tenant_budget(tenant_id)
    if monthly_spend >= budget:
        raise BudgetExceededError()
    elif monthly_spend >= budget * 0.9:
        send_alert("Approaching budget limit")
```

**Validation:**
- [ ] Set tenant budget to $10
- [ ] Make AI calls totaling $9.50
- [ ] Verify alert sent
- [ ] Make call that would exceed $10
- [ ] Verify blocked

---

#### 4. AI Model Routing (4-6 hours) 🔴 P0
**File:** `saas-boilerplate/backend/core/ai_governance.py` (extend)

**What it does:**
- Route expensive calls to Sonnet, cheap calls to Haiku
- Per-tenant tier determines which models available
- Admin can override routing rules

**Implementation approach:**
```python
def route_model(task_type, tenant_tier):
    if task_type == "qa_iteration" and iteration > 1:
        return "claude-haiku-4"
    elif tenant_tier == "basic":
        return "claude-haiku-4"
    elif tenant_tier == "pro":
        return "claude-sonnet-4"
    return default_model
```

**Validation:**
- [ ] Basic tier tenant makes AI call
- [ ] Verify routed to Haiku
- [ ] Pro tier tenant makes AI call
- [ ] Verify routed to Sonnet

---

### Priority 2: Observability (Week 2-3)

#### 5. Error Tracking - Sentry Integration (2-3 hours) 🔴 P0
**Files:**
- `saas-boilerplate/backend/core/monitoring.py`
- Update `requirements.txt` to add `sentry-sdk`

**What it does:**
- Wraps FastAPI app with Sentry
- All exceptions automatically logged
- Tenant context included in errors

**Implementation approach:**
```python
import sentry_sdk
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))

# Add tenant context to all errors
sentry_sdk.set_context("tenant", {
    "tenant_id": current_tenant_id,
    "tier": tenant_tier
})
```

**Validation:**
- [ ] Trigger an exception
- [ ] Verify appears in Sentry dashboard
- [ ] Verify tenant_id is in error context

---

#### 6. Backups & Recovery (2-3 hours) 🔴 P0
**Files:**
- `docs/BACKUP_RECOVERY.md` (documentation)
- Railway dashboard configuration

**What it does:**
- Configure Railway auto-backup (daily snapshots, 30-day retention)
- Document restore procedure step-by-step
- **Test the restore procedure**

**Implementation approach:**
1. Enable Railway auto-backup in dashboard
2. Set retention to 30 days
3. Create test database
4. Take manual backup
5. Delete test data
6. Restore from backup
7. Verify data restored
8. Document every step

**Validation:**
- [ ] Backup configured in Railway
- [ ] Restore procedure documented
- [ ] **Restore procedure tested successfully**
- [ ] Measure RTO (time to restore)
- [ ] Measure RPO (data loss window)

---

### Priority 3: Access Control (Week 3-4)

#### 7. Role-Based Access (2-3 hours) 🔴 P0
**File:** `saas-boilerplate/backend/core/rbac.py`

**What it does:**
- Middleware checks user role before allowing access
- Roles: admin, user, viewer
- Admin can manage users, billing, costs
- User can use features
- Viewer can only read

**Implementation approach:**
```python
# Use Auth0 roles (already exists)
# Middleware decorator:
@require_role("admin")
def admin_endpoint():
    pass
```

**Validation:**
- [ ] Create admin user
- [ ] Create regular user
- [ ] Admin can access admin endpoints
- [ ] Regular user cannot access admin endpoints

---

#### 8. Session Management (2-3 hours) 🔴 P0
**File:** `saas-boilerplate/backend/core/auth.py` (extend auth0_lib)

**What it does:**
- Validate JWT tokens on every request
- Refresh tokens when expired
- Handle token revocation

**Implementation approach:**
```python
# Auth0 JWT validation middleware
# Automatically refresh if needed
# Store session context per request
```

**Validation:**
- [ ] Login creates valid JWT
- [ ] Expired token auto-refreshes
- [ ] Invalid token rejected

---

#### 9. Usage Limits (4-6 hours) 🔴 P0
**File:** `saas-boilerplate/backend/core/usage_limits.py`

**What it does:**
- Track usage per tenant (API calls, exports, etc.)
- Enforce hard limits per plan tier
- Block requests that exceed limits

**Implementation approach:**
```python
# Middleware counts requests per tenant
# Check against plan limits
# Return 429 Too Many Requests if exceeded

limits = {
    "basic": {"api_calls": 1000, "exports": 10},
    "pro": {"api_calls": 10000, "exports": 100}
}
```

**Validation:**
- [ ] Basic tier tenant makes 1001 API calls
- [ ] Verify 1001st call blocked
- [ ] Pro tier tenant makes 1001 calls
- [ ] Verify allowed

---

### Priority 4: Configuration (Week 4)

#### 10. Capability Registry (4-6 hours) 🔴 P0
**Files:**
- `saas-boilerplate/backend/config/capabilities.json`
- `saas-boilerplate/backend/core/capability_loader.py`

**What it does:**
- Central config for all P0/P1/P2 capabilities
- Per-tenant overrides (e.g., tenant A has P2 features enabled)
- Load capabilities on startup
- Enforce capability checks in middleware

**Implementation approach:**
```json
{
  "capabilities": {
    "ai_cost_tracking": {
      "priority": "P0",
      "enabled_by_default": true,
      "required_for_production": true
    },
    "social_posting": {
      "priority": "P2",
      "enabled_by_default": false,
      "tier_override": {
        "pro": true
      }
    }
  }
}
```

**Validation:**
- [ ] Load capabilities from JSON
- [ ] Verify P0 capabilities auto-enabled
- [ ] Verify P2 capabilities disabled for basic tier
- [ ] Verify P2 capabilities enabled for pro tier

---

## Your Constraints

**Follow these rules (from PLATFORM_CAPABILITIES.md Section 5):**

1. **No direct API calls** - All third-party services go through adapter libraries
2. **Single adapter per capability** - Don't duplicate code
3. **All AI calls through governance** - No exceptions
4. **All DB queries tenant-scoped** - No exceptions
5. **Capabilities configurable** - Everything in central config

**Code style:**
- Follow existing patterns in teebu-saas-platform
- Use same libraries (FastAPI, SQLAlchemy, React, Tailwind)
- Heavy comments (Teebu's preference)
- Simple, debuggable code (no clever tricks)

**Testing:**
- Every capability needs validation tests
- Use the checklists from PLATFORM_CAPABILITIES.md Section 8
- Actually run the tests, don't just write them

---

## Your Deliverables

**For each capability you build:**

1. **Code files** in appropriate directories
2. **Tests** that validate the capability works
3. **Documentation** in `docs/` explaining how to use it
4. **Configuration** added to capability registry
5. **Validation report** showing checklist items completed

**Final deliverable:**

A complete P0 kernel where:
- [ ] All 13 P0 capabilities working
- [ ] All validation checklists passed
- [ ] All tests passing
- [ ] All documentation written
- [ ] Platform ready for production use

---

## Your Timeline

**Week 1:** Multi-tenancy + AI Cost Tracking + AI Budget Enforcement + AI Model Routing  
**Week 2:** Error Tracking + Backups & Recovery  
**Week 3:** RBAC + Session Management + Usage Limits  
**Week 4:** Capability Registry + Testing + Documentation  

**Total: 4 weeks, ~45-60 hours of work**

---

## How to Start

1. **Read PLATFORM_CAPABILITIES.md thoroughly**
2. **Explore teebu-saas-platform codebase** - understand the existing structure
3. **Start with Multi-Tenancy** (highest impact, foundational)
4. **Build one capability at a time** - don't skip validation
5. **Test as you go** - don't wait until the end
6. **Document everything** - Teebu needs to maintain this solo

---

## Communication Protocol

**After completing each capability:**

Report back with:
- ✅ What was built (file paths, line count)
- ✅ What tests were run (validation checklist)
- ✅ What works (demo/proof)
- ✅ What's next (next capability to build)

**If blocked:**
- State the blocker clearly
- Propose 2-3 solutions
- Ask specific questions (not "what should I do?")

---

## Success Criteria

You are done when:

- [ ] All 13 P0 capabilities implemented
- [ ] All validation checklists from PLATFORM_CAPABILITIES.md Section 8 passed
- [ ] All tests passing
- [ ] All documentation complete
- [ ] Teebu can deploy a new tenant and it "just works"

**Your goal: Make the platform boring and reliable.**

No heroics. No clever code. Just solid, tested, documented infrastructure.

---

## Remember

You are building the **foundation**. 

The other Claude is building **products** on top of your work.

If you do your job right, they can ship CD, AFH, and FO without worrying about multi-tenancy, cost tracking, backups, or any of the infrastructure.

**Make it boring. Make it work. Make it solid.**

Go build.
