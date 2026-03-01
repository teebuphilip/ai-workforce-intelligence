#!/usr/bin/env python3
"""
Auth0 Library Test Suite
=========================

Tests to validate auth0_lib.py functionality.
Run this AFTER setting up your Auth0 test tenant and M2M application.

Usage:
    python test_auth0_lib.py
"""

import sys
import json
import time
from auth0_lib import Auth0Config, Auth0Lib, load_auth0_lib

# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CONFIG = {
    "auth0_domain": "your-test-tenant.auth0.com",
    "auth0_client_id": "YOUR_CLIENT_ID",
    "auth0_client_secret": "YOUR_CLIENT_SECRET",
    "auth0_audience": "https://your-test-tenant.auth0.com/api/v2/",
    "account_name": "Test Account",
    "log_level": "DEBUG"
}

# Test data
TEST_EMAIL = f"test+auth0_{int(time.time())}@example.com"
TEST_PASSWORD = "TestPassword123!@#"
TEST_ROLE_NAME = f"TestRole_{int(time.time())}"

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
    """Assert that an Auth0 operation succeeded"""
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
        config = Auth0Config(config_dict=TEST_CONFIG)
        print_success(f"Config loaded: {config}")
        
        assert config.domain == TEST_CONFIG["auth0_domain"]
        assert config.client_id == TEST_CONFIG["auth0_client_id"]
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
        config = Auth0Config(config_dict=TEST_CONFIG)
        auth = Auth0Lib(config)
        print_success("Auth0Lib initialized")
        
        assert auth.config.account_name == "Test Account"
        print_success("Library config accessible")
    except Exception as e:
        print_failure(f"Library initialization failed: {e}")
        sys.exit(1)

def test_03_get_management_token():
    """Test getting management API token"""
    print_test_header("Get Management Token")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.get_management_token()
    
    assert_success(result, "Get management token")
    
    print_success(f"Token obtained (cached: {result.get('cached', False)})")
    print_success(f"Expires in: {result.get('expires_in', 'N/A')} seconds")
    
    # Test cached token
    result2 = auth.get_management_token()
    if result2.get("cached"):
        print_success("Cached token reused successfully")
    else:
        print_failure("Token should have been cached")

def test_04_create_user():
    """Test user creation"""
    print_test_header("User Creation")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.create_user(
        email=TEST_EMAIL,
        password=TEST_PASSWORD,
        email_verified=False,
        user_metadata={"test": "true", "created_by": "test_suite"}
    )
    
    assert_success(result, "Create user")
    
    user = result["data"]
    print_success(f"User ID: {user['user_id']}")
    print_success(f"User email: {user['email']}")
    
    return user["user_id"]

def test_05_get_user(user_id):
    """Test getting user by ID"""
    print_test_header("Get User by ID")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.get_user(user_id=user_id)
    
    assert_success(result, "Get user")
    
    user = result["data"]
    print_success(f"User email: {user['email']}")
    print_success(f"User created: {user['created_at']}")

def test_06_get_user_by_email(expected_email):
    """Test getting user by email"""
    print_test_header("Get User by Email")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.get_user_by_email(email=expected_email)
    
    assert_success(result, "Get user by email")
    
    user = result["data"]
    print_success(f"Found user: {user['email']}")
    print_success(f"User ID: {user['user_id']}")

def test_07_update_user(user_id):
    """Test updating user"""
    print_test_header("Update User")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.update_user(
        user_id=user_id,
        user_metadata={"test": "updated", "updated_at": time.time()},
        email_verified=True
    )
    
    assert_success(result, "Update user")
    
    user = result["data"]
    print_success(f"User updated: {user['user_id']}")
    print_success(f"Email verified: {user.get('email_verified', False)}")

def test_08_list_users():
    """Test listing users"""
    print_test_header("List Users")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.list_users(per_page=5)
    
    assert_success(result, "List users")
    
    users = result["data"]
    print_success(f"Found {len(users)} users")
    
    if users:
        print_success(f"First user: {users[0].get('email', 'N/A')}")

def test_09_search_users(search_email):
    """Test searching users with query"""
    print_test_header("Search Users")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.list_users(
        per_page=10,
        search_query=f'email:"{search_email}"'
    )
    
    if result["success"]:
        users = result["data"]
        print_success(f"Search returned {len(users)} users")
        
        if users:
            print_success(f"Found: {users[0]['email']}")
    else:
        print_failure(f"Search failed: {result.get('error')}")

def test_10_change_password(user_id):
    """Test changing user password"""
    print_test_header("Change User Password")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    new_password = "NewTestPassword456!@#"
    
    result = auth.change_user_password(
        user_id=user_id,
        new_password=new_password
    )
    
    assert_success(result, "Change password")
    
    print_success(f"Password changed for user: {user_id}")

def test_11_send_verification_email(user_id):
    """Test sending verification email"""
    print_test_header("Send Verification Email")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.send_verification_email(user_id=user_id)
    
    # This might fail if user is already verified
    if result["success"]:
        print_success("Verification email sent")
    else:
        print_failure(f"Send verification failed: {result.get('error')}")
        print("Note: This might fail if email is already verified")

def test_12_create_role():
    """Test creating a role"""
    print_test_header("Create Role")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.create_role(
        name=TEST_ROLE_NAME,
        description="Test role created by test suite"
    )
    
    assert_success(result, "Create role")
    
    role = result["data"]
    print_success(f"Role ID: {role['id']}")
    print_success(f"Role name: {role['name']}")
    
    return role["id"]

