"""
Stripe Library Usage Examples
==============================

Examples showing how to use stripe_lib.py in AF and FO contexts.
"""

from stripe_lib import load_stripe_lib, load_stripe_lib_from_dict


# ============================================================
# EXAMPLE 1: BASIC SETUP (AF PORTFOLIO)
# ============================================================

def example_af_basic():
    """Load library with AF config and create a product"""
    
    # Load from config file
    stripe = load_stripe_lib('af_stripe_config.json')
    
    # Create a product for InboxTamer
    result = stripe.create_subscription_product(
        business_name="InboxTamer",
        description="AI-powered email productivity tool"
    )
    
    if result["success"]:
        print(f"Product created: {result['data']['id']}")
        print(f"Product name: {result['data']['name']}")
    else:
        print(f"Error: {result['error']}")


# ============================================================
# EXAMPLE 2: COMPLETE BUSINESS SETUP (ONE CALL)
# ============================================================

def example_complete_setup():
    """Create product + prices + payment links in one call"""
    
    stripe = load_stripe_lib('af_stripe_config.json')
    
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
        if result["annual_payment_link"]:
            print(f"✓ Annual payment link: {result['annual_payment_link']}")
    else:
        print(f"✗ Errors: {result['errors']}")


# ============================================================
# EXAMPLE 3: MANUAL STEP-BY-STEP SETUP
# ============================================================

def example_manual_setup():
    """Create product, prices, and links step by step"""
    
    stripe = load_stripe_lib('af_stripe_config.json')
    
    # Step 1: Create product
    product_result = stripe.create_subscription_product(
        business_name="LeadGenerator",
        description="B2B lead generation tool",
        metadata={
            "launch_date": "2025-01-25",
            "target_arr": "6000"
        }
    )
    
    if not product_result["success"]:
        print(f"Failed to create product: {product_result['error']}")
        return
    
    product_id = product_result["data"]["id"]
    print(f"✓ Product created: {product_id}")
    
    # Step 2: Create monthly price
    monthly_result = stripe.create_price(
        product_id=product_id,
        amount_cents=2900,  # $29.00
        interval="month",
        metadata={"tier": "standard"}
    )
    
    if not monthly_result["success"]:
        print(f"Failed to create monthly price: {monthly_result['error']}")
        return
    
    monthly_price_id = monthly_result["data"]["id"]
    print(f"✓ Monthly price created: {monthly_price_id}")
    
    # Step 3: Create payment link
    link_result = stripe.create_payment_link(
        price_id=monthly_price_id,
        after_completion_url="https://leadgenerator.com/welcome"
    )
    
    if not link_result["success"]:
        print(f"Failed to create payment link: {link_result['error']}")
        return
    
    payment_link = link_result["data"]["url"]
    print(f"✓ Payment link: {payment_link}")


# ============================================================
# EXAMPLE 4: LOADING FROM DICT (FO BUILD AUTOMATION)
# ============================================================

def example_fo_build_automation():
    """Load config from dict (useful in FO build scripts)"""
    
    # In FO build, you might construct config dynamically
    config = {
        "stripe_secret_key": "sk_live_FO_KEY",
        "stripe_webhook_secret": "whsec_FO_WEBHOOK",
        "account_name": "FounderOps LLC",
        "log_level": "DEBUG",  # More verbose for build debugging
        "log_file": "/var/log/fo_stripe.log"
    }
    
    stripe = load_stripe_lib_from_dict(config)
    
    # Create customer's business
    result = stripe.create_complete_subscription_product(
        business_name="CustomerBusinessName",
        monthly_price_dollars=99.00,
        description="Customer's SaaS product"
    )
    
    return result


# ============================================================
# EXAMPLE 5: WEBHOOK HANDLING
# ============================================================

def example_webhook_handler(request_body: bytes, signature_header: str):
    """Handle incoming Stripe webhook"""
    
    stripe = load_stripe_lib('af_stripe_config.json')
    
    # Step 1: Verify signature
    verify_result = stripe.verify_webhook_signature(
        payload=request_body,
        signature_header=signature_header
    )
    
    if not verify_result["success"]:
        print(f"Invalid webhook signature: {verify_result['error']}")
        return {"status": "error", "message": "Invalid signature"}
    
    event = verify_result["event"]
    
    # Step 2: Define handlers for different event types
    def handle_subscription_created(event):
        print(f"New subscription created!")
        subscription = event["data"]["object"]
        print(f"Customer: {subscription['customer']}")
        print(f"Amount: ${subscription['plan']['amount'] / 100}")
        # Your business logic here (send welcome email, etc)
        return {"processed": True}
    
    def handle_subscription_deleted(event):
        print(f"Subscription canceled")
        subscription = event["data"]["object"]
        print(f"Customer: {subscription['customer']}")
        # Your business logic here (send goodbye email, disable access, etc)
        return {"processed": True}
    
    def handle_payment_failed(event):
        print(f"Payment failed!")
        invoice = event["data"]["object"]
        print(f"Customer: {invoice['customer']}")
        # Your business logic here (send dunning email, etc)
        return {"processed": True}
    
    handlers = {
        "customer.subscription.created": handle_subscription_created,
        "customer.subscription.deleted": handle_subscription_deleted,
        "invoice.payment_failed": handle_payment_failed,
    }
    
    # Step 3: Route event to handler
    handle_result = stripe.handle_webhook_event(event, handlers)
    
    return handle_result


# ============================================================
# EXAMPLE 6: CANCEL SUBSCRIPTION
# ============================================================

