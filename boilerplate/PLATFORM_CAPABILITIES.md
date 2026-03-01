# Teebu SaaS Platform
# Business Capability & Tool Agreement (Core Platform)

**Version:** 1.0 (Canonical)  
**Last Updated:** February 22, 2026  
**Status:** Locked - Tool changes require explicit review

---

## Purpose

Define the canonical SaaS capability set and locked implementation choices.

**No product scoping. No schedule. This is the foundation.**

---

## TL;DR

Below is the **product-agnostic capability agreement**.

No CD. No AFH. No FO.

Just:
* Business Capability
* What it covers
* Locked tool (if selected)
* Priority level (platform-wide)
* Implementation approach

This is the baseline agreed upon before any product discussion.

---

# 1️⃣ Core Platform Capabilities (Mandatory Kernel)

These capabilities form the reusable SaaS platform layer.

| Domain          | Capability          | What It Covers                                                                        | Tool                | Platform Priority | Implementation Approach                                                                 |
| --------------- | ------------------- | ------------------------------------------------------------------------------------- | ------------------- | ----------------- | --------------------------------------------------------------------------------------- |
| Identity        | Authentication      | Login, logout, sessions                                                               | Auth0               | 🔴 P0             | Central auth adapter library                                                            |
| Identity        | Role-Based Access   | Admin/user roles                                                                      | Auth0               | 🔴 P0             | Middleware enforcement                                                                  |
| Identity        | Session Management  | JWT validation, refresh                                                               | Auth0               | 🔴 P0             | Middleware                                                                              |
| Revenue         | Billing             | Subscriptions, webhooks, refunds                                                      | Stripe              | 🔴 P0             | Billing service wrapper                                                                 |
| Revenue         | Coupons & Discounts | Promo codes                                                                           | Stripe              | 🟠 P1             | Billing wrapper                                                                         |
| Revenue         | Usage Metering Hook | Usage reporting                                                                       | Stripe Metered      | 🟠 P1             | Metering interface                                                                      |
| Access          | Entitlements        | Plan → feature mapping                                                                | Custom              | 🔴 P0             | Enforcement middleware                                                                  |
| Access          | Usage Limits        | Quotas + hard enforcement                                                             | Custom              | 🔴 P0             | Request interceptor                                                                     |
| Architecture    | Multi-Tenancy       | tenant_id isolation                                                                   | Custom DB           | 🔴 P0             | Query scoping + middleware                                                              |
| AI Governance   | Cost Tracking       | Token + cost per request                                                              | Custom              | 🔴 P0             | AI wrapper layer                                                                        |
| AI Governance   | Model Routing       | Model selection logic                                                                 | Custom              | 🔴 P0             | AI adapter                                                                              |
| AI Governance   | Budget Enforcement  | Stop at limit                                                                         | Custom              | 🔴 P0             | Guardrail middleware                                                                    |
| Communication   | Transactional Email | System-triggered emails                                                               | MailerLite          | 🟠 P1             | Email adapter                                                                           |
| Communication   | Marketing Email     | Campaigns + lists                                                                     | MailerLite          | 🟠 P1             | Email adapter                                                                           |
| Observability   | Error Tracking      | Runtime exceptions                                                                    | Sentry              | 🔴 P0             | Monitoring adapter                                                                      |
| Observability   | Uptime Monitoring   | Downtime alerts                                                                       | BetterUptime        | 🟠 P1             | External monitoring                                                                     |
| Data Governance | Backups & Recovery  | Automated snapshots + documented and tested restore procedure                         | Railway Auto-Backup | 🔴 P0             | Configure daily snapshots + define retention policy + document and test restore process |
| Admin           | Admin Dashboard     | User/billing/cost management                                                          | Custom React        | 🟠 P1             | Internal UI                                                                             |
| Financial Ops   | Expense Tracking    | Track AI, infra, Stripe fees, email, domain, and operational costs per tenant/product | Custom DB           | 🟠 P1             | Central cost logging table + cost attribution engine + P&L aggregation dashboard        |
| Config          | Capability Registry | Enable/disable modules                                                                | JSON registry       | 🔴 P0             | Central config loader                                                                   |

**Total P0 Capabilities:** 13  
**Total P1 Capabilities:** 7  
**Total Core Platform Capabilities:** 20

---

# 2️⃣ Extension Capabilities (Optional Modules)

These are modular and enabled per application.

