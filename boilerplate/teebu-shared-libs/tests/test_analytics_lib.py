#!/usr/bin/env python3
"""
Analytics Library Test Suite
=============================

Tests to validate analytics_lib.py functionality.
Run this AFTER setting up your GA4 property and API secret.

Usage:
    python test_analytics_lib.py
"""

import sys
import json
import time
from analytics_lib import AnalyticsConfig, AnalyticsLib, load_analytics_lib

# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CONFIG = {
    "ga4_measurement_id": "G-XXXXXXXXXX",
    "ga4_api_secret": "YOUR_API_SECRET_HERE",
    "account_name": "Test Account",
    "log_level": "DEBUG",
    "debug_mode": True  # Use GA4 debug endpoint to validate events
}

# Test data
TEST_CLIENT_ID = "test_client_12345"
TEST_USER_ID = "test_user_67890"

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
    """Assert that an Analytics operation succeeded"""
    if not result.get("success"):
        print_failure(f"{operation_name} failed")
        print(f"Error: {result.get('error')}")
        if 'response' in result:
            print(f"Response: {json.dumps(result['response'], indent=2)}")
        sys.exit(1)
    print_success(f"{operation_name} succeeded")

# ============================================================
# TESTS
# ============================================================

def test_01_config_loading():
    """Test config loading from dict"""
    print_test_header("Config Loading")
    
    try:
        config = AnalyticsConfig(config_dict=TEST_CONFIG)
        print_success(f"Config loaded: {config}")
        
        assert config.measurement_id == TEST_CONFIG["ga4_measurement_id"]
        assert config.api_secret == TEST_CONFIG["ga4_api_secret"]
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
        config = AnalyticsConfig(config_dict=TEST_CONFIG)
        analytics = AnalyticsLib(config)
        print_success("AnalyticsLib initialized")
        
        assert analytics.config.account_name == "Test Account"
        print_success("Library config accessible")
    except Exception as e:
        print_failure(f"Library initialization failed: {e}")
        sys.exit(1)

def test_03_track_page_view():
    """Test tracking page view"""
    print_test_header("Track Page View")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_page_view(
        page_path="/test-page",
        page_title="Test Page",
        client_id=TEST_CLIENT_ID
    )
    
    assert_success(result, "Track page view")
    
    print_success(f"Events sent: {result.get('events_sent', 0)}")

def test_04_track_custom_event():
    """Test tracking custom event"""
    print_test_header("Track Custom Event")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_event(
        event_name="button_click",
        client_id=TEST_CLIENT_ID,
        user_id=TEST_USER_ID,
        event_params={
            "button_name": "cta_button",
            "page": "/pricing"
        }
    )
    
    assert_success(result, "Track custom event")
    
    print_success(f"Events sent: {result.get('events_sent', 0)}")

def test_05_track_signup():
    """Test tracking user signup"""
    print_test_header("Track Signup")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_signup(
        user_id=TEST_USER_ID,
        client_id=TEST_CLIENT_ID,
        signup_method="email",
        user_properties={
            "plan": "free",
            "source": "landing_page"
        }
    )
    
    assert_success(result, "Track signup")
    
    print_success("Signup event tracked with user properties")

def test_06_track_login():
    """Test tracking user login"""
    print_test_header("Track Login")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_login(
        user_id=TEST_USER_ID,
        client_id=TEST_CLIENT_ID,
        login_method="email"
    )
    
    assert_success(result, "Track login")
    
    print_success("Login event tracked")

def test_07_track_purchase():
    """Test tracking purchase"""
    print_test_header("Track Purchase")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_purchase(
        transaction_id="test_charge_12345",
        value=49.00,
        currency="USD",
        client_id=TEST_CLIENT_ID,
        user_id=TEST_USER_ID,
        items=[{
            "item_id": "monthly_plan",
            "item_name": "Monthly Subscription",
            "price": 49.00,
            "quantity": 1
        }]
    )
    
    assert_success(result, "Track purchase")
    
    print_success("Purchase tracked: $49.00")

def test_08_track_begin_checkout():
    """Test tracking begin checkout"""
    print_test_header("Track Begin Checkout")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_begin_checkout(
        value=49.00,
        currency="USD",
        client_id=TEST_CLIENT_ID,
        user_id=TEST_USER_ID,
        items=[{
            "item_id": "monthly_plan",
            "item_name": "Monthly Subscription",
            "price": 49.00
        }]
    )
    
    assert_success(result, "Track begin checkout")
    
    print_success("Begin checkout tracked")

def test_09_track_subscription_start():
    """Test tracking subscription start"""
    print_test_header("Track Subscription Start")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_subscription_start(
        subscription_id="sub_test_12345",
        plan_name="Monthly Pro",
        value=49.00,
        currency="USD",
        client_id=TEST_CLIENT_ID,
        user_id=TEST_USER_ID
    )
    
    assert_success(result, "Track subscription start")
    
    print_success("Subscription start tracked")

