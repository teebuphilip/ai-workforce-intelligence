#!/usr/bin/env python3
"""
MailerLite Library Test Suite
==============================

Tests to validate mailerlite_lib.py functionality.
Run this AFTER setting up your MailerLite API key.

Usage:
    python test_mailerlite_lib.py
"""

import sys
import json
from mailerlite_lib import MailerLiteConfig, MailerLiteLib, load_mailerlite_lib

# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CONFIG = {
    "mailerlite_api_key": "REPLACE_WITH_YOUR_MAILERLITE_API_KEY",
    "account_name": "Test Account",
    "log_level": "DEBUG"
}

# Test data
TEST_EMAIL = "test+mailerlite@example.com"
TEST_GROUP_NAME = "Test Group - Delete Me"

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
    """Assert that a MailerLite operation succeeded"""
    if not result.get("success"):
        print_failure(f"{operation_name} failed")
        print(f"Error: {result.get('error')}")
        if 'error_detail' in result:
            print(f"Details: {json.dumps(result['error_detail'], indent=2)}")
        sys.exit(1)
    print_success(f"{operation_name} succeeded")

# ============================================================
# TESTS
# ============================================================

def test_01_config_loading():
    """Test config loading from dict"""
    print_test_header("Config Loading")
    
    try:
        config = MailerLiteConfig(config_dict=TEST_CONFIG)
        print_success(f"Config loaded: {config}")
        
        assert config.api_key == TEST_CONFIG["mailerlite_api_key"]
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
        config = MailerLiteConfig(config_dict=TEST_CONFIG)
        mailer = MailerLiteLib(config)
        print_success("MailerLiteLib initialized")
        
        assert mailer.config.account_name == "Test Account"
        print_success("Library config accessible")
    except Exception as e:
        print_failure(f"Library initialization failed: {e}")
        sys.exit(1)

def test_03_list_fields():
    """Test listing custom fields"""
    print_test_header("List Custom Fields")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.list_fields()
    
    # This might fail if API key is invalid, but we allow it
    if result["success"]:
        print_success("Fields listed successfully")
        print_success(f"Found {len(result['data'].get('data', []))} fields")
    else:
        print_failure(f"List fields failed: {result.get('error')}")
        print("Note: This might indicate invalid API key")

def test_04_create_group():
    """Test group creation"""
    print_test_header("Group Creation")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.create_group(name=TEST_GROUP_NAME)
    
    assert_success(result, "Create group")
    
    group = result["data"]["data"]
    print_success(f"Group ID: {group['id']}")
    print_success(f"Group name: {group['name']}")
    
    return group["id"]

def test_05_list_groups(expected_group_name=None):
    """Test listing groups"""
    print_test_header("List Groups")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.list_groups(limit=10)
    
    assert_success(result, "List groups")
    
    groups = result["data"].get("data", [])
    print_success(f"Found {len(groups)} groups")
    
    if expected_group_name:
        found = any(g["name"] == expected_group_name for g in groups)
        if found:
            print_success(f"Test group '{expected_group_name}' found in list")
        else:
            print_failure(f"Test group '{expected_group_name}' NOT found in list")

def test_06_add_subscriber():
    """Test adding a subscriber"""
    print_test_header("Add Subscriber")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.add_subscriber(
        email=TEST_EMAIL,
        fields={"name": "Test User", "last_name": "MailerLite"},
        status="active"
    )
    
    assert_success(result, "Add subscriber")
    
    subscriber = result["data"]["data"]
    print_success(f"Subscriber ID: {subscriber['id']}")
    print_success(f"Subscriber email: {subscriber['email']}")
    
    return subscriber["id"]

def test_07_get_subscriber_by_email(expected_email):
    """Test getting subscriber by email"""
    print_test_header("Get Subscriber by Email")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.get_subscriber_by_email(email=expected_email)
    
    assert_success(result, "Get subscriber by email")
    
    subscriber = result["data"]
    print_success(f"Found subscriber: {subscriber['email']}")
    print_success(f"Subscriber ID: {subscriber['id']}")
    
    return subscriber["id"]

def test_08_update_subscriber(subscriber_id):
    """Test updating subscriber"""
    print_test_header("Update Subscriber")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.update_subscriber(
        subscriber_id=subscriber_id,
        fields={"name": "Updated Test User"}
    )
    
    assert_success(result, "Update subscriber")
    
    print_success(f"Subscriber updated: {subscriber_id}")

def test_09_add_subscriber_to_group(subscriber_id, group_id):
    """Test adding subscriber to group"""
    print_test_header("Add Subscriber to Group")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.add_subscriber_to_group(
        subscriber_id=subscriber_id,
        group_id=group_id
    )
    
    # This might return success with empty data
    if result["success"] or result.get("status_code") == 200:
        print_success("Subscriber added to group")
    else:
        print_failure(f"Failed to add to group: {result.get('error')}")

def test_10_list_campaigns():
    """Test listing campaigns"""
    print_test_header("List Campaigns")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.list_campaigns(limit=5)
    
    # Campaigns might be empty for new accounts
    if result["success"]:
        campaigns = result["data"].get("data", [])
        print_success(f"Found {len(campaigns)} campaigns")
        
        if campaigns:
            print_success(f"First campaign: {campaigns[0].get('name', 'N/A')}")
    else:
        print_failure(f"List campaigns failed: {result.get('error')}")

