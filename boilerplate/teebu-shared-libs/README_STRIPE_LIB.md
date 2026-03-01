# Stripe Library for AF/FO

Shared Stripe integration library for AF portfolio businesses and FO customer deployments.

**Version:** 1.0.0  
**Author:** Teebu  
**Date:** January 21, 2025

---

## Features

- ✅ Create subscription products and prices
- ✅ Generate payment links for easy checkout
- ✅ Handle and verify webhooks
- ✅ Cancel subscriptions (immediate or at period end)
- ✅ Comprehensive debug logging with configurable levels
- ✅ Config-driven for multi-account support (AF vs FO)
- ✅ Automatic retry with exponential backoff
- ✅ Idempotent operations
- ✅ Terminal-friendly output for solo operator debugging

---

## Installation

```bash
# Install Stripe Python library
pip install stripe --break-system-packages

# Copy library files to your project
cp stripe_lib.py /path/to/your/project/
cp af_stripe_config.json /path/to/your/project/  # Edit with your keys
```

---

## Quick Start

### 1. Configure Your Stripe Account

Edit `af_stripe_config.json` (or `fo_stripe_config.json`):

```json
{
  "stripe_secret_key": "sk_live_YOUR_KEY_HERE",
  "stripe_webhook_secret": "whsec_YOUR_WEBHOOK_SECRET",
  "account_name": "Teebu Ventures LLC (AF Portfolio)",
  "log_level": "INFO",
  "log_file": "stripe_operations.log"
}
```

### 2. Create Your First Product

```python
from stripe_lib import load_stripe_lib

# Load library
stripe = load_stripe_lib('af_stripe_config.json')

# Create complete subscription setup (product + prices + payment link)
result = stripe.create_complete_subscription_product(
    business_name="InboxTamer",
    monthly_price_dollars=49.00,
    annual_price_dollars=499.00,
    description="AI-powered email productivity tool",
    after_completion_url="https://inboxtamer.com/welcome"
)

if result["success"]:
    print(f"✓ Product ID: {result['product']['id']}")
    print(f"✓ Monthly payment link: {result['monthly_payment_link']}")
    print(f"✓ Annual payment link: {result['annual_payment_link']}")
else:
    print(f"✗ Errors: {result['errors']}")
```

**That's it!** You now have a Stripe product ready to accept payments.

---

## Configuration

### Config File Structure

```json
{
  "stripe_secret_key": "sk_live_xxx",           // Required: Stripe secret API key
  "stripe_webhook_secret": "whsec_xxx",         // Optional: For webhook verification
  "account_name": "Your Business Name",         // Optional: For logging
  "log_level": "INFO",                          // Optional: DEBUG | INFO | ERROR
  "log_file": "stripe_operations.log"           // Optional: Log file path
}
```

### Log Levels

| Level   | When to Use                          | What Gets Logged                                    |
|---------|--------------------------------------|-----------------------------------------------------|
| `ERROR` | Production (quiet)                   | Only failures                                       |
| `INFO`  | Normal operation (default)           | Operation start/completion, timing                  |
| `DEBUG` | Troubleshooting (verbose)            | Full requests, responses, retries, all details      |

### Changing Log Level

**Method 1: Edit config file (requires restart)**
```json
{
  "log_level": "DEBUG"
}
```

**Method 2: Environment variable (no restart for new processes)**
```bash
export STRIPE_LOG_LEVEL=DEBUG
python your_script.py

# Turn it back off
export STRIPE_LOG_LEVEL=INFO
```

---

## API Reference

### Core Methods

#### `create_subscription_product()`
Create a Stripe Product for subscriptions.

```python
result = stripe.create_subscription_product(
    business_name="InboxTamer",
    description="Email productivity tool",
    statement_descriptor="INBOXTAMER",  # Optional: appears on credit card
    metadata={"launch_date": "2025-01-25"}  # Optional: custom data
)
```