| Domain      | Capability              | What It Covers             | Tool           | Platform Priority | Implementation Approach |
| ----------- | ----------------------- | -------------------------- | -------------- | ----------------- | ----------------------- |
| Marketplace | Listing CRUD            | Item creation & management | Custom API     | 🟠 P1             | Domain module           |
| Marketplace | Escrow & Split Payments | Revenue sharing            | Stripe Connect | 🟠 P1             | Billing extension       |
| Marketplace | Search & Filtering      | Discoverability            | MeiliSearch    | 🟠 P1             | Search service wrapper  |
| Marketplace | Purchase Delivery       | Grant buyer access         | Custom         | 🟠 P1             | Workflow module         |
| Social      | Reddit Posting          | Automated posting          | PRAW           | 🟡 P2             | Social adapter          |
| Social      | Twitter Posting         | Automated posting          | Tweepy         | 🟡 P2             | Social adapter          |
| Social      | Discord Posting         | Community messages         | Webhooks       | 🟡 P2             | Social adapter          |
| Content     | Content Automation      | AI templating + scheduling | Custom + AI    | 🟡 P2             | Content module          |
| Analytics   | Product Analytics       | Usage + funnels            | PostHog        | 🟡 P2             | Analytics adapter       |
| Analytics   | Revenue Dashboard       | MRR + cost metrics         | Custom         | 🟡 P2             | Reporting module        |
| Compliance  | Data Export             | User data export           | Custom API     | 🟡 P2             | GDPR module             |
| Compliance  | Account Deletion        | Data removal workflows     | Custom         | 🟡 P2             | GDPR module             |

**Total Extension Capabilities:** 12  
**Marketplace (P1):** 4  
**Social/Content/Analytics/Compliance (P2):** 8

---

# 3️⃣ Locked Tool Decisions

Unless cost or reliability forces change, these are fixed:

| Capability Area  | Tool                               | Justification                          |
| ---------------- | ---------------------------------- | -------------------------------------- |
| Authentication   | Auth0                              | Best free tier (7K users)              |
| Payments         | Stripe                             | Industry standard, best API            |
| Escrow           | Stripe Connect                     | Only real option for revenue splitting |
| Email            | MailerLite                         | Free 1K subs, already using            |
| Error Monitoring | Sentry                             | Free 5K errors/month, industry standard|
| Hosting          | Railway                            | $5/app, auto-deploy                    |
| Database         | Railway PostgreSQL                 | Included with hosting                  |
| Backups          | Railway Auto-Backup                | Built-in, free                         |
| CDN              | Cloudflare                         | Best free CDN                          |
| Search           | MeiliSearch                        | Free self-hosted, fast                 |
| Social APIs      | Official SDKs (PRAW, Tweepy, etc.) | Stable, well-documented                |

**Tool changes require explicit review and approval.**

---

# 4️⃣ Capability Priority Definitions

| Level   | Meaning                                        | When Required                    |
| ------- | ---------------------------------------------- | -------------------------------- |
| 🔴 P0   | Required for any production SaaS               | Before first customer            |
| 🟠 P1   | Required shortly after launch                  | Within 30 days of first customer |
| 🟡 P2   | Nice-to-have / growth stage                    | When scaling or expanding        |

**P0 = Non-negotiable. P1 = Soon. P2 = Later.**

---

# 5️⃣ Platform Implementation Rules

These rules govern how capabilities are implemented across the platform:

| # | Rule                                                | Rationale                                          |
|---|-----------------------------------------------------|----------------------------------------------------|
| 1 | Business logic must not directly call third-party APIs | Enables adapter swapping without business logic changes |
| 2 | Every capability must have a single adapter library | Prevents duplicate code, ensures consistency       |
| 3 | All AI calls must pass through AI Governance        | Cost control, budget enforcement, model routing    |
| 4 | All DB queries must be tenant-scoped               | Data isolation, prevents cross-tenant leaks        |
| 5 | Capabilities must be enabled via central configuration | Feature flags, per-tenant customization           |

**These rules are immutable. All implementations must comply.**

---

# 6️⃣ Implementation Status (Current)

Based on teebu-saas-platform codebase analysis:

## Already Built (✅)

| Capability | Implementation | Lines of Code |
|-----------|----------------|---------------|
| Authentication | auth0_lib.py | 750 lines |
| Billing | stripe_lib.py | 828 lines |
| Marketing Email | mailerlite_lib.py | 680 lines |
| Entitlements | entitlements.py + webhook_entitlements.py | ~400 lines |
| Social Posting | posting.py | ~300 lines |
| Git Operations | git_lib.py | 720 lines |
| Analytics | analytics_lib.py | 650 lines |

**Total Built:** 7 capabilities (~4,300 lines of reusable code)

## Partially Built (🔄)

| Capability | What Exists | What's Missing |
|-----------|-------------|----------------|
| Multi-Tenancy | Database schema supports it | tenant_id middleware not implemented |
| AI Cost Tracking | CSV logging (fo_run_log.csv) | Dashboard, attribution, enforcement |
| Capability Registry | business_config.json | Extension to support P0/P1/P2 toggles |

## Not Built (❌)

| Capability | Priority | Estimated Effort |
|-----------|----------|------------------|
| Role-Based Access | P0 | 2-3 hours (Auth0 roles exist) |
| Session Management | P0 | 2-3 hours (Auth0 JWT exists) |
| Usage Limits | P0 | 4-6 hours |
| AI Model Routing | P0 | 4-6 hours |
| AI Budget Enforcement | P0 | 4-6 hours |
| Error Tracking | P0 | 2-3 hours (Sentry integration) |
| Backups & Recovery | P0 | 2-3 hours (Railway config + docs) |
| Multi-Tenancy (full) | P0 | 8-10 hours |
| AI Cost Tracking (full) | P0 | 6-8 hours |
| Capability Registry (full) | P0 | 4-6 hours |

