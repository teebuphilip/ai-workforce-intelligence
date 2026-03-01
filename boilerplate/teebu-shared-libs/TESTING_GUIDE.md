# Testing Guide for AF/FO Libraries

Complete guide for testing the Stripe, MailerLite, and Auth0 libraries.

---

## Overview

Three test suites validate all library functionality:

1. **test_stripe_lib.py** - Payment processing tests
2. **test_mailerlite_lib.py** - Email marketing tests  
3. **test_auth0_lib.py** - Authentication tests

Plus:
- **run_all_tests.py** - Master test runner

---

## Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### 2. Get API Credentials

**Stripe:**
- Go to https://dashboard.stripe.com/test/apikeys
- Copy **Secret key** (starts with `sk_test_`)
- Use TEST MODE keys (not live keys)

**MailerLite:**
- Go to https://dashboard.mailerlite.com/integrations/api
- Generate new API key
- Copy the key

**Auth0:**
- Go to https://manage.auth0.com/dashboard
- Create **Machine to Machine Application**:
  1. Applications → Create Application
  2. Select "Machine to Machine Applications"
  3. Authorize for **Auth0 Management API**
  4. Grant scopes:
     - `read:users`
     - `create:users`
     - `update:users`
     - `delete:users`
     - `read:roles`
     - `create:roles`
     - `update:roles`
  5. Copy **Domain**, **Client ID**, **Client Secret**

---

## Configuration

### Edit Test Files

**test_stripe_lib.py:**
```python
TEST_CONFIG = {
    "stripe_secret_key": "sk_test_YOUR_KEY_HERE",
    ...
}
```

**test_mailerlite_lib.py:**
```python
TEST_CONFIG = {
    "mailerlite_api_key": "YOUR_KEY_HERE",
    ...
}
```

**test_auth0_lib.py:**
```python
TEST_CONFIG = {
    "auth0_domain": "your-tenant.auth0.com",
    "auth0_client_id": "YOUR_CLIENT_ID",
    "auth0_client_secret": "YOUR_CLIENT_SECRET",
    ...
}
```

---

## Running Tests

### Option 1: Run All Tests

```bash
python run_all_tests.py
```

This runs all three test suites sequentially and shows a summary.

### Option 2: Run Individual Tests

```bash
# Run only Stripe tests
python run_all_tests.py stripe

# Run only MailerLite tests
python run_all_tests.py mailerlite

# Run only Auth0 tests
python run_all_tests.py auth0
```

### Option 3: Run Test Files Directly

```bash
python test_stripe_lib.py
python test_mailerlite_lib.py
python test_auth0_lib.py
```

---

## What Each Test Suite Does

### Stripe Tests

**Creates:**
- Test products
- Test prices (monthly/annual)
- Payment links

**Tests:**
- Product creation
- Price creation
- Payment link generation
- Complete subscription setup (convenience method)
- Error handling

**Cleanup:**
- Products remain in Stripe dashboard (test mode)
- Safe to leave or delete manually

**Time:** ~30 seconds

---

### MailerLite Tests

**Creates:**
- Test groups
- Test subscribers
- Welcome automation setup

**Tests:**
- Subscriber management (add, get, update, unsubscribe)
- Group operations (create, list, delete)
- List campaigns and automations
- Custom fields
- Welcome automation setup (convenience method)
- Error handling

**Cleanup:**
- Automatically deletes test subscribers
- Automatically deletes test groups
- Clean slate after tests

**Time:** ~45 seconds

---

### Auth0 Tests

**Creates:**
- Test users
- Test roles
- Basic auth structure (user/admin/premium roles)

**Tests:**
- User management (create, get, update, delete, search)
- Authentication token management
- Password operations (change, reset email)
- Email verification
- Role operations (create, list, assign)
- User role assignments
- User blocking
- Basic auth setup (convenience method)
- Error handling

**Cleanup:**
- Automatically deletes test users
- Test roles remain (delete manually via dashboard)

**Time:** ~60 seconds

---

## Expected Output

### Successful Test Run

