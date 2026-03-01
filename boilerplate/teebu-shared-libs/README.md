# AF/FO Shared Libraries

**Production-ready Python libraries for automating SaaS business deployments.**

Built for solo operators who need deterministic, debuggable systems.

---

## Overview

Four integrated libraries that eliminate deployment bottlenecks for the AutoFounder (AF) portfolio and FounderOps (FO) build system:

| Library | Purpose | Key Features |
|---------|---------|--------------|
| **stripe_lib** | Payment processing | Subscriptions, payment links, webhooks |
| **mailerlite_lib** | Email marketing | Subscribers, campaigns, automation |
| **auth0_lib** | Authentication | Users, roles, password flows |
| **git_lib** | Version control | Repos, commits, branches, remotes |

**Time Savings:** 37-62 hours per 25 business deployments

---

## Quick Start

### 1. Install

```bash
# Clone repository
git clone https://github.com/teebu/teebu-shared-libs.git
cd teebu-shared-libs

# Install dependencies
pip install -r requirements.txt --break-system-packages

# Verify git is installed
git --version
```

### 2. Configure

Edit config files with your API credentials:

```bash
# AF Portfolio configs
af_stripe_config.json       # Stripe API key
af_mailerlite_config.json   # MailerLite API key
af_auth0_config.json        # Auth0 credentials
af_git_config.json          # GitHub/GitLab token

# FO Customer configs
fo_stripe_config.json
fo_mailerlite_config.json
fo_auth0_config.json
fo_git_config.json
```

### 3. Test

```bash
# Run all tests
python run_all_tests.py

# Or test individually
python run_all_tests.py stripe
python run_all_tests.py mailerlite
python run_all_tests.py auth0
python run_all_tests.py git
```

### 4. Use

```python
from stripe_lib import load_stripe_lib
from mailerlite_lib import load_mailerlite_lib
from auth0_lib import load_auth0_lib
from git_lib import load_git_lib

# Load libraries
stripe = load_stripe_lib('af_stripe_config.json')
mailer = load_mailerlite_lib('af_mailerlite_config.json')
auth = load_auth0_lib('af_auth0_config.json')
git = load_git_lib('af_git_config.json')

# Use them
stripe.create_complete_subscription_product(
    business_name="InboxTamer",
    monthly_price_dollars=49.00
)
```

---

## Features

### Shared Design

All four libraries share:

- ✅ **Config-driven** - Separate AF and FO accounts
- ✅ **Configurable logging** - ERROR/INFO/DEBUG levels
- ✅ **Automatic retry** - Exponential backoff on failures
- ✅ **Terminal-friendly** - Designed for vi/bash workflows
- ✅ **Comprehensive errors** - Detailed error information
- ✅ **Consistent API** - Same patterns across all libraries
- ✅ **Heavy documentation** - Comments and examples everywhere

### Stripe Library

```python
# Create complete subscription setup
result = stripe.create_complete_subscription_product(
    business_name="YourBusiness",
    monthly_price_dollars=49.00,
    annual_price_dollars=499.00
)

payment_link = result["monthly_payment_link"]
```

**Features:**
- Product and price creation
- Payment link generation
- Subscription management
- Webhook verification
- Cancellation support

[Full Stripe Documentation →](README_STRIPE_LIB.md)

### MailerLite Library

```python
# Add subscriber to email list
result = mailer.add_subscriber(
    email="user@example.com",
    fields={"name": "John Doe"},
    groups=["welcome_group_id"]
)

# Set up welcome automation
result = mailer.setup_welcome_automation(
    business_name="YourBusiness"
)
```

**Features:**
- Subscriber management
- Group operations
- Campaign tracking
- Automation workflows
- Webhook support

### Auth0 Library

```python
# Create user
result = auth.create_user(
    email="user@example.com",
    password="SecurePassword123!",
    email_verified=False
)

# Set up basic auth structure
result = auth.setup_basic_auth(
    business_name="YourBusiness"
)
```

**Features:**
- User CRUD operations
- Role management
- Password reset flows
- Email verification
- Token management

### Git Library