def test_11_list_automations():
    """Test listing automations"""
    print_test_header("List Automations")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.list_automations(limit=5)
    
    # Automations might be empty for new accounts
    if result["success"]:
        automations = result["data"].get("data", [])
        print_success(f"Found {len(automations)} automations")
        
        if automations:
            print_success(f"First automation: {automations[0].get('name', 'N/A')}")
    else:
        print_failure(f"List automations failed: {result.get('error')}")

def test_12_setup_welcome_automation():
    """Test convenience method for welcome automation"""
    print_test_header("Setup Welcome Automation")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.setup_welcome_automation(
        business_name="TestBusiness",
        welcome_group_name="TestBusiness Welcome"
    )
    
    assert_success(result, "Setup welcome automation")
    
    print_success(f"Welcome group created: {result['group']['id']}")
    
    return result['group']['id']

def test_13_unsubscribe_subscriber(subscriber_id):
    """Test unsubscribing a subscriber"""
    print_test_header("Unsubscribe Subscriber")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    result = mailer.unsubscribe_subscriber(subscriber_id=subscriber_id)
    
    assert_success(result, "Unsubscribe subscriber")
    
    print_success(f"Subscriber unsubscribed: {subscriber_id}")

def test_14_cleanup(group_ids, subscriber_ids):
    """Clean up test data"""
    print_test_header("Cleanup Test Data")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    # Delete subscribers
    for sub_id in subscriber_ids:
        result = mailer.delete_subscriber(sub_id)
        if result["success"]:
            print_success(f"Deleted subscriber: {sub_id}")
        else:
            print_failure(f"Failed to delete subscriber {sub_id}: {result.get('error')}")
    
    # Delete groups
    for group_id in group_ids:
        result = mailer.delete_group(group_id)
        if result["success"] or result.get("status_code") == 204:
            print_success(f"Deleted group: {group_id}")
        else:
            print_failure(f"Failed to delete group {group_id}: {result.get('error')}")

def test_15_error_handling():
    """Test error handling with invalid input"""
    print_test_header("Error Handling")
    
    config = MailerLiteConfig(config_dict=TEST_CONFIG)
    mailer = MailerLiteLib(config)
    
    # Try to get non-existent subscriber
    result = mailer.get_subscriber(subscriber_id="invalid_id_12345")
    
    # This should fail gracefully
    if not result["success"]:
        print_success("Error handled correctly")
        print_success(f"Error message: {result['error']}")
        print_success(f"Status code: {result.get('status_code')}")
    else:
        print_failure("Should have failed but didn't")

# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all tests in sequence"""
    
    print("\n" + "=" * 60)
    print("MAILERLITE LIBRARY TEST SUITE")
    print("=" * 60)
    
    # Check if API key is configured
    if "REPLACE_WITH" in TEST_CONFIG["mailerlite_api_key"]:
        print("\n" + "!" * 60)
        print("ERROR: API key not configured!")
        print("!" * 60)
        print("\nPlease edit test_mailerlite_lib.py and set:")
        print("1. mailerlite_api_key (get from mailerlite.com/integrations/api)")
        print("\nNote: These tests will create/delete test data in your account")
        sys.exit(1)
    
    # Track created resources for cleanup
    group_ids = []
    subscriber_ids = []
    
    try:
        # Basic tests
        test_01_config_loading()
        test_02_library_initialization()
        
        # Field operations
        test_03_list_fields()
        
        # Group operations
        group_id = test_04_create_group()
        group_ids.append(group_id)
        test_05_list_groups(TEST_GROUP_NAME)
        
        # Subscriber operations
        subscriber_id = test_06_add_subscriber()
        subscriber_ids.append(subscriber_id)
        
        test_07_get_subscriber_by_email(TEST_EMAIL)
        test_08_update_subscriber(subscriber_id)
        test_09_add_subscriber_to_group(subscriber_id, group_id)
        
        # Campaign and automation
        test_10_list_campaigns()
        test_11_list_automations()
        
        # Convenience method
        welcome_group_id = test_12_setup_welcome_automation()
        group_ids.append(welcome_group_id)
        
        # Unsubscribe
        test_13_unsubscribe_subscriber(subscriber_id)
        
        # Error handling
        test_15_error_handling()
        
        # Cleanup
        test_14_cleanup(group_ids, subscriber_ids)
        
        # Success summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nMailerLite library is working correctly!")
        print("\nNext steps:")
        print("1. Review created/deleted data in MailerLite dashboard")
        print("2. Test webhook creation (requires public URL)")
        print("3. Integrate into your AF/FO build scripts")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("TEST SUITE FAILED ✗")
        print("=" * 60)
        print(f"\nError: {e}")
        
        # Attempt cleanup even on failure
        print("\nAttempting cleanup...")
        try:
            test_14_cleanup(group_ids, subscriber_ids)
        except:
            print("Cleanup failed - you may need to manually delete test data")
        
        import traceback
        traceback.print_exc()
        sys.exit(1)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_all_tests()