```
============================================================
TEST: Config Loading
============================================================

✓ Config loaded: StripeConfig(account=Test Account, log_level=DEBUG)
✓ Config fields validated

============================================================
TEST: Library Initialization
============================================================

✓ StripeLib initialized
✓ Library config accessible

...

============================================================
ALL TESTS PASSED ✓
============================================================

Stripe library is working correctly!
```

### Failed Test Run

```
============================================================
TEST: Create Product
============================================================

✗ Create product failed
Error: Invalid API key provided
Status: 401

TEST SUITE FAILED ✗
```

---

## Troubleshooting

### Issue: "Invalid API key"

**Solution:**
- Verify API key is correct
- For Stripe: Use TEST mode key (sk_test_...)
- For Auth0: Verify client ID and secret match
- Check for extra spaces when copying keys

### Issue: "Permission denied" (Auth0)

**Solution:**
- Verify M2M application has correct scopes
- Required scopes:
  - read:users, create:users, update:users, delete:users
  - read:roles, create:roles, update:roles
- Re-authorize application if needed

### Issue: "Rate limit exceeded"

**Solution:**
- Wait 60 seconds
- Tests include retry logic
- API providers have rate limits

### Issue: "Test data not cleaned up"

**Solution:**
- MailerLite: Re-run tests (cleanup runs at end)
- Stripe: Delete products manually in test dashboard
- Auth0: Delete roles manually in dashboard

### Issue: Tests fail partway through

**Solution:**
- Check error message for specific failure
- Enable DEBUG logging (already enabled in tests)
- Review full stack trace
- Some cleanup may not run - delete test data manually

---

## Test Data Management

### What Gets Created

**Stripe (Test Mode):**
- Products: "TestBusiness", "TestComplete"
- Prices: Various test amounts
- Payment links: Generated URLs

**MailerLite:**
- Groups: "Test Group - Delete Me", "TestBusiness Welcome"
- Subscribers: test+mailerlite@example.com
- Custom fields: (if any created)

**Auth0:**
- Users: test+auth0_[timestamp]@example.com
- Roles: TestRole_[timestamp], TestBusiness_user/admin/premium

### Automatic Cleanup

✓ MailerLite subscribers - deleted automatically  
✓ MailerLite groups - deleted automatically  
✓ Auth0 users - deleted automatically  
✗ Stripe products - remain in test dashboard  
✗ Auth0 roles - remain in dashboard

### Manual Cleanup

**Stripe:**
1. Go to https://dashboard.stripe.com/test/products
2. Delete test products if desired
3. Or leave them (test mode, no harm)

**Auth0:**
1. Go to Auth0 Dashboard → User Management → Roles
2. Find TestRole_* and TestBusiness_* roles
3. Delete if desired

---

## Integration Testing

After library tests pass, test integration:

### Test 1: Complete Business Setup

```python
from stripe_lib import load_stripe_lib
from mailerlite_lib import load_mailerlite_lib
from auth0_lib import load_auth0_lib

def test_complete_business_setup():
    # Load libraries
    stripe = load_stripe_lib('af_stripe_config.json')
    mailer = load_mailerlite_lib('af_mailerlite_config.json')
    auth = load_auth0_lib('af_auth0_config.json')
    
    # Set up payment
    stripe_result = stripe.create_complete_subscription_product(
        business_name="IntegrationTest",
        monthly_price_dollars=49.00
    )
    assert stripe_result["success"]
    
    # Set up email
    mailer_result = mailer.setup_welcome_automation(
        business_name="IntegrationTest"
    )
    assert mailer_result["success"]
    
    # Set up auth
    auth_result = auth.setup_basic_auth(
        business_name="IntegrationTest"
    )
    assert auth_result["success"]
    
    print("✓ Complete business setup successful!")
    
    return {
        "payment_link": stripe_result["monthly_payment_link"],
        "group_id": mailer_result["group"]["id"],
        "roles": auth_result["roles"]
    }

# Run test
result = test_complete_business_setup()
print(f"Payment link: {result['payment_link']}")
```

### Test 2: User Signup Flow