```python
# Set up new repository
result = git.setup_new_repo(
    repo_path="/repos/your-business",
    remote_url="https://github.com/user/repo.git",
    initial_files={
        "README.md": "# Your Business",
        ".gitignore": "*.pyc\n__pycache__/"
    }
)

# Commit and push
git.add_and_commit(repo_path, "Update code")
git.push(repo_path, remote="origin", branch="main")
```

**Features:**
- Repository initialization
- Commit operations
- Branch management
- Tag operations
- Remote operations (GitHub/GitLab)

---

## Installation

### System Requirements

- **Python:** 3.9+
- **Git:** 2.x+ (system package)
- **OS:** macOS, Linux, Windows (WSL)

### Python Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

Installs:
- `stripe>=7.0.0` - Stripe API client
- `requests>=2.31.0` - HTTP library for MailerLite/Auth0

### Git Installation

```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt-get install git

# Verify
git --version
```

---

## Configuration

### Config File Structure

All libraries use JSON config files:

```json
{
  "api_key_or_credentials": "YOUR_KEY_HERE",
  "account_name": "Your Account Name",
  "log_level": "INFO",
  "log_file": "operations.log"
}
```

### Getting API Credentials

**Stripe:**
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy "Secret key" (starts with `sk_test_` for testing)
3. Add to `af_stripe_config.json` or `fo_stripe_config.json`

**MailerLite:**
1. Go to https://dashboard.mailerlite.com/integrations/api
2. Generate API key
3. Add to `af_mailerlite_config.json` or `fo_mailerlite_config.json`

**Auth0:**
1. Go to https://manage.auth0.com/dashboard
2. Create Machine-to-Machine Application
3. Authorize for Auth0 Management API
4. Grant scopes: `read:users`, `create:users`, `update:users`, `delete:users`, `read:roles`, `create:roles`, `update:roles`
5. Copy Domain, Client ID, Client Secret
6. Add to `af_auth0_config.json` or `fo_auth0_config.json`

**Git (optional for remote operations):**
1. GitHub: https://github.com/settings/tokens (Generate personal access token)
2. GitLab: https://gitlab.com/-/profile/personal_access_tokens
3. Add to `af_git_config.json` or `fo_git_config.json`

### Multi-Account Support

Use separate configs for AF (your portfolio) vs FO (customer deployments):

```python
# AF operations (your account)
af_stripe = load_stripe_lib('af_stripe_config.json')

# FO operations (customer account)
fo_stripe = load_stripe_lib('fo_stripe_config.json')
```

---

## Testing

### Test Suite

Four comprehensive test suites validate all functionality:

```bash
# Run all tests
python run_all_tests.py

# Run individual tests
python run_all_tests.py stripe      # ~30 seconds
python run_all_tests.py mailerlite  # ~45 seconds
python run_all_tests.py auth0       # ~60 seconds
python run_all_tests.py git         # ~30 seconds (local only)
```

### What Gets Tested

- ✅ Config loading and validation
- ✅ Library initialization
- ✅ All CRUD operations
- ✅ Convenience methods
- ✅ Error handling
- ✅ Retry logic
- ✅ Automatic cleanup (where possible)

### Test Requirements

**Stripe:** Test mode API key  
**MailerLite:** Valid API key (creates/deletes test data)  
**Auth0:** M2M application with proper scopes  
**Git:** No API credentials needed (local operations only)

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for complete details.

---

## Usage Examples

### Complete Business Setup

