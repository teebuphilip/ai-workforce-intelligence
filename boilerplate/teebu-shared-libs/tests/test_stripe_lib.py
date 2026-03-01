#!/usr/bin/env python3
"""
Stripe Library Test Suite
==========================

Basic tests to validate stripe_lib.py functionality.
Run this AFTER setting up your Stripe test account keys.

Usage:
    python test_stripe_lib.py
"""

import sys
import json
from stripe_lib import StripeConfig, StripeLib, load_stripe_lib

# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CONFIG = {
    "stripe_secret_key": "sk_test_REPLACE_WITH_YOUR_TEST_KEY",
    "stripe_webhook_secret": "whsec_test_REPLACE_WITH_YOUR_TEST_WEBHOOK_SECRET",
    "account_name": "Test Account",
    "log_level": "DEBUG"
}

# ============================================================
# TEST HELPERS
# ============================================================

def print_test_header(test_name):
    print(f"\n{'=' * 60}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 60}\n")

def print_success(message):
    print(f"✓ {message}")

def print_failure(message):
    print(f"✗ {message}")

def assert_success(result, operation_name):
    """Assert that a Stripe operation succeeded"""
    if not result.get("success"):
        print_failure(f"{operation_name} failed")
        print(f"Error: {result.get('error')}")
        if 'full_error' in result:
            print(f"Details: {json.dumps(result['full_error'], indent=2)}")
        sys.exit(1)
    print_success(f"{operation_name} succeeded")

# ============================================================
# TESTS
# ============================================================

def test_01_config_loading():
    """Test config loading from dict"""
    print_test_header("Config Loading")
    
    try:
        config = StripeConfig(config_dict=TEST_CONFIG)
        print_success(f"Config loaded: {config}")
        
        assert config.stripe_secret_key == TEST_CONFIG["stripe_secret_key"]
        assert config.account_name == TEST_CONFIG["account_name"]
        assert config.log_level == TEST_CONFIG["log_level"]
        
        print_success("Config fields validated")
    except Exception as e:
        print_failure(f"Config loading failed: {e}")
        sys.exit(1)

def test_02_library_initialization():
    """Test library initialization"""
    print_test_header("Library Initialization")
    
    try:
        config = StripeConfig(config_dict=TEST_CONFIG)
        stripe = StripeLib(config)
        print_success("StripeLib initialized")
        
        assert stripe.config.account_name == "Test Account"
        print_success("Library config accessible")
    except Exception as e:
        print_failure(f"Library initialization failed: {e}")
        sys.exit(1)

def test_03_create_product():
    """Test product creation"""
    print_test_header("Product Creation")
    
    config = StripeConfig(config_dict=TEST_CONFIG)
    stripe = StripeLib(config)
    
    result = stripe.create_subscription_product(
        business_name="TestBusiness",
        description="Test product for validation",
        metadata={"test": "true"}
    )
    
    assert_success(result, "Create product")
    
    product = result["data"]
    print_success(f"Product ID: {product['id']}")
    print_success(f"Product name: {product['name']}")
    
    return product["id"]

def test_04_create_price(product_id):
    """Test price creation"""
    print_test_header("Price Creation")
    
    config = StripeConfig(config_dict=TEST_CONFIG)
    stripe = StripeLib(config)
    
    result = stripe.create_price(
        product_id=product_id,
        amount_cents=4900,  # $49.00
        interval="month"
    )
    
    assert_success(result, "Create price")
    
    price = result["data"]
    print_success(f"Price ID: {price['id']}")
    print_success(f"Price amount: ${price['unit_amount'] / 100}")
    
    return price["id"]

def test_05_create_payment_link(price_id):
    """Test payment link creation"""
    print_test_header("Payment Link Creation")
    
    config = StripeConfig(config_dict=TEST_CONFIG)
    stripe = StripeLib(config)
    
    result = stripe.create_payment_link(
        price_id=price_id,
        after_completion_url="https://example.com/success"
    )
    
    assert_success(result, "Create payment link")
    
    link = result["data"]
    print_success(f"Payment link: {link['url']}")
    
    return link["url"]

def test_06_complete_setup():
    """Test complete subscription setup (convenience method)"""
    print_test_header("Complete Subscription Setup")
    
    config = StripeConfig(config_dict=TEST_CONFIG)
    stripe = StripeLib(config)
    
    result = stripe.create_complete_subscription_product(
        business_name="TestComplete",
        monthly_price_dollars=49.00,
        annual_price_dollars=499.00,
        description="Complete test product"
    )
    
    assert_success(result, "Complete setup")
    
    print_success(f"Product ID: {result['product']['id']}")
    print_success(f"Monthly payment link: {result['monthly_payment_link']}")
    
    if result.get('annual_payment_link'):
        print_success(f"Annual payment link: {result['annual_payment_link']}")

def test_07_error_handling():
    """Test error handling with invalid input"""
    print_test_header("Error Handling")
    
    config = StripeConfig(config_dict=TEST_CONFIG)
    stripe = StripeLib(config)
    
    # Try to create price with invalid product ID
    result = stripe.create_price(
        product_id="prod_invalid_id_12345",
        amount_cents=4900,
        interval="month"
    )
    
    # This should fail gracefully
    if not result["success"]:
        print_success("Error handled correctly")
        print_success(f"Error message: {result['error']}")
        print_success(f"Stripe error code: {result.get('stripe_error_code')}")
    else:
        print_failure("Should have failed but didn't")
        sys.exit(1)

# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all tests in sequence"""
    
    print("\n" + "=" * 60)
    print("STRIPE LIBRARY TEST SUITE")
    print("=" * 60)
    
    # Check if test keys are configured
    if "REPLACE_WITH_YOUR_TEST_KEY" in TEST_CONFIG["stripe_secret_key"]:
        print("\n" + "!" * 60)
        print("ERROR: Test keys not configured!")
        print("!" * 60)
        print("\nPlease edit test_stripe_lib.py and set:")
        print("1. stripe_secret_key (get from Stripe Dashboard → Developers → API keys)")
        print("2. stripe_webhook_secret (optional, for webhook tests)")
        print("\nUse TEST MODE keys (sk_test_xxx) not live keys!")
        sys.exit(1)
    
    try:
        # Basic tests
        test_01_config_loading()
        test_02_library_initialization()
        
        # Product/price/link creation
        product_id = test_03_create_product()
        price_id = test_04_create_price(product_id)
        payment_link = test_05_create_payment_link(price_id)
        
        # Convenience method
        test_06_complete_setup()
        
        # Error handling
        test_07_error_handling()
        
        # Success summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nStripe library is working correctly!")
        print("\nNext steps:")
        print("1. Review the created products in Stripe Dashboard")
        print("2. Try the payment links (test mode - no real charges)")
        print("3. Integrate into your AF/FO build scripts")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("TEST SUITE FAILED ✗")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_all_tests()
