# Google Analytics 4 Setup Guide

Quick guide to set up GA4 for use with analytics_lib.py

---

## Step 1: Create GA4 Property

1. Go to https://analytics.google.com
2. Click **Admin** (bottom left gear icon)
3. Click **Create Property**
4. Enter property details:
   - Property name: "InboxTamer" (or your business name)
   - Timezone: Your timezone
   - Currency: USD
5. Click **Next**
6. Fill in business details (optional)
7. Click **Create**

---

## Step 2: Create Data Stream

1. After creating property, you'll see "Set up a data stream"
2. Click **Web** (for website tracking)
3. Enter details:
   - Website URL: https://inboxtamer.com
   - Stream name: "InboxTamer Web"
4. Click **Create stream**

**Save these values:**
- **Measurement ID:** G-XXXXXXXXXX (starts with G-)
- Keep this page open for Step 3

---

## Step 3: Get API Secret

1. On the stream details page, scroll down
2. Find **Measurement Protocol API secrets**
3. Click **Create**
4. Enter:
   - Nickname: "Backend Server"
5. Click **Create**

**Save this value:**
- **Secret value:** (long string, copy immediately - shown only once)

---

## Step 4: Configure analytics_lib

Edit your config file:

```json
{
  "ga4_measurement_id": "G-XXXXXXXXXX",
  "ga4_api_secret": "your_secret_here",
  "account_name": "InboxTamer",
  "log_level": "INFO",
  "log_file": "analytics_operations.log",
  "debug_mode": false
}
```

---

## Step 5: Add Frontend Tracking (Optional)

For client-side tracking (page views, button clicks), add to your HTML:

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

Replace `G-XXXXXXXXXX` with your Measurement ID.

---

## Step 6: Test Events

### Enable Debug Mode

Edit config:
```json
{
  "debug_mode": true
}
```

### Send Test Event

```python
from analytics_lib import load_analytics_lib

analytics = load_analytics_lib('analytics_config.json')

result = analytics.track_event(
    event_name="test_event",
    event_params={"test": "true"}
)

print(result)
```

### View in DebugView

1. Go to GA4 Admin
2. Click **DebugView** (left sidebar)
3. You should see events appear in real-time

**Note:** Standard reports take 24-48 hours to populate.

---

## What to Track

### Essential Events (All Businesses)

```python
# Page views
analytics.track_page_view("/pricing", "Pricing")

# User signup
analytics.track_signup(
    user_id="user_12345",
    signup_method="email"
)

# User login
analytics.track_login(
    user_id="user_12345",
    login_method="email"
)

# Purchase
analytics.track_purchase(
    transaction_id="ch_12345",
    value=49.00,
    items=[{
        "item_id": "monthly",
        "item_name": "Monthly Plan",
        "price": 49.00
    }]
)
```

### Subscription Events

```python
# Subscription start
analytics.track_subscription_start(
    subscription_id="sub_12345",
    plan_name="Monthly Pro",
    value=49.00
)

# Subscription cancel
analytics.track_subscription_cancel(
    subscription_id="sub_12345",
    plan_name="Monthly Pro",
    reason="Too expensive"
)
```

### Custom Business Events

```python
# Feature usage
analytics.track_event(
    event_name="feature_used",
    user_id="user_12345",
    event_params={
        "feature": "export_data",
        "format": "csv"
    }
)

# Button clicks
analytics.track_event(
    event_name="button_click",
    event_params={
        "button_name": "cta_signup",
        "page": "/home"
    }
)
```

---

## Integration with Stripe Webhooks

Automatic tracking from Stripe events:

```python
from analytics_lib import load_analytics_lib

analytics = load_analytics_lib('analytics_config.json')

@app.post("/stripe-webhook")
async def stripe_webhook(request):
    event = stripe.Webhook.construct_event(...)
    
    # Automatically track purchase/subscription events
    analytics.track_stripe_webhook(
        event_type=event["type"],
        stripe_event=event
    )
    
    return {"success": True}
```

Supported Stripe events:
- `charge.succeeded` → Tracked as purchase
- `customer.subscription.created` → Tracked as subscription_start
- `customer.subscription.deleted` → Tracked as subscription_cancel

---

## Key Metrics to Monitor

### Acquisition
- Signups (by source)
- Conversion rate (visitor → signup)

### Activation
- First purchase (signup → paid)
- Time to purchase

### Revenue
- MRR (Monthly Recurring Revenue)
- LTV (Lifetime Value)
- ARPU (Average Revenue Per User)

### Retention
- Churn rate
- Active users (DAU/WAU/MAU)

### Referral
- Shares
- Invites sent

---

## Reports to Create

### 1. Conversion Funnel

Events to track:
1. page_view (/pricing)
2. begin_checkout
3. purchase

### 2. User Journey

From signup to first purchase:
1. sign_up
2. login (engagement)
3. feature_used (activation)
4. purchase

### 3. Revenue Dashboard

- Total revenue (purchase events)
- Subscriptions started
- Subscriptions cancelled
- Net MRR

---

## Troubleshooting

### Events not showing in DebugView

✓ Check `debug_mode: true` in config
✓ Verify Measurement ID is correct
✓ Check API secret is valid
✓ Look at library logs (enable DEBUG)

### Events in DebugView but not reports

✓ Standard reports take 24-48 hours
✓ Check date range in reports
✓ Some reports need minimum data

### "Invalid measurement ID" error

✓ Measurement ID must start with G-
✓ Copy from Data Streams, not property ID
✓ Check for extra spaces

### "Invalid API secret" error

✓ Create new secret in Measurement Protocol settings
✓ Copy immediately (shown only once)
✓ Each property needs separate secret

---

## Privacy & GDPR

GA4 is designed for privacy compliance:

✓ IP anonymization (automatic)
✓ No cross-site tracking
✓ User deletion (via GA4 UI)
✓ Consent mode support

**Recommended:**
- Add cookie consent banner
- Include GA4 in privacy policy
- Honor user opt-outs

---

## Cost

**FREE** for:
- Up to 10 million events/month
- Standard reports
- Data retention (14 months)

**GA4 360** (paid):
- Higher limits
- Advanced features
- SLA support

**You won't need paid tier.**

---

## Quick Reference

### Config File
```json
{
  "ga4_measurement_id": "G-XXXXXXXXXX",
  "ga4_api_secret": "your_secret",
  "account_name": "Business Name",
  "log_level": "INFO",
  "debug_mode": false
}
```

### Load Library
```python
from analytics_lib import load_analytics_lib
analytics = load_analytics_lib('analytics_config.json')
```

### Track Event
```python
analytics.track_event("event_name", user_id="123")
```

### Enable Debug Logging
```bash
export ANALYTICS_LOG_LEVEL=DEBUG
```

---

**Ready to track? Set up GA4 property, get credentials, configure library, start tracking.**