```python
from stripe_lib import load_stripe_lib
from mailerlite_lib import load_mailerlite_lib
from auth0_lib import load_auth0_lib
from git_lib import load_git_lib

def setup_af_business(business_name, monthly_price):
    """Complete automated setup for one AF business"""
    
    # Load all libraries
    stripe = load_stripe_lib('af_stripe_config.json')
    mailer = load_mailerlite_lib('af_mailerlite_config.json')
    auth = load_auth0_lib('af_auth0_config.json')
    git = load_git_lib('af_git_config.json')
    
    print(f"Setting up {business_name}...")
    
    # 1. Payment processing
    payment = stripe.create_complete_subscription_product(
        business_name=business_name,
        monthly_price_dollars=monthly_price
    )
    
    # 2. Email marketing
    email = mailer.setup_welcome_automation(
        business_name=business_name
    )
    
    # 3. Authentication
    authentication = auth.setup_basic_auth(
        business_name=business_name
    )
    
    # 4. Git repository
    repo = git.setup_new_repo(
        repo_path=f"/repos/{business_name.lower()}",
        remote_url=f"https://github.com/af/{business_name.lower()}.git",
        initial_files={
            "README.md": f"# {business_name}",
            ".gitignore": "*.pyc\n__pycache__/\n.env"
        }
    )
    
    print(f"✓ {business_name} ready!")
    print(f"  Payment: {payment['monthly_payment_link']}")
    print(f"  Email group: {email['group']['id']}")
    print(f"  Roles: {list(authentication['roles'].keys())}")
    print(f"  Repo: {repo['repo_path']}")
    
    return {
        "payment_link": payment["monthly_payment_link"],
        "email_group_id": email["group"]["id"],
        "auth_roles": authentication["roles"],
        "repo_commit": repo.get("commit_hash")
    }

# Set up InboxTamer
config = setup_af_business("InboxTamer", 49.00)
```

**Time:** ~30 seconds per business  
**Manual alternative:** 90-150 minutes per business

### User Signup Flow

```python
def handle_user_signup(email, password, name):
    """Complete user signup across all systems"""
    
    auth = load_auth0_lib('af_auth0_config.json')
    mailer = load_mailerlite_lib('af_mailerlite_config.json')
    
    # 1. Create Auth0 user
    user = auth.create_user(
        email=email,
        password=password,
        user_metadata={"name": name}
    )
    
    if not user["success"]:
        return {"error": "Account creation failed"}
    
    # 2. Add to email list
    subscriber = mailer.add_subscriber(
        email=email,
        fields={"name": name},
        groups=["new_users_group_id"]
    )
    
    # 3. Assign default role
    auth.assign_roles_to_user(
        user_id=user["data"]["user_id"],
        role_ids=["user_role_id"]
    )
    
    # 4. Send verification email
    auth.send_verification_email(user["data"]["user_id"])
    
    return {
        "success": True,
        "user_id": user["data"]["user_id"]
    }
```

### Batch Deploy 25 Businesses

```python
AF_PORTFOLIO = [
    {"name": "InboxTamer", "price": 49.00},
    {"name": "LeadGenerator", "price": 29.00},
    {"name": "ContentScheduler", "price": 39.00},
    # ... 22 more
]

for business in AF_PORTFOLIO:
    config = setup_af_business(
        business_name=business["name"],
        monthly_price=business["price"]
    )
    
    # Save config
    with open(f"configs/{business['name'].lower()}.json", 'w') as f:
        json.dump(config, f, indent=2)

print(f"✓ Deployed {len(AF_PORTFOLIO)} businesses in ~12.5 minutes")
```

---

## Logging & Debugging

### Log Levels

All libraries support three log levels:

| Level | When to Use | What Gets Logged |
|-------|-------------|------------------|
| `ERROR` | Production (quiet) | Only failures |
| `INFO` | Normal operation | Operations and results |
| `DEBUG` | Troubleshooting | Everything (requests, retries, full responses) |

### Change Log Level

**Method 1: Edit config file (requires restart)**

```json
{
  "log_level": "DEBUG"
}
```

**Method 2: Environment variable (no restart for new processes)**

```bash
export STRIPE_LOG_LEVEL=DEBUG
export MAILERLITE_LOG_LEVEL=DEBUG
export AUTH0_LOG_LEVEL=DEBUG
export GIT_LOG_LEVEL=DEBUG

python your_script.py
```

### Log Files

Logs are written to both stdout (terminal) and files:

```bash
# Watch logs in real-time
tail -f stripe_operations.log
tail -f mailerlite_operations.log
tail -f auth0_operations.log
tail -f git_operations.log

# Search logs
grep ERROR stripe_operations.log
grep InboxTamer mailerlite_operations.log
```

### Example Debug Output

```
2025-01-21 10:23:45 [STRIPE-LIB] INFO - Creating subscription product: InboxTamer
2025-01-21 10:23:45 [STRIPE-LIB] DEBUG - CREATE_PRODUCT[InboxTamer] - Attempt 1/3 | {"kwargs": {...}}
2025-01-21 10:23:46 [STRIPE-LIB] INFO - CREATE_PRODUCT[InboxTamer] - SUCCESS | {"attempt": 1, "elapsed_sec": 0.234}
2025-01-21 10:23:46 [STRIPE-LIB] DEBUG - CREATE_PRODUCT[InboxTamer] - Full response | {"response": {...}}
```

