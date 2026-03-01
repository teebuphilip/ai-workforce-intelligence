#!/usr/bin/env python3
"""
Git Library Test Suite
=======================

Tests to validate git_lib.py functionality.
These tests use local Git operations (no remote required).

Usage:
    python test_git_lib.py
"""

import sys
import json
import os
import shutil
import tempfile
from git_lib import GitConfig, GitLib, load_git_lib

# ============================================================
# TEST CONFIGURATION
# ============================================================

TEST_CONFIG = {
    "git_user_name": "Test User",
    "git_user_email": "test@example.com",
    "account_name": "Test Account",
    "log_level": "DEBUG"
}

# Test directory (will be created in temp)
TEST_DIR = None

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
    """Assert that a Git operation succeeded"""
    if not result.get("success"):
        print_failure(f"{operation_name} failed")
        print(f"Error: {result.get('error')}")
        print(f"Stderr: {result.get('stderr')}")
        print(f"Stdout: {result.get('stdout')}")
        sys.exit(1)
    print_success(f"{operation_name} succeeded")

def setup_test_dir():
    """Create temporary test directory"""
    global TEST_DIR
    TEST_DIR = tempfile.mkdtemp(prefix="git_lib_test_")
    print(f"Test directory: {TEST_DIR}")
    return TEST_DIR

def cleanup_test_dir():
    """Remove test directory"""
    global TEST_DIR
    if TEST_DIR and os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
        print(f"\nCleaned up test directory: {TEST_DIR}")

# ============================================================
# TESTS
# ============================================================

def test_01_config_loading():
    """Test config loading from dict"""
    print_test_header("Config Loading")
    
    try:
        config = GitConfig(config_dict=TEST_CONFIG)
        print_success(f"Config loaded: {config}")
        
        assert config.git_user_name == TEST_CONFIG["git_user_name"]
        assert config.git_user_email == TEST_CONFIG["git_user_email"]
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
        config = GitConfig(config_dict=TEST_CONFIG)
        git = GitLib(config)
        print_success("GitLib initialized")
        
        assert git.config.account_name == "Test Account"
        print_success("Library config accessible")
    except Exception as e:
        print_failure(f"Library initialization failed: {e}")
        sys.exit(1)

def test_03_init_repo():
    """Test repository initialization"""
    print_test_header("Repository Initialization")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    repo_path = os.path.join(TEST_DIR, "test_repo")
    
    result = git.init_repo(repo_path=repo_path, initial_branch="main")
    
    assert_success(result, "Init repository")
    
    # Verify .git directory exists
    assert os.path.exists(os.path.join(repo_path, ".git"))
    print_success(f"Repository created: {repo_path}")
    
    return repo_path

def test_04_get_status(repo_path):
    """Test getting repository status"""
    print_test_header("Get Repository Status")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.get_status(repo_path=repo_path)
    
    assert_success(result, "Get status")
    
    print_success(f"Has changes: {result.get('has_changes', False)}")

def test_05_create_file_and_add(repo_path):
    """Test creating file and adding to staging"""
    print_test_header("Create File and Add to Staging")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    # Create a test file
    test_file = os.path.join(repo_path, "README.md")
    with open(test_file, 'w') as f:
        f.write("# Test Repository\n\nThis is a test.")
    
    print_success(f"Created file: README.md")
    
    # Add file to staging
    result = git.add_files(repo_path=repo_path)
    
    assert_success(result, "Add files")

def test_06_commit(repo_path):
    """Test committing changes"""
    print_test_header("Commit Changes")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.commit(
        repo_path=repo_path,
        message="Initial commit: Add README"
    )
    
    assert_success(result, "Commit changes")
    
    if result.get("commit_hash"):
        print_success(f"Commit hash: {result['commit_hash']}")