def example_cancel_subscription():
    """Cancel a customer's subscription"""
    
    stripe = load_stripe_lib('af_stripe_config.json')
    
    subscription_id = "sub_1234567890"
    
    # Cancel at end of billing period (default)
    result = stripe.cancel_subscription(
        subscription_id=subscription_id,
        at_period_end=True
    )
    
    if result["success"]:
        print(f"Subscription will cancel at period end")
        print(f"Cancel date: {result['data']['cancel_at']}")
    else:
        print(f"Cancel failed: {result['error']}")
    
    # Or cancel immediately
    result_immediate = stripe.cancel_subscription(
        subscription_id=subscription_id,
        at_period_end=False
    )
    
    if result_immediate["success"]:
        print(f"Subscription canceled immediately")


# ============================================================
# EXAMPLE 7: DEBUG MODE (TROUBLESHOOTING)
# ============================================================

def example_debug_mode():
    """Enable verbose logging for troubleshooting"""
    
    # Method 1: Set in config file
    # Change "log_level": "INFO" to "log_level": "DEBUG"
    
    # Method 2: Set via environment variable (no restart needed for new processes)
    import os
    os.environ['STRIPE_LOG_LEVEL'] = 'DEBUG'
    
    # Now all Stripe operations will log verbosely
    stripe = load_stripe_lib('af_stripe_config.json')
    
    # This will log:
    # - Full request parameters
    # - Retry attempts
    # - Full Stripe responses
    # - Timing information
    result = stripe.create_subscription_product(
        business_name="DebugTest",
        description="Testing verbose logging"
    )
    
    # To turn off debug mode:
    # os.environ['STRIPE_LOG_LEVEL'] = 'INFO'
    # (Or restart process after editing config)


# ============================================================
# EXAMPLE 8: FO BUILD SCRIPT INTEGRATION
# ============================================================

def example_fo_build_script(business_name: str, monthly_price: float):
    """
    Example FO build script function.
    This would be called during automated business deployment.
    """
    
    print(f"=== FO Build: Setting up Stripe for {business_name} ===")
    
    # Load FO Stripe config
    stripe = load_stripe_lib('fo_stripe_config.json')
    
    # Create complete setup
    result = stripe.create_complete_subscription_product(
        business_name=business_name,
        monthly_price_dollars=monthly_price,
        description=f"Subscription for {business_name}",
        after_completion_url=f"https://{business_name.lower()}.com/welcome"
    )
    
    if not result["success"]:
        print(f"✗ Stripe setup FAILED: {result['errors']}")
        return None
    
    # Save IDs to config file for the business
    import json
    stripe_config = {
        "product_id": result["product"]["id"],
        "monthly_price_id": result["monthly_price"]["id"],
        "monthly_payment_link": result["monthly_payment_link"],
    }
    
    with open(f"{business_name.lower()}_stripe_config.json", 'w') as f:
        json.dump(stripe_config, f, indent=2)
    
    print(f"✓ Stripe setup complete")
    print(f"✓ Payment link: {result['monthly_payment_link']}")
    print(f"✓ Config saved to {business_name.lower()}_stripe_config.json")
    
    return stripe_config


# ============================================================
# EXAMPLE 9: AF PORTFOLIO - BATCH SETUP
# ============================================================

def example_af_batch_setup():
    """Set up multiple AF businesses at once"""
    
    stripe = load_stripe_lib('af_stripe_config.json')
    
    businesses = [
        {"name": "InboxTamer", "price": 49.00},
        {"name": "LeadGenerator", "price": 29.00},
        {"name": "ContentScheduler", "price": 39.00},
    ]
    
    results = []
    
    for business in businesses:
        print(f"\n=== Setting up {business['name']} ===")
        
        result = stripe.create_complete_subscription_product(
            business_name=business["name"],
            monthly_price_dollars=business["price"],
            description=f"Subscription for {business['name']}"
        )
        
        if result["success"]:
            print(f"✓ {business['name']} setup complete")
            print(f"  Payment link: {result['monthly_payment_link']}")
        else:
            print(f"✗ {business['name']} setup FAILED: {result['errors']}")
        
        results.append({
            "business": business["name"],
            "success": result["success"],
            "payment_link": result.get("monthly_payment_link")
        })
    
    return results


# ============================================================
# EXAMPLE 10: ERROR HANDLING
# ============================================================

def example_error_handling():
    """Proper error handling patterns"""
    
    stripe = load_stripe_lib('af_stripe_config.json')
    
    result = stripe.create_subscription_product(
        business_name="TestBusiness",
        description="Test product"
    )
    
    # Always check success flag
    if not result["success"]:
        # Access error details
        print(f"Operation failed!")
        print(f"Error message: {result['error']}")
        print(f"Stripe error code: {result.get('stripe_error_code')}")
        print(f"HTTP status: {result.get('http_status')}")
        print(f"Request ID: {result.get('request_id')}")
        print(f"Attempts made: {result.get('attempts')}")
        
        # Full error detail (useful for debugging)
        if 'full_error' in result:
            print(f"Full error details: {result['full_error']}")
        
        # Handle specific error types
        if result.get('stripe_error_code') == 'card_declined':
            print("Customer's card was declined")
        elif result.get('http_status') == 429:
            print("Rate limited - too many requests")
        
        return False
    
    # Success path
    print(f"Product created successfully!")
    print(f"Product ID: {result['data']['id']}")
    print(f"Elapsed time: {result['elapsed_sec']}s")
    print(f"Attempts: {result['attempt']}")
    
    return True


# ============================================================
# RUN EXAMPLES
# ============================================================

if __name__ == "__main__":
    print("Stripe Library Examples")
    print("=" * 60)
    print("\nUncomment examples below to run them\n")
    
    # example_af_basic()
    # example_complete_setup()
    # example_manual_setup()
    # example_debug_mode()
    # example_af_batch_setup()
    # example_error_handling()
    
    print("\nSee function definitions above for usage patterns")
