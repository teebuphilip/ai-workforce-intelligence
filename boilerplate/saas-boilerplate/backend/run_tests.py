"""
Backend Test Runner
Run all boilerplate backend tests
"""

import pytest
import sys

def run_all_tests():
    """Run all backend boilerplate tests"""
    
    print("=" * 60)
    print("BACKEND BOILERPLATE TESTS")
    print("=" * 60)
    print()
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code

if __name__ == "__main__":
    sys.exit(run_all_tests())