**Total P0 Gaps:** 10 capabilities, ~45-60 hours to complete kernel

---

# 7️⃣ Cost Model (Per Business)

Estimated monthly operational costs based on locked tools:

| Cost Category | Tool | Monthly Cost | Notes |
|--------------|------|--------------|-------|
| Hosting | Railway | $5-10 | Scales with usage |
| Database | Railway PostgreSQL | Included | Part of hosting |
| Auth | Auth0 | $0 | Free up to 7K users |
| Payments | Stripe | 2.9% + $0.30 | Per transaction only |
| Email | MailerLite | $0-9 | Free 1K subs, then $9/month |
| Error Tracking | Sentry | $0 | Free 5K errors/month |
| Uptime Monitor | BetterUptime | $0 | Free 3 monitors |
| CDN | Cloudflare | $0 | Free tier |
| Search | MeiliSearch | Included | Self-hosted on Railway |
| AI APIs | Claude/ChatGPT | Variable | $50-500/month per business |
| Domain | GoDaddy | $1-2 | Annual cost amortized |

**Total Fixed Costs:** ~$6-12/month per business  
**Total Variable Costs:** $50-500/month (AI usage)  
**Total Per Business:** ~$56-512/month

**For 25 businesses:** ~$1,400-$12,800/month total operating costs

---

# 8️⃣ Compliance & Validation

Before declaring any capability "done," it must pass:

## P0 Capability Checklist

- [ ] Adapter library implemented following Rule #2
- [ ] Unit tests written and passing
- [ ] Integration tests with real service (if applicable)
- [ ] Error handling and retries implemented
- [ ] Logging and observability hooks added
- [ ] Documentation written (usage guide)
- [ ] Configuration added to capability registry
- [ ] Tenant-scoping implemented (Rule #4, if applicable)
- [ ] Deployed to staging environment
- [ ] Validated in production with real tenant

## P0 Data Governance Specific (Backups)

- [ ] Railway auto-backup configured
- [ ] Retention policy defined (30 days recommended)
- [ ] Restore procedure documented step-by-step
- [ ] **Restore procedure tested successfully**
- [ ] RTO (Recovery Time Objective) measured
- [ ] RPO (Recovery Point Objective) measured
- [ ] Restore drill scheduled (quarterly)

## P1 Financial Ops Specific (Expense Tracking)

- [ ] Cost logging table created
- [ ] All cost categories instrumented:
  - [ ] AI API costs (Claude, ChatGPT)
  - [ ] Infrastructure costs (Railway)
  - [ ] Stripe transaction fees
  - [ ] Email costs (MailerLite)
  - [ ] Domain costs
- [ ] Cost attribution engine built (per tenant/product)
- [ ] P&L aggregation working
- [ ] Dashboard displaying MRR, costs, profit per business
- [ ] Export to CSV/Google Sheets for accounting

---

# 9️⃣ Change Management

## How to Modify This Spec

This is the **canonical platform definition**. Changes require:

1. **Proposal:** Document why a change is needed
2. **Impact Analysis:** What breaks if we make this change?
3. **Approval:** Explicit agreement from platform owner (Teebu)
4. **Version Bump:** Update version number and last updated date
5. **Migration Plan:** How do existing capabilities adapt?

## When Tool Changes Are Allowed

Tool changes from locked decisions require:

- [ ] Current tool has reliability/cost issues
- [ ] Alternative tool provides 10x improvement
- [ ] Migration path is documented
- [ ] Cost/benefit analysis completed
- [ ] Rollback plan exists

**Example:** Switching from Auth0 to Clerk would require proving Clerk is significantly better AND worth the migration effort.

---

# 🔟 Next Steps

Now that this spec is locked:

1. **Check into repo** as `PLATFORM_CAPABILITIES.md`
2. **Create implementation roadmap** based on product needs:
   - CD (CourtDominion) - which P0/P1 capabilities needed
   - AFH (AutoFounder Hub) - which P0/P1 + extensions needed
   - FO (FounderOps) - full P0 kernel + auto-provisioning
3. **Build P0 kernel** before launching any product to production
4. **Track progress** against P0 checklist
5. **Validate each capability** before marking complete

---

## Summary

**This document defines:**
- ✅ 20 core platform capabilities (13 P0, 7 P1)
- ✅ 12 optional extension capabilities
- ✅ 11 locked tool decisions
- ✅ 5 immutable implementation rules
- ✅ Clear validation criteria for completion
- ✅ Cost model and change management process

**This is the foundation. Build products on top of this.**

**Version:** 1.0 (Canonical)  
**Status:** Locked  
**Last Updated:** February 22, 2026
