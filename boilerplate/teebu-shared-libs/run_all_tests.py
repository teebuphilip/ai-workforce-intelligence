#!/usr/bin/env python3
"""
Master Test Runner
==================

Run all library tests in sequence or individually.

Usage:
    python run_all_tests.py              # Run all tests
    python run_all_tests.py stripe       # Run only Stripe tests
    python run_all_tests.py mailerlite   # Run only MailerLite tests
    python run_all_tests.py auth0        # Run only Auth0 tests
"""

import sys
import subprocess
import os

# ============================================================
# TEST CONFIGURATION
# ============================================================

TESTS = {
    "stripe": {
        "script": "test_stripe_lib.py",
        "name": "Stripe Library",
        "description": "Payment processing tests"
    },
    "mailerlite": {
        "script": "test_mailerlite_lib.py",
        "name": "MailerLite Library",
        "description": "Email marketing tests"
    },
    "auth0": {
        "script": "test_auth0_lib.py",
        "name": "Auth0 Library",
        "description": "Authentication tests"
    },
    "git": {
        "script": "test_git_lib.py",
        "name": "Git Library",
        "description": "Git repository operations tests (local only)"
    }
}

# ============================================================
# HELPERS
# ============================================================

def print_header(message):
    print("\n" + "=" * 70)
    print(message)
    print("=" * 70 + "\n")

def print_separator():
    print("\n" + "-" * 70 + "\n")

def run_test(test_key):
    """Run a single test suite"""
    test_info = TESTS[test_key]
    
    print_header(f"Running {test_info['name']} Tests")
    print(f"Description: {test_info['description']}")
    print(f"Script: {test_info['script']}\n")
    
    # Check if test script exists
    if not os.path.exists(test_info['script']):
        print(f"✗ ERROR: Test script not found: {test_info['script']}")
        return False
    
    # Run the test
    try:
        result = subprocess.run(
            ["python3", test_info['script']],
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n✓ {test_info['name']} tests PASSED")
            return True
        else:
            print(f"\n✗ {test_info['name']} tests FAILED (exit code: {result.returncode})")
            return False
    
    except Exception as e:
        print(f"\n✗ ERROR running {test_info['name']} tests: {e}")
        return False

def run_all_tests():
    """Run all test suites"""
    print_header("AF/FO Libraries - Master Test Suite")
    print("Running all library tests...\n")
    
    results = {}
    
    for test_key in TESTS.keys():
        success = run_test(test_key)
        results[test_key] = success
        print_separator()
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_key, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{TESTS[test_key]['name']:30s} {status}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Libraries are ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test suite(s) FAILED. Review errors above.")
        return 1

def show_usage():
    """Show usage information"""
    print("\nAF/FO Libraries - Master Test Runner")
    print("=" * 70)
    print("\nUsage:")
    print("  python run_all_tests.py              # Run all tests")
    print("  python run_all_tests.py stripe       # Run only Stripe tests")
    print("  python run_all_tests.py mailerlite   # Run only MailerLite tests")
    print("  python run_all_tests.py auth0        # Run only Auth0 tests")
    print("\nAvailable Tests:")
    
    for key, info in TESTS.items():
        print(f"  {key:15s} - {info['description']}")
    
    print("\nBefore running tests:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Configure API keys in test_*.py files")
    print("  3. Run tests (they will create/delete test data)")
    print()

# ============================================================
# MAIN
# ============================================================

def main():
    """Main entry point"""
    
    # Parse command line arguments
    if len(sys.argv) == 1:
        # No arguments - run all tests
        exit_code = run_all_tests()
        sys.exit(exit_code)
    
    elif len(sys.argv) == 2:
        test_key = sys.argv[1].lower()
        
        if test_key in ["help", "-h", "--help"]:
            show_usage()
            sys.exit(0)
        
        elif test_key in TESTS:
            # Run specific test
            success = run_test(test_key)
            sys.exit(0 if success else 1)
        
        else:
            print(f"✗ ERROR: Unknown test '{test_key}'")
            show_usage()
            sys.exit(1)
    
    else:
        print("✗ ERROR: Too many arguments")
        show_usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