**Returns:**
```python
{
    "success": True,
    "data": {
        "id": "prod_xxx",
        "name": "InboxTamer",
        # ... full Stripe Product object
    },
    "attempt": 1,
    "elapsed_sec": 0.234
}
```

---

#### `create_price()`
Create a Price for a Product.

```python
result = stripe.create_price(
    product_id="prod_xxx",
    amount_cents=4900,  # $49.00
    currency="usd",
    interval="month",  # or "year"
    interval_count=1,
    metadata={"tier": "pro"}
)
```

---

#### `create_payment_link()`
Create a Payment Link for easy checkout.

```python
result = stripe.create_payment_link(
    price_id="price_xxx",
    quantity=1,
    after_completion_url="https://yoursite.com/welcome",
    metadata={"source": "website"}
)
```

**Returns:**
```python
{
    "success": True,
    "data": {
        "id": "plink_xxx",
        "url": "https://buy.stripe.com/xxx",  # Share this with customers
        # ... full PaymentLink object
    }
}
```

---

#### `create_complete_subscription_product()`
**Convenience method:** Create product + prices + payment links in one call.

```python
result = stripe.create_complete_subscription_product(
    business_name="InboxTamer",
    monthly_price_dollars=49.00,
    annual_price_dollars=499.00,  # Optional
    description="Email productivity tool",
    after_completion_url="https://inboxtamer.com/welcome"
)
```

**Returns:**
```python
{
    "success": True,
    "business_name": "InboxTamer",
    "product": { ... },  # Stripe Product object
    "monthly_price": { ... },
    "monthly_payment_link": "https://buy.stripe.com/monthly_xxx",
    "annual_price": { ... },
    "annual_payment_link": "https://buy.stripe.com/annual_xxx",
    "errors": []
}
```

---

#### `cancel_subscription()`
Cancel a customer's subscription.

```python
# Cancel at end of billing period (default)
result = stripe.cancel_subscription(
    subscription_id="sub_xxx",
    at_period_end=True
)

# Cancel immediately
result = stripe.cancel_subscription(
    subscription_id="sub_xxx",
    at_period_end=False
)
```

---

### Webhook Methods

#### `verify_webhook_signature()`
Verify incoming Stripe webhook is authentic.

```python
result = stripe.verify_webhook_signature(
    payload=request.body,  # Raw bytes
    signature_header=request.headers['Stripe-Signature']
)

if result["success"]:
    event = result["event"]
    # Process event
else:
    # Invalid signature - reject
    print(result["error"])
```

---

#### `handle_webhook_event()`
Route webhook event to appropriate handler function.

```python
def handle_subscription_created(event):
    subscription = event["data"]["object"]
    customer_id = subscription["customer"]
    # Send welcome email, enable access, etc
    return {"processed": True}

def handle_payment_failed(event):
    # Send dunning email, retry payment, etc
    return {"processed": True}

handlers = {
    "customer.subscription.created": handle_subscription_created,
    "invoice.payment_failed": handle_payment_failed,
}

result = stripe.handle_webhook_event(event, handlers)
```

---

## Usage Patterns

### Pattern 1: AF Portfolio Setup

```python
from stripe_lib import load_stripe_lib

# Load AF config
stripe = load_stripe_lib('af_stripe_config.json')

# Set up each business
businesses = [
    {"name": "InboxTamer", "price": 49.00},
    {"name": "LeadGenerator", "price": 29.00},
    {"name": "ContentScheduler", "price": 39.00},
]

for biz in businesses:
    result = stripe.create_complete_subscription_product(
        business_name=biz["name"],
        monthly_price_dollars=biz["price"]
    )
    
    if result["success"]:
        print(f"✓ {biz['name']}: {result['monthly_payment_link']}")
    else:
        print(f"✗ {biz['name']}: {result['errors']}")
```

---

### Pattern 2: FO Build Automation