---

## Error Handling

### Standard Return Format

All library methods return a consistent format:

```python
{
    "success": bool,           # True if operation succeeded
    "data": dict,             # Result data (if success=True)
    "error": str,             # Error message (if success=False)
    "error_detail": dict,     # Full error details (if available)
    "attempts": int,          # Number of retry attempts made
    "elapsed_sec": float      # Time taken
}
```

### Error Handling Pattern

```python
result = stripe.create_subscription_product(
    business_name="Test",
    description="Test product"
)

if not result["success"]:
    # Handle error
    print(f"Operation failed: {result['error']}")
    print(f"Status code: {result.get('status_code')}")
    print(f"Attempts: {result.get('attempts')}")
    
    # Full details in DEBUG mode
    if 'error_detail' in result:
        print(f"Details: {result['error_detail']}")
    
    # Take action
    if result.get('status_code') == 401:
        print("Invalid API key")
    elif result.get('status_code') == 429:
        print("Rate limited - wait and retry")
else:
    # Success
    data = result["data"]
    print(f"Product created: {data['id']}")
```

### Automatic Retry

All libraries retry failed operations automatically:

- **Attempts:** 3 (configurable)
- **Backoff:** Exponential (1s, 2s, 4s)
- **Retryable errors:** Network issues, rate limits, 5xx errors
- **Non-retryable:** 400, 401, 403, 404 errors

Retry behavior is logged at DEBUG level.

---

## Security

### Credentials Management

**Never commit API keys to Git:**

```bash
# Add to .gitignore
*_config.json
*.log
.env
```

**Use environment variables in production:**

```python
import os

config = {
    "stripe_secret_key": os.getenv("STRIPE_SECRET_KEY"),
    "mailerlite_api_key": os.getenv("MAILERLITE_API_KEY"),
    # ...
}

stripe = load_stripe_lib_from_dict(config)
```

### Security Features

**Stripe:**
- ✅ PCI-scope minimized (no raw card data)
- ✅ Webhook signature verification
- ✅ Token-based authentication

**Auth0:**
- ✅ Passwords redacted in logs
- ✅ Management token auto-refresh
- ✅ Secure password reset flows

**MailerLite:**
- ✅ API key-based auth (Bearer token)
- ✅ HTTPS only

**Git:**
- ✅ Token injection for remote URLs
- ✅ Support for GitHub/GitLab tokens
- ✅ No credentials in logs

---

## Production Deployment

### Recommended Structure

```
production/
├── teebu-shared-libs/          # Git submodule or pip install
├── af-portfolio/
│   ├── configs/
│   │   ├── af_stripe_config.json
│   │   ├── af_mailerlite_config.json
│   │   ├── af_auth0_config.json
│   │   └── af_git_config.json
│   ├── deploy_business.py
│   └── manage_portfolio.py
└── fo-build-system/
    ├── configs/
    │   ├── fo_stripe_config.json
    │   ├── fo_mailerlite_config.json
    │   ├── fo_auth0_config.json
    │   └── fo_git_config.json
    └── build_customer.py
```

### Environment Variables

```bash
# Production environment
export STRIPE_SECRET_KEY="sk_live_..."
export MAILERLITE_API_KEY="..."
export AUTH0_CLIENT_ID="..."
export AUTH0_CLIENT_SECRET="..."
export GITHUB_TOKEN="..."

# Log level
export STRIPE_LOG_LEVEL=INFO
export MAILERLITE_LOG_LEVEL=INFO
export AUTH0_LOG_LEVEL=INFO
export GIT_LOG_LEVEL=INFO
```

### Monitoring

```python
import logging

# Set up application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Libraries will log to their own files
# Plus you can capture application-level events
```

---

## Troubleshooting

### Common Issues

**"Invalid API key"**
- ✓ Verify key is correct in config
- ✓ For Stripe: Use test mode key (sk_test_...)
- ✓ Check for extra spaces when copying
- ✓ Ensure config file is being loaded