```python
def test_user_signup_flow():
    auth = load_auth0_lib('af_auth0_config.json')
    mailer = load_mailerlite_lib('af_mailerlite_config.json')
    
    # 1. Create user in Auth0
    user_result = auth.create_user(
        email="testuser@example.com",
        password="TestPassword123!"
    )
    assert user_result["success"]
    user_id = user_result["data"]["user_id"]
    
    # 2. Add to email list
    sub_result = mailer.add_subscriber(
        email="testuser@example.com",
        fields={"name": "Test User"}
    )
    assert sub_result["success"]
    
    # 3. Assign role
    role_result = auth.assign_roles_to_user(
        user_id=user_id,
        role_ids=["rol_xxxxx"]  # Your role ID
    )
    
    print("✓ User signup flow successful!")
    
    # Cleanup
    auth.delete_user(user_id)
    mailer.delete_subscriber(sub_result["data"]["data"]["id"])

# Run test
test_user_signup_flow()
```

---

## Performance Benchmarks

Expected test execution times:

| Test Suite  | Operations | Time      |
|-------------|-----------|-----------|
| Stripe      | 7         | ~30 sec   |
| MailerLite  | 15        | ~45 sec   |
| Auth0       | 19        | ~60 sec   |
| **Total**   | **41**    | **~2 min**|

---

## Continuous Integration

To run tests in CI/CD:

```yaml
# .github/workflows/test.yml
name: Library Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        env:
          STRIPE_TEST_KEY: ${{ secrets.STRIPE_TEST_KEY }}
          MAILERLITE_API_KEY: ${{ secrets.MAILERLITE_API_KEY }}
          AUTH0_DOMAIN: ${{ secrets.AUTH0_DOMAIN }}
          AUTH0_CLIENT_ID: ${{ secrets.AUTH0_CLIENT_ID }}
          AUTH0_CLIENT_SECRET: ${{ secrets.AUTH0_CLIENT_SECRET }}
        run: python run_all_tests.py
```

Store secrets in GitHub repo settings.

---

## Test Coverage

What's tested:

✓ Config loading  
✓ Library initialization  
✓ API authentication  
✓ Create operations  
✓ Read operations  
✓ Update operations  
✓ Delete operations  
✓ List/search operations  
✓ Error handling  
✓ Convenience methods  
✓ Retry logic (on failures)  
✓ Token caching (Auth0)  

What's NOT tested:

✗ Webhook payload verification (requires external calls)  
✗ Email delivery (requires email provider)  
✗ Payment processing (requires real cards)  
✗ Rate limiting edge cases  
✗ Concurrent operations  

---

## Next Steps After Tests Pass

1. **Review dashboards:**
   - Stripe: Check test products
   - MailerLite: Verify no leftover test data
   - Auth0: Review test roles

2. **Integrate into build:**
   - Add libraries to your FO build script
   - Test with one AF business
   - Validate end-to-end flow

3. **Set up monitoring:**
   - Log library operations
   - Track API errors
   - Monitor rate limits

4. **Production config:**
   - Switch to production API keys
   - Update log levels (INFO for production)
   - Enable log files

---

## FAQ

**Q: Can I run tests multiple times?**  
A: Yes. MailerLite and Auth0 tests clean up automatically. Stripe products accumulate (harmless in test mode).

**Q: Will tests charge my accounts?**  
A: No. Stripe tests use test mode. MailerLite and Auth0 are in free tiers typically.

**Q: How do I test webhooks?**  
A: Webhooks require public URLs. Use ngrok or deploy to test server. Webhook verification is in library but not tested by test suite.

**Q: Tests failed - is data still created?**  
A: Possibly. Check dashboards and delete test data manually if needed.

**Q: Can I modify test data?**  
A: Yes. Edit TEST_EMAIL, TEST_GROUP_NAME, etc. in test files.

**Q: How often should I run tests?**  
A: After any library changes, before deployments, or when APIs update.

---

## Support

If tests fail consistently:

1. Enable DEBUG logging (already enabled)
2. Check API status pages:
   - https://status.stripe.com
   - https://status.mailerlite.com  
   - https://status.auth0.com
3. Verify API credentials
4. Check rate limits
5. Review error messages carefully

---

**Ready to test?**

```bash
python run_all_tests.py
```

Good luck! 🚀