def test_10_track_subscription_cancel():
    """Test tracking subscription cancel"""
    print_test_header("Track Subscription Cancel")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_subscription_cancel(
        subscription_id="sub_test_12345",
        plan_name="Monthly Pro",
        client_id=TEST_CLIENT_ID,
        user_id=TEST_USER_ID,
        reason="Too expensive"
    )
    
    assert_success(result, "Track subscription cancel")
    
    print_success("Subscription cancel tracked")

def test_11_track_batch_events():
    """Test tracking multiple events in batch"""
    print_test_header("Track Batch Events")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    events = [
        {
            "name": "feature_used",
            "params": {"feature": "export_data"}
        },
        {
            "name": "feature_used",
            "params": {"feature": "send_email"}
        },
        {
            "name": "button_click",
            "params": {"button": "help"}
        }
    ]
    
    result = analytics.track_events_batch(
        events=events,
        client_id=TEST_CLIENT_ID,
        user_id=TEST_USER_ID
    )
    
    assert_success(result, "Track batch events")
    
    print_success(f"Batch tracked: {result.get('events_sent', 0)} events")

def test_12_track_stripe_webhook():
    """Test convenience method for Stripe webhooks"""
    print_test_header("Track Stripe Webhook")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    # Simulate Stripe charge.succeeded webhook
    stripe_event = {
        "type": "charge.succeeded",
        "data": {
            "object": {
                "id": "ch_test_12345",
                "amount": 4900,  # $49.00 in cents
                "currency": "usd",
                "metadata": {
                    "user_id": TEST_USER_ID
                }
            }
        }
    }
    
    result = analytics.track_stripe_webhook(
        event_type="charge.succeeded",
        stripe_event=stripe_event,
        client_id=TEST_CLIENT_ID
    )
    
    assert_success(result, "Track Stripe webhook")
    
    print_success("Stripe webhook tracked as purchase")

def test_13_client_id_generation():
    """Test automatic client ID generation"""
    print_test_header("Client ID Generation")
    
    config = AnalyticsConfig(config_dict=TEST_CONFIG)
    analytics = AnalyticsLib(config)
    
    # Track event without providing client_id
    result = analytics.track_event(
        event_name="test_event",
        user_id=TEST_USER_ID
    )
    
    assert_success(result, "Track event with auto-generated client_id")
    
    print_success("Client ID generated automatically")

def test_14_error_handling():
    """Test error handling with invalid config"""
    print_test_header("Error Handling")
    
    # Create config with invalid credentials
    invalid_config = {
        "ga4_measurement_id": "G-INVALID",
        "ga4_api_secret": "invalid_secret",
        "account_name": "Test",
        "log_level": "DEBUG",
        "debug_mode": False
    }
    
    config = AnalyticsConfig(config_dict=invalid_config)
    analytics = AnalyticsLib(config)
    
    result = analytics.track_event(
        event_name="test_event",
        client_id=TEST_CLIENT_ID
    )
    
    # This might succeed (GA4 accepts events without validation in non-debug mode)
    # Or fail gracefully
    if result["success"]:
        print_success("Event sent (GA4 accepted without validation)")
    else:
        print_success("Error handled gracefully")
        print_success(f"Error message: {result.get('error')}")

# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all tests in sequence"""
    
    print("\n" + "=" * 60)
    print("ANALYTICS LIBRARY TEST SUITE")
    print("=" * 60)
    
    # Check if credentials are configured
    if "XXXXXXXXXX" in TEST_CONFIG["ga4_measurement_id"]:
        print("\n" + "!" * 60)
        print("ERROR: GA4 credentials not configured!")
        print("!" * 60)
        print("\nPlease edit test_analytics_lib.py and set:")
        print("1. ga4_measurement_id (from GA4 property)")
        print("2. ga4_api_secret (from GA4 Data Streams)")
        print("\nHow to get credentials:")
        print("1. Go to GA4 Admin → Data Streams")
        print("2. Click on your stream")
        print("3. Scroll down to 'Measurement Protocol API secrets'")
        print("4. Create secret and copy values")
        print("\nNote: Tests use debug mode to validate events")
        sys.exit(1)
    
    try:
        # Basic tests
        test_01_config_loading()
        test_02_library_initialization()
        
        # Page tracking
        test_03_track_page_view()
        
        # Custom events
        test_04_track_custom_event()
        
        # User lifecycle
        test_05_track_signup()
        test_06_track_login()
        
        # E-commerce
        test_07_track_purchase()
        test_08_track_begin_checkout()
        test_09_track_subscription_start()
        test_10_track_subscription_cancel()
        
        # Batch tracking
        test_11_track_batch_events()
        
        # Convenience methods
        test_12_track_stripe_webhook()
        
        # Utility tests
        test_13_client_id_generation()
        test_14_error_handling()
        
        # Success summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nAnalytics library is working correctly!")
        print("\nNext steps:")
        print("1. Check events in GA4 DebugView (real-time)")
        print("2. Wait 24-48 hours for events in standard reports")
        print("3. Integrate into your SaaS boilerplate")
        print("4. Track real user events")
        
        print("\nGA4 DebugView:")
        print("Admin → DebugView → See events in real-time")
        
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