**"Permission denied" (Auth0)**
- ✓ Verify M2M app has required scopes
- ✓ Re-authorize if scopes changed
- ✓ Check client_id and client_secret match

**"Rate limit exceeded"**
- ✓ Wait 60 seconds before retrying
- ✓ Reduce request frequency
- ✓ Libraries include retry logic

**"Git command not found"**
- ✓ Install Git: `brew install git` (macOS) or `apt-get install git` (Linux)
- ✓ Verify: `git --version`

**Tests fail partway through**
- ✓ Enable DEBUG logging
- ✓ Check error messages
- ✓ Verify API credentials
- ✓ Clean up test data manually if needed

### Debug Checklist

1. ✓ Enable DEBUG logging
2. ✓ Check log files
3. ✓ Verify API credentials
4. ✓ Check API status pages
5. ✓ Run individual tests
6. ✓ Review error details
7. ✓ Check rate limits

### API Status Pages

- Stripe: https://status.stripe.com
- MailerLite: https://status.mailerlite.com
- Auth0: https://status.auth0.com
- GitHub: https://www.githubstatus.com

---

## Contributing

### Development Setup

```bash
# Clone repo
git clone https://github.com/teebu/teebu-shared-libs.git
cd teebu-shared-libs

# Install in development mode
pip install -e .

# Run tests
python run_all_tests.py
```

### Code Style

- Heavy commenting (explain why, not just what)
- Consistent error handling
- Comprehensive logging
- Type hints encouraged
- Docstrings for all public methods

### Pull Request Process

1. Create feature branch
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description

---

## License

Proprietary - Teebu (AF/FO Systems)

---

## Changelog

### v1.0.0 (2025-01-21)

**Initial Release**

- ✅ Stripe library - Payment processing
- ✅ MailerLite library - Email marketing
- ✅ Auth0 library - Authentication
- ✅ Git library - Version control
- ✅ Complete test coverage (4 test suites)
- ✅ Comprehensive documentation
- ✅ Config-driven multi-account support
- ✅ Automatic retry with backoff
- ✅ Configurable logging (ERROR/INFO/DEBUG)

---

## Support

### Documentation

- **Complete Guide:** [ALL_LIBRARIES_SUMMARY.txt](ALL_LIBRARIES_SUMMARY.txt)
- **Stripe Details:** [README_STRIPE_LIB.md](README_STRIPE_LIB.md)
- **Testing Guide:** [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Source Code:** All libraries are heavily commented

### Getting Help

1. Check documentation
2. Review library source code (comments explain everything)
3. Enable DEBUG logging
4. Check log files
5. Review test examples

---

## Acknowledgments

Built for solo operators who need:
- ✅ Deterministic systems (no surprises)
- ✅ Debuggable operations (verbose when needed)
- ✅ Terminal-friendly workflows (vi/bash)
- ✅ Production-ready code (proper error handling)

**Time savings: 37-62 hours per 25 business deployments**

---

## Quick Reference

### Load Libraries

```python
from stripe_lib import load_stripe_lib
from mailerlite_lib import load_mailerlite_lib
from auth0_lib import load_auth0_lib
from git_lib import load_git_lib
```

### Essential Operations

```python
# Stripe
stripe.create_complete_subscription_product(name, price)
stripe.cancel_subscription(subscription_id)

# MailerLite
mailer.add_subscriber(email, fields, groups)
mailer.setup_welcome_automation(business_name)

# Auth0
auth.create_user(email, password)
auth.setup_basic_auth(business_name)

# Git
git.setup_new_repo(repo_path, remote_url, initial_files)
git.add_and_commit(repo_path, message)
git.push(repo_path, remote, branch)
```

### Run Tests

```bash
python run_all_tests.py              # All tests
python run_all_tests.py stripe       # Individual
```

### Enable Debug Logging

```bash
export STRIPE_LOG_LEVEL=DEBUG
export MAILERLITE_LOG_LEVEL=DEBUG
export AUTH0_LOG_LEVEL=DEBUG
export GIT_LOG_LEVEL=DEBUG
```

---

**Ready to ship? Start with InboxTamer. Then scale to 25 businesses. Hit $15k/month. You have the tools.**