def test_07_add_and_commit(repo_path):
    """Test convenience method add_and_commit"""
    print_test_header("Add and Commit (Convenience)")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    # Create another file
    test_file = os.path.join(repo_path, "test.txt")
    with open(test_file, 'w') as f:
        f.write("Test content")
    
    result = git.add_and_commit(
        repo_path=repo_path,
        message="Add test.txt"
    )
    
    assert_success(result, "Add and commit")
    
    if result.get("commit_hash"):
        print_success(f"Commit hash: {result['commit_hash']}")

def test_08_create_branch(repo_path):
    """Test creating a branch"""
    print_test_header("Create Branch")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.create_branch(
        repo_path=repo_path,
        branch_name="feature/test-feature",
        checkout=True
    )
    
    assert_success(result, "Create branch")
    
    print_success("Branch created: feature/test-feature")

def test_09_list_branches(repo_path):
    """Test listing branches"""
    print_test_header("List Branches")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.list_branches(repo_path=repo_path)
    
    assert_success(result, "List branches")
    
    branches = result.get("branches", [])
    print_success(f"Found {len(branches)} branches")
    
    for branch in branches:
        print_success(f"  - {branch}")

def test_10_checkout_branch(repo_path):
    """Test checking out a branch"""
    print_test_header("Checkout Branch")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.checkout_branch(
        repo_path=repo_path,
        branch_name="main"
    )
    
    assert_success(result, "Checkout branch")
    
    print_success("Switched to main branch")

def test_11_create_tag(repo_path):
    """Test creating a tag"""
    print_test_header("Create Tag")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.create_tag(
        repo_path=repo_path,
        tag_name="v1.0.0",
        message="Release version 1.0.0"
    )
    
    assert_success(result, "Create tag")
    
    print_success("Tag created: v1.0.0")

def test_12_list_tags(repo_path):
    """Test listing tags"""
    print_test_header("List Tags")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.list_tags(repo_path=repo_path)
    
    assert_success(result, "List tags")
    
    tags = result.get("tags", [])
    print_success(f"Found {len(tags)} tags")
    
    for tag in tags:
        print_success(f"  - {tag}")

def test_13_delete_tag(repo_path):
    """Test deleting a tag"""
    print_test_header("Delete Tag")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    # Create a tag to delete
    git.create_tag(repo_path=repo_path, tag_name="v0.0.1")
    
    # Delete it
    result = git.delete_tag(
        repo_path=repo_path,
        tag_name="v0.0.1"
    )
    
    assert_success(result, "Delete tag")
    
    print_success("Tag deleted: v0.0.1")

def test_14_delete_branch(repo_path):
    """Test deleting a branch"""
    print_test_header("Delete Branch")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    # Make sure we're not on the branch we want to delete
    git.checkout_branch(repo_path=repo_path, branch_name="main")
    
    # Delete feature branch
    result = git.delete_branch(
        repo_path=repo_path,
        branch_name="feature/test-feature",
        force=True
    )
    
    assert_success(result, "Delete branch")
    
    print_success("Branch deleted: feature/test-feature")

def test_15_setup_new_repo():
    """Test convenience method for complete repo setup"""
    print_test_header("Setup New Repository (Convenience)")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    new_repo_path = os.path.join(TEST_DIR, "new_repo")
    
    initial_files = {
        "README.md": "# New Repository\n\nCreated via setup_new_repo",
        "src/main.py": "print('Hello, World!')",
        ".gitignore": "*.pyc\n__pycache__/\n"
    }
    
    result = git.setup_new_repo(
        repo_path=new_repo_path,
        initial_files=initial_files,
        initial_commit_message="Initial setup via convenience method"
    )
    
    assert_success(result, "Setup new repository")
    
    print_success(f"Steps completed: {len(result['steps'])}")
    
    for step in result["steps"]:
        status = "✓" if step["success"] else "✗"
        print_success(f"  {status} {step['step']}")
    
    if result.get("commit_hash"):
        print_success(f"Initial commit: {result['commit_hash']}")

