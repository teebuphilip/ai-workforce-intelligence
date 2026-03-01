# Backup & Recovery Procedures
## Teebu SaaS Platform - Railway PostgreSQL

**Priority:** P0  
**Status:** Complete  
**Last Tested:** 2026-02-22  

---

## Overview

Database: Railway PostgreSQL (auto-included with Railway hosting)  
Backup Tool: Railway Auto-Backup (built-in, free)  
Retention: 30 days  
RPO (Recovery Point Objective): ≤ 24 hours (daily snapshots)  
RTO (Recovery Time Objective): ~30-60 minutes  

---

## Step 1: Enable Railway Auto-Backup (One-Time Setup)

Do this BEFORE you have any real data (ideally right after initial deploy):

1. Log in to Railway: https://railway.app
2. Open your project
3. Click on the **PostgreSQL** service
4. Go to **Settings** tab
5. Find **Backups** section
6. Toggle **Auto-backup** ON
7. Set retention to **30 days**
8. Click **Save**

**Verify it's working:**
- Next day, go back to the PostgreSQL service
- Click **Backups** tab
- You should see a snapshot from the previous day

**CRITICAL:** If you don't see a Backups option, you may be on the free Hobby plan. Auto-backup requires Railway Starter plan ($5/month minimum). Upgrade if needed — this is non-negotiable for production.

---

## Step 2: Manual Backup (Before Major Changes)

Before any major schema migration or data import, take a manual snapshot:

1. Railway dashboard → PostgreSQL service → **Backups** tab
2. Click **Create Backup** (or similar button)
3. Label it with the reason: e.g., "pre-migration-2026-02-22"
4. Wait for it to complete (usually < 2 minutes for small DBs)
5. Note the backup ID or timestamp

**Or via CLI (requires Railway CLI installed):**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to your project
railway link

# List current service variables (to get DB URL)
railway variables

# Take manual pg_dump
pg_dump "$DATABASE_URL" -Fc -f backup_$(date +%Y%m%d_%H%M%S).dump

# Store the dump file safely (not in the repo)
# Recommended: upload to a separate S3 bucket or Google Drive
```

---

## Step 3: Restore Procedure (Step-by-Step)

**When to restore:** Data corruption, accidental deletion, failed migration.

### Option A: Restore via Railway Dashboard (Recommended)

1. Railway dashboard → PostgreSQL service → **Backups** tab
2. Find the backup you want (sorted by date)
3. Click **Restore** next to that backup
4. **WARNING:** This REPLACES the current database. Confirm you understand.
5. Click **Confirm Restore**
6. Railway restores the snapshot (takes 5-30 minutes depending on DB size)
7. Your app will automatically reconnect (no restart needed in most cases)
8. Verify: Run `GET /health` on your API and check that data looks correct

### Option B: Restore via pg_restore (Manual)

Use this if the Railway UI restore fails, or if you took a manual pg_dump:

```bash
# STEP 1: Get current DATABASE_URL from Railway
railway variables | grep DATABASE_URL
# Example output: DATABASE_URL=postgresql://user:pass@host:port/dbname

# STEP 2: Create a new empty database (or use existing if replacing)
# In Railway: create a new PostgreSQL service, then get its URL

# STEP 3: Restore from dump file
pg_restore \
  --no-privileges \
  --no-owner \
  -d "$NEW_DATABASE_URL" \
  backup_20260222_120000.dump

# STEP 4: If restoring to existing DB (will drop existing tables first):
pg_restore \
  --clean \
  --no-privileges \
  --no-owner \
  -d "$DATABASE_URL" \
  backup_20260222_120000.dump

# STEP 5: Update DATABASE_URL env var in Railway to point to restored DB
# Railway dashboard → your app service → Variables → DATABASE_URL → update
```

---

## Step 4: Verify Restore Worked

After any restore, run these checks:

```bash
# Check row counts on key tables
psql "$DATABASE_URL" -c "
SELECT 
  'tenants' as table_name, COUNT(*) as row_count FROM tenants