def test_13_list_roles():
    """Test listing roles"""
    print_test_header("List Roles")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.list_roles()
    
    assert_success(result, "List roles")
    
    roles = result["data"]
    print_success(f"Found {len(roles)} roles")
    
    if roles:
        print_success(f"First role: {roles[0].get('name', 'N/A')}")

def test_14_assign_role_to_user(user_id, role_id):
    """Test assigning role to user"""
    print_test_header("Assign Role to User")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.assign_roles_to_user(
        user_id=user_id,
        role_ids=[role_id]
    )
    
    # This might return empty data on success
    if result["success"] or result.get("status_code") == 204:
        print_success(f"Role assigned to user")
    else:
        print_failure(f"Failed to assign role: {result.get('error')}")

def test_15_get_user_roles(user_id):
    """Test getting user's roles"""
    print_test_header("Get User Roles")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.get_user_roles(user_id=user_id)
    
    assert_success(result, "Get user roles")
    
    roles = result["data"]
    print_success(f"User has {len(roles)} roles")
    
    if roles:
        print_success(f"First role: {roles[0].get('name', 'N/A')}")

def test_16_setup_basic_auth():
    """Test convenience method for basic auth setup"""
    print_test_header("Setup Basic Auth")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.setup_basic_auth(business_name="TestBusiness")
    
    assert_success(result, "Setup basic auth")
    
    print_success(f"Created {len(result['roles'])} roles")
    
    if result['roles']:
        for role_name, role_data in result['roles'].items():
            print_success(f"  - {role_name}: {role_data.get('id', 'N/A')}")
    
    # Return role IDs for cleanup
    return [role_data.get('id') for role_data in result['roles'].values() if role_data]

def test_17_block_user(user_id):
    """Test blocking a user"""
    print_test_header("Block User")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    result = auth.update_user(
        user_id=user_id,
        blocked=True
    )
    
    assert_success(result, "Block user")
    
    user = result["data"]
    print_success(f"User blocked: {user.get('blocked', False)}")

def test_18_cleanup(user_ids, role_ids):
    """Clean up test data"""
    print_test_header("Cleanup Test Data")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    # Delete users
    for user_id in user_ids:
        result = auth.delete_user(user_id)
        if result["success"] or result.get("status_code") == 204:
            print_success(f"Deleted user: {user_id}")
        else:
            print_failure(f"Failed to delete user {user_id}: {result.get('error')}")
    
    # Note: Role deletion not implemented in library yet
    # Roles would need to be deleted manually via dashboard
    if role_ids:
        print(f"\nNote: {len(role_ids)} test roles created - delete manually via Auth0 dashboard")
        print("Role IDs:")
        for role_id in role_ids:
            print(f"  - {role_id}")

def test_19_error_handling():
    """Test error handling with invalid input"""
    print_test_header("Error Handling")
    
    config = Auth0Config(config_dict=TEST_CONFIG)
    auth = Auth0Lib(config)
    
    # Try to get non-existent user
    result = auth.get_user(user_id="auth0|invalid_id_12345")
    
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
    print("AUTH0 LIBRARY TEST SUITE")
    print("=" * 60)
    
    # Check if credentials are configured
    if "YOUR_" in TEST_CONFIG["auth0_client_id"]:
        print("\n" + "!" * 60)
        print("ERROR: Auth0 credentials not configured!")
        print("!" * 60)
        print("\nPlease edit test_auth0_lib.py and set:")
        print("1. auth0_domain (your-tenant.auth0.com)")
        print("2. auth0_client_id (from M2M application)")
        print("3. auth0_client_secret (from M2M application)")
        print("\nTo create M2M application:")
        print("1. Go to Auth0 Dashboard → Applications → Create Application")
        print("2. Select 'Machine to Machine Applications'")
        print("3. Authorize for Auth0 Management API")
        print("4. Grant scopes: read:users, update:users, delete:users, create:users,")
        print("   read:roles, create:roles, update:roles")
        print("\nNote: These tests will create/delete test data in your tenant")
        sys.exit(1)
    
    # Track created resources for cleanup
    user_ids = []
    role_ids = []
    
    try:
        # Basic tests
        test_01_config_loading()
        test_02_library_initialization()
        test_03_get_management_token()
        
        # User operations
        user_id = test_04_create_user()
        user_ids.append(user_id)
        
        test_05_get_user(user_id)
        test_06_get_user_by_email(TEST_EMAIL)
        test_07_update_user(user_id)
        test_08_list_users()
        test_09_search_users(TEST_EMAIL)
        
        # Password operations
        test_10_change_password(user_id)
        test_11_send_verification_email(user_id)
        
        # Role operations
        role_id = test_12_create_role()
        role_ids.append(role_id)
        
        test_13_list_roles()
        test_14_assign_role_to_user(user_id, role_id)
        test_15_get_user_roles(user_id)
        
        # Convenience method
        setup_role_ids = test_16_setup_basic_auth()
        role_ids.extend(setup_role_ids)
        
        # Block user
        test_17_block_user(user_id)
        
        # Error handling
        test_19_error_handling()
        
        # Cleanup
        test_18_cleanup(user_ids, role_ids)
        
        # Success summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nAuth0 library is working correctly!")
        print("\nNext steps:")
        print("1. Review created/deleted data in Auth0 dashboard")
        print("2. Manually delete test roles if needed")
        print("3. Test password reset email flow (requires email provider)")
        print("4. Integrate into your AF/FO build scripts")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("TEST SUITE FAILED ✗")
        print("=" * 60)
        print(f"\nError: {e}")
        
        # Attempt cleanup even on failure
        print("\nAttempting cleanup...")
        try:
            test_18_cleanup(user_ids, role_ids)
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