def test_16_clone_repo(repo_path):
    """Test cloning a repository"""
    print_test_header("Clone Repository")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    clone_path = os.path.join(TEST_DIR, "cloned_repo")
    
    # Clone the test repo we created earlier
    result = git.clone_repo(
        repo_url=repo_path,  # Local path works as URL
        destination=clone_path
    )
    
    assert_success(result, "Clone repository")
    
    # Verify cloned repo exists
    assert os.path.exists(os.path.join(clone_path, ".git"))
    print_success(f"Repository cloned: {clone_path}")

def test_17_add_remote(repo_path):
    """Test adding a remote"""
    print_test_header("Add Remote")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    # Add a fake remote (won't actually connect)
    result = git.add_remote(
        repo_path=repo_path,
        name="origin",
        url="https://github.com/test/test-repo.git"
    )
    
    # This might fail if remote already exists, that's ok
    if result["success"]:
        print_success("Remote added: origin")
    else:
        # Try to list instead
        list_result = git.list_remotes(repo_path=repo_path)
        if list_result["success"]:
            print_success(f"Remotes: {list_result.get('remotes', {})}")

def test_18_list_remotes(repo_path):
    """Test listing remotes"""
    print_test_header("List Remotes")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    result = git.list_remotes(repo_path=repo_path)
    
    # This might return empty if no remotes
    if result["success"]:
        remotes = result.get("remotes", {})
        print_success(f"Found {len(remotes)} remotes")
        
        for name, url in remotes.items():
            print_success(f"  {name}: {url}")
    else:
        print_success("No remotes configured (this is ok)")

def test_19_error_handling():
    """Test error handling with invalid operations"""
    print_test_header("Error Handling")
    
    config = GitConfig(config_dict=TEST_CONFIG)
    git = GitLib(config)
    
    # Try to get status of non-existent repo
    result = git.get_status(repo_path="/nonexistent/path")
    
    # This should fail gracefully
    if not result["success"]:
        print_success("Error handled correctly")
        print_success(f"Error message: {result['error']}")
    else:
        print_failure("Should have failed but didn't")

# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all tests in sequence"""
    
    print("\n" + "=" * 60)
    print("GIT LIBRARY TEST SUITE")
    print("=" * 60)
    print("\nNote: These tests use local Git operations only.")
    print("No remote repository or GitHub token required.\n")
    
    # Set up test directory
    setup_test_dir()
    
    try:
        # Basic tests
        test_01_config_loading()
        test_02_library_initialization()
        
        # Repository operations
        repo_path = test_03_init_repo()
        test_04_get_status(repo_path)
        
        # File and commit operations
        test_05_create_file_and_add(repo_path)
        test_06_commit(repo_path)
        test_07_add_and_commit(repo_path)
        
        # Branch operations
        test_08_create_branch(repo_path)
        test_09_list_branches(repo_path)
        test_10_checkout_branch(repo_path)
        test_14_delete_branch(repo_path)
        
        # Tag operations
        test_11_create_tag(repo_path)
        test_12_list_tags(repo_path)
        test_13_delete_tag(repo_path)
        
        # Convenience method
        test_15_setup_new_repo()
        
        # Clone operation
        test_16_clone_repo(repo_path)
        
        # Remote operations (local only)
        test_17_add_remote(repo_path)
        test_18_list_remotes(repo_path)
        
        # Error handling
        test_19_error_handling()
        
        # Success summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nGit library is working correctly!")
        print("\nNext steps:")
        print("1. Configure GitHub/GitLab tokens for remote operations")
        print("2. Test push/pull with actual remote repositories")
        print("3. Integrate into your AF/FO build scripts")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("TEST SUITE FAILED ✗")
        print("=" * 60)
        print(f"\nError: {e}")
        
        import traceback
        traceback.print_exc()
        
        return 1
    
    finally:
        # Always cleanup
        cleanup_test_dir()
    
    return 0

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