```python
from stripe_lib import load_stripe_lib_from_dict

def fo_build_stripe_setup(business_name, monthly_price):
    """Called during FO automated build"""
    
    # Load FO config
    config = {
        "stripe_secret_key": "sk_live_FO_KEY",
        "account_name": "FounderOps LLC",
        "log_level": "DEBUG"  # Verbose during builds
    }
    
    stripe = load_stripe_lib_from_dict(config)
    
    # Create setup
    result = stripe.create_complete_subscription_product(
        business_name=business_name,
        monthly_price_dollars=monthly_price,
        description=f"Subscription for {business_name}"
    )
    
    # Save config for the business
    if result["success"]:
        import json
        config_data = {
            "product_id": result["product"]["id"],
            "payment_link": result["monthly_payment_link"]
        }
        
        with open(f"{business_name}_stripe.json", 'w') as f:
            json.dump(config_data, f, indent=2)
    
    return result
```

---

### Pattern 3: Webhook Endpoint (Flask Example)

```python
from flask import Flask, request
from stripe_lib import load_stripe_lib

app = Flask(__name__)
stripe = load_stripe_lib('af_stripe_config.json')

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    signature = request.headers.get('Stripe-Signature')
    
    # Verify signature
    verify_result = stripe.verify_webhook_signature(payload, signature)
    
    if not verify_result["success"]:
        return {"error": "Invalid signature"}, 400
    
    event = verify_result["event"]
    
    # Define handlers
    def handle_subscription_created(event):
        # Your logic here
        return {"status": "processed"}
    
    handlers = {
        "customer.subscription.created": handle_subscription_created,
    }
    
    # Route event
    handle_result = stripe.handle_webhook_event(event, handlers)
    
    return {"received": True}, 200
```

---

## Error Handling

All methods return a dict with `success` field:

```python
result = stripe.create_subscription_product(...)

if not result["success"]:
    # Handle error
    print(f"Error: {result['error']}")
    print(f"Stripe error code: {result.get('stripe_error_code')}")
    print(f"HTTP status: {result.get('http_status')}")
    print(f"Request ID: {result.get('request_id')}")
    print(f"Attempts: {result.get('attempts')}")
    
    # Access full error details (DEBUG mode)
    if 'full_error' in result:
        print(result['full_error'])
else:
    # Success
    data = result["data"]
    print(f"Created: {data['id']}")
```

### Automatic Retry

All operations retry automatically on failure:
- **Retry attempts:** 3
- **Backoff:** Exponential (1s, 2s, 4s)
- **Logs:** All attempts logged for debugging

---

## Debugging

### Enable Verbose Logging

```bash
# Terminal session
export STRIPE_LOG_LEVEL=DEBUG
python your_script.py
```

**What you'll see:**
```
2025-01-21 10:23:45 [STRIPE-LIB] INFO - StripeLib initialized | {"account": "Teebu Ventures LLC", "log_level": "DEBUG"}
2025-01-21 10:23:45 [STRIPE-LIB] INFO - Creating subscription product: InboxTamer
2025-01-21 10:23:45 [STRIPE-LIB] DEBUG - CREATE_PRODUCT[InboxTamer] - Attempt 1/3 | {"kwargs": {"name": "InboxTamer", ...}}
2025-01-21 10:23:46 [STRIPE-LIB] INFO - CREATE_PRODUCT[InboxTamer] - SUCCESS | {"attempt": 1, "elapsed_sec": 0.234}
2025-01-21 10:23:46 [STRIPE-LIB] DEBUG - CREATE_PRODUCT[InboxTamer] - Full response | {"response": {"id": "prod_xxx", ...}}
```

### Log File

All operations also log to `stripe_operations.log` (configurable):

```bash
# Watch logs in real-time
tail -f stripe_operations.log

# Grep for errors
grep ERROR stripe_operations.log

# Grep for specific business
grep InboxTamer stripe_operations.log
```

---

## Multiple Accounts (AF vs FO)

Use separate config files for different Stripe accounts:

```python
# AF Portfolio operations
af_stripe = load_stripe_lib('af_stripe_config.json')
af_stripe.create_subscription_product(...)

# FO Customer operations
fo_stripe = load_stripe_lib('fo_stripe_config.json')
fo_stripe.create_subscription_product(...)
```

**Both can run in same process** - just load different configs.

---

## Integration with FO Build System

Add to your FO build script:

```python
# fo_build.sh calls this Python function

def setup_stripe_for_business(business_name, monthly_price):
    """Called during FO automated deployment"""
    
    from stripe_lib import load_stripe_lib
    
    stripe = load_stripe_lib('fo_stripe_config.json')
    
    result = stripe.create_complete_subscription_product(
        business_name=business_name,
        monthly_price_dollars=monthly_price,
        description=f"Subscription for {business_name}",
        after_completion_url=f"https://{business_name.lower()}.com/welcome"
    )
    
    if not result["success"]:
        raise Exception(f"Stripe setup failed: {result['errors']}")
    
    # Return config for deployment
    return {
        "product_id": result["product"]["id"],
        "payment_link": result["monthly_payment_link"]
    }
```

---

## Testing

### Test Mode

Stripe provides test mode for development:

```json
{
  "stripe_secret_key": "sk_test_YOUR_TEST_KEY",
  "log_level": "DEBUG"
}
```

**Test mode features:**
- No real charges
- Use test card numbers: `4242 4242 4242 4242`
- Separate from production data
- Full Stripe API access

### Integration Test Example

```python
from stripe_lib import load_stripe_lib

def test_create_product():
    stripe = load_stripe_lib('test_config.json')
    
    result = stripe.create_subscription_product(
        business_name="TestBusiness",
        description="Test product"
    )
    
    assert result["success"], f"Failed: {result.get('error')}"
    assert result["data"]["id"].startswith("prod_")
    
    print("✓ Test passed")

if __name__ == "__main__":
    test_create_product()
```

---

## FAQ

### Q: Do I need a separate Stripe account for each AF business?

**A:** No. Use one Stripe account with multiple Products. See "Multiple Accounts" section.

### Q: How do I change log level without restarting?

**A:** You can't (library loads config once). But it's a 2-second restart. For 5 years from now: `export STRIPE_LOG_LEVEL=DEBUG` then restart your script.

### Q: What if a Stripe operation fails after 3 retries?

**A:** It returns `{"success": False, ...}` with full error details. Check logs for debugging info.

### Q: Can I use this library in FO and AF simultaneously?

**A:** Yes. Load different configs for each account. They don't interfere.

### Q: Where are my API keys?

**A:** Stripe Dashboard → Developers → API keys. Use **Secret key** (starts with `sk_`).

### Q: How do I get webhook secret?

**A:** Stripe Dashboard → Developers → Webhooks → Add endpoint → Copy signing secret (starts with `whsec_`).

---

## Security Notes

- ✅ **Never commit API keys to Git** - add config files to `.gitignore`
- ✅ Use environment variables for production secrets
- ✅ Rotate keys if compromised
- ✅ Use Stripe's test mode for development
- ✅ Webhook signatures prevent replay attacks

---

## Support

For issues or questions:
1. Check logs: `tail -f stripe_operations.log`
2. Enable DEBUG mode: `export STRIPE_LOG_LEVEL=DEBUG`
3. Review examples: `stripe_lib_examples.py`
4. Stripe docs: https://stripe.com/docs/api

---

## License

Proprietary - Teebu (AF/FO systems)

---

## Changelog

### v1.0.0 (2025-01-21)
- Initial release
- Support for product/price creation
- Payment link generation
- Webhook handling
- Subscription cancellation
- Configurable logging
- Multi-account support

---

**Built for solo operators who need deterministic, debuggable systems.**

*Remember: You're not old, fat, and dumb. You're experienced, pragmatic, and wise enough to build systems that work.*