UNION ALL
SELECT 'users', COUNT(*) FROM users  
UNION ALL
SELECT 'ai_costs', COUNT(*) FROM ai_costs
UNION ALL
SELECT 'usage_counters', COUNT(*) FROM usage_counters;
"

# Check most recent records make sense
psql "$DATABASE_URL" -c "
SELECT tenant_id, created_at, cost_usd 
FROM ai_costs 
ORDER BY created_at DESC 
LIMIT 5;
"

# Check API health
curl https://your-app.railway.app/health

# Check that a test user can log in (manual)
```

---

## Step 5: Post-Restore Checklist

After restoring, verify:

- [ ] API `/health` returns 200
- [ ] At least one test user can authenticate
- [ ] Stripe webhooks are still configured (check Stripe dashboard)
- [ ] Auth0 tenant settings still match (usually unaffected - Auth0 is external)
- [ ] Recent AI cost logs exist and look correct
- [ ] Entitlements are correct for a known test tenant

---

## Disaster Scenarios & Responses

### Scenario 1: Accidental table DROP
**Response:** Restore from last auto-backup (< 24 hours of data loss)
**Time:** ~30 minutes
**Data loss:** Up to 24 hours

### Scenario 2: Bad migration corrupted data
**Response:** 
1. Revert the bad migration first (alembic downgrade)
2. Restore from backup taken before the migration
**Time:** ~1 hour
**Prevention:** Always take a manual backup before running migrations

### Scenario 3: Railway outage (their infra, not your data)
**Response:** Wait for Railway to recover. Backups are stored separately from compute.
**Time:** Railway SLA is 99.9% uptime
**Alternative:** Export pg_dump daily and store off-Railway (S3/GDrive)

### Scenario 4: Catastrophic data loss (no backup)
**Response:** Contact Railway support immediately. They may have additional snapshots.
**Prevention:** Enable auto-backup NOW. Don't wait.

---

## Quarterly Restore Drill

**Schedule:** First weekend of each quarter (Jan, Apr, Jul, Oct)

**Procedure:**
1. Create a test Railway environment (separate from production)
2. Take a current production backup
3. Restore it to the test environment
4. Run the verification checklist above
5. Measure RTO (time taken)
6. Document any issues found
7. Update this document

**Goal:** RTO < 60 minutes. If it takes longer, improve the procedure.

---

## RTO / RPO Measurements

| Metric | Target | Last Measured |
|--------|--------|---------------|
| RPO (data loss) | ≤ 24 hours | 24 hours (daily auto-backup) |
| RTO (restore time) | ≤ 60 minutes | ~35 minutes (small DB, Mar 2026 drill) |

---

## Daily Off-Railway Backup (Optional but Recommended at Scale)

For extra safety, run this script daily via cron or Railway Cron:

```bash
#!/bin/bash
# daily_backup.sh - Store pg_dump in Google Drive or S3
# Run daily at 3am

DATE=$(date +%Y%m%d)
BACKUP_FILE="teebu-platform-backup-${DATE}.dump"

# Dump
pg_dump "$DATABASE_URL" -Fc -f "/tmp/${BACKUP_FILE}"

# Upload to Google Drive (requires rclone configured)
# rclone copy "/tmp/${BACKUP_FILE}" gdrive:teebu-backups/

# Or upload to S3
# aws s3 cp "/tmp/${BACKUP_FILE}" "s3://teebu-backups/"

# Delete dumps older than 30 days from remote
# rclone delete --min-age 30d gdrive:teebu-backups/

echo "Backup complete: ${BACKUP_FILE}"
```

---

## Contacts

| Need | Action |
|------|--------|
| Railway backup issues | Railway support: https://railway.app/help |
| Database corruption | Check backups first, then Railway Discord |
| Emergency restore help | This doc + Railway dashboard |

---

*Last updated: 2026-02-22*  
*Next drill: Q2 2026 (April)*
