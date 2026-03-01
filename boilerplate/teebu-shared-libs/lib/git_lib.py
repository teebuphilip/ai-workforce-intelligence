"""
AF/FO Git Library
=================
Shared Git integration library for AF portfolio businesses and FO customer deployments.

Features:
- Repository initialization and cloning
- Commit, push, pull operations
- Branch management
- Tag operations
- Remote management (GitHub, GitLab, Bitbucket)
- Comprehensive debug logging with configurable levels
- Config-driven for multi-account support (AF vs FO)

Author: Teebu (via Claude)
Version: 1.0.0
Date: 2025-01-21
"""

import os
import json
import logging
import subprocess
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


# ============================================================
# LOGGING SETUP
# ============================================================

class GitLibLogger:
    """Custom logger with configurable verbosity for debugging"""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("git_lib")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler (stdout for terminal visibility)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s [GIT-LIB] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s [GIT-LIB] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def debug(self, msg: str, extra: Optional[Dict] = None):
        """Debug level logging (verbose)"""
        if extra:
            msg = f"{msg} | {json.dumps(extra, indent=2, default=str)}"
        self.logger.debug(msg)
    
    def info(self, msg: str, extra: Optional[Dict] = None):
        """Info level logging (normal operations)"""
        if extra:
            msg = f"{msg} | {json.dumps(extra, default=str)}"
        self.logger.info(msg)
    
    def error(self, msg: str, extra: Optional[Dict] = None):
        """Error level logging (failures only)"""
        if extra:
            msg = f"{msg} | {json.dumps(extra, indent=2, default=str)}"
        self.logger.error(msg)


# ============================================================
# CONFIGURATION
# ============================================================

class GitConfig:
    """Configuration container for Git operations"""
    
    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize Git configuration.
        
        Args:
            config_path: Path to JSON config file
            config_dict: Dict with config values (takes precedence over file)
        """
        if config_dict:
            self.config = config_dict
        elif config_path:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            raise ValueError("Must provide either config_path or config_dict")
        
        # Optional fields (Git works without API tokens for local operations)
        self.github_token = self.config.get('github_token')
        self.gitlab_token = self.config.get('gitlab_token')
        self.git_user_name = self.config.get('git_user_name', 'AF/FO Builder')
        self.git_user_email = self.config.get('git_user_email', 'builder@example.com')
        
        self.account_name = self.config.get('account_name', 'Unknown Account')
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_file = self.config.get('log_file')
        
        # Check for env var override on log level
        env_log_level = os.getenv('GIT_LOG_LEVEL')
        if env_log_level:
            self.log_level = env_log_level
    
    def __repr__(self):
        return f"GitConfig(account={self.account_name}, user={self.git_user_name}, log_level={self.log_level})"


# ============================================================
# MAIN LIBRARY CLASS
# ============================================================

class GitLib:
    """Main Git library interface"""
    
    def __init__(self, config: GitConfig):
        """
        Initialize Git library.
        
        Args:
            config: GitConfig instance
        """
        self.config = config
        self.logger = GitLibLogger(
            log_level=config.log_level,
            log_file=config.log_file
        )
        
        self.logger.info(f"GitLib initialized", {
            "account": config.account_name,
            "user": config.git_user_name,
            "log_level": config.log_level
        })
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _run_git_command(
        self,
        command: List[str],
        operation_name: str,
        cwd: Optional[str] = None,
        check: bool = True,
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        Run git command with error handling and logging.
        
        Args:
            command: Git command as list (e.g., ['git', 'status'])
            operation_name: Human-readable name for logging
            cwd: Working directory (repo path)
            check: Raise error on non-zero exit code
            max_retries: Number of retry attempts
        
        Returns:
            Dict with success status and output/error
        """
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                
                self.logger.debug(
                    f"{operation_name} - Attempt {attempt}/{max_retries}",
                    {"command": " ".join(command), "cwd": cwd}
                )
                
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=False,  # Handle errors manually
                    timeout=300  # 5 minute timeout
                )
                
                elapsed = time.time() - start_time
                
                if result.returncode == 0:
                    self.logger.info(
                        f"{operation_name} - SUCCESS",
                        {"attempt": attempt, "elapsed_sec": round(elapsed, 3)}
                    )
                    
                    self.logger.debug(
                        f"{operation_name} - Output",
                        {"stdout": result.stdout, "stderr": result.stderr}
                    )
                    
                    return {
                        "success": True,
                        "stdout": result.stdout.strip(),
                        "stderr": result.stderr.strip(),
                        "returncode": result.returncode,
                        "attempt": attempt,
                        "elapsed_sec": round(elapsed, 3)
                    }
                
                # Command failed
                error_data = {
                    "attempt": attempt,
                    "returncode": result.returncode,
                    "elapsed_sec": round(elapsed, 3),
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip()
                }
                
                self.logger.error(
                    f"{operation_name} - FAILED (attempt {attempt}/{max_retries})",
                    error_data
                )
                
                # If last attempt or check=True, return error
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": result.stderr.strip() or result.stdout.strip() or "Git command failed",
                        "returncode": result.returncode,
                        "stdout": result.stdout.strip(),
                        "stderr": result.stderr.strip(),
                        "attempts": attempt
                    }
                
                # Retry with backoff
                backoff = 2 ** (attempt - 1)
                self.logger.debug(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            
            except subprocess.TimeoutExpired:
                self.logger.error(f"{operation_name} - TIMEOUT (300s)")
                return {
                    "success": False,
                    "error": "Command timeout after 300 seconds",
                    "attempts": attempt
                }
            
            except Exception as e:
                self.logger.error(
                    f"{operation_name} - UNEXPECTED ERROR",
                    {"error": str(e), "type": type(e).__name__}
                )
                
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "attempts": attempt
                }
    
    # ========================================
    # REPOSITORY OPERATIONS
    # ========================================
    
    def init_repo(
        self,
        repo_path: str,
        initial_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Initialize a new Git repository.
        
        Args:
            repo_path: Path where repo should be created
            initial_branch: Name of initial branch (default: main)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Initializing repository: {repo_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(repo_path, exist_ok=True)
        
        # Initialize repo
        result = self._run_git_command(
            command=['git', 'init', '-b', initial_branch],
            operation_name=f"INIT_REPO[{repo_path}]",
            cwd=repo_path
        )
        
        if not result["success"]:
            return result
        
        # Configure user
        self._run_git_command(
            command=['git', 'config', 'user.name', self.config.git_user_name],
            operation_name="CONFIG_USER_NAME",
            cwd=repo_path
        )
        
        self._run_git_command(
            command=['git', 'config', 'user.email', self.config.git_user_email],
            operation_name="CONFIG_USER_EMAIL",
            cwd=repo_path
        )
        
        return result
    
    def clone_repo(
        self,
        repo_url: str,
        destination: str,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clone a remote repository.
        
        Args:
            repo_url: Git repository URL
            destination: Local path for cloned repo
            branch: Specific branch to clone (optional)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Cloning repository: {repo_url} -> {destination}")
        
        command = ['git', 'clone']
        
        if branch:
            command.extend(['-b', branch])
        
        command.extend([repo_url, destination])
        
        return self._run_git_command(
            command=command,
            operation_name=f"CLONE_REPO[{repo_url}]"
        )
    
    def get_status(
        self,
        repo_path: str
    ) -> Dict[str, Any]:
        """
        Get repository status.
        
        Args:
            repo_path: Path to repository
        
        Returns:
            Dict with success status and git status output
        """
        self.logger.info(f"Getting status: {repo_path}")
        
        result = self._run_git_command(
            command=['git', 'status', '--porcelain'],
            operation_name=f"STATUS[{repo_path}]",
            cwd=repo_path
        )
        
        if result["success"]:
            # Parse status
            status_lines = result["stdout"].split('\n') if result["stdout"] else []
            result["has_changes"] = len(status_lines) > 0 and status_lines[0] != ''
            result["status_lines"] = status_lines
        
        return result
    
    # ========================================
    # COMMIT OPERATIONS
    # ========================================
    
    def add_files(
        self,
        repo_path: str,
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add files to staging area.
        
        Args:
            repo_path: Path to repository
            files: List of files to add (None = add all)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Adding files: {repo_path}")
        
        if files is None or len(files) == 0:
            # Add all files
            command = ['git', 'add', '.']
        else:
            # Add specific files
            command = ['git', 'add'] + files
        
        return self._run_git_command(
            command=command,
            operation_name=f"ADD_FILES[{repo_path}]",
            cwd=repo_path
        )
    
    def commit(
        self,
        repo_path: str,
        message: str,
        allow_empty: bool = False
    ) -> Dict[str, Any]:
        """
        Commit staged changes.
        
        Args:
            repo_path: Path to repository
            message: Commit message
            allow_empty: Allow empty commits
        
        Returns:
            Dict with success status and commit hash
        """
        self.logger.info(f"Committing changes: {repo_path}")
        
        command = ['git', 'commit', '-m', message]
        
        if allow_empty:
            command.append('--allow-empty')
        
        result = self._run_git_command(
            command=command,
            operation_name=f"COMMIT[{repo_path}]",
            cwd=repo_path
        )
        
        if result["success"]:
            # Get commit hash
            hash_result = self._run_git_command(
                command=['git', 'rev-parse', 'HEAD'],
                operation_name="GET_COMMIT_HASH",
                cwd=repo_path
            )
            
            if hash_result["success"]:
                result["commit_hash"] = hash_result["stdout"]
        
        return result
    
    def add_and_commit(
        self,
        repo_path: str,
        message: str,
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Convenience method: Add and commit in one operation.
        
        Args:
            repo_path: Path to repository
            message: Commit message
            files: List of files to add (None = add all)
        
        Returns:
            Dict with success status and commit hash
        """
        self.logger.info(f"Add and commit: {repo_path}")
        
        # Add files
        add_result = self.add_files(repo_path, files)
        
        if not add_result["success"]:
            return add_result
        
        # Commit
        return self.commit(repo_path, message)
    
    # ========================================
    # BRANCH OPERATIONS
    # ========================================
    
    def create_branch(
        self,
        repo_path: str,
        branch_name: str,
        checkout: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            repo_path: Path to repository
            branch_name: Name of new branch
            checkout: Switch to new branch after creation
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Creating branch: {branch_name} in {repo_path}")
        
        if checkout:
            command = ['git', 'checkout', '-b', branch_name]
        else:
            command = ['git', 'branch', branch_name]
        
        return self._run_git_command(
            command=command,
            operation_name=f"CREATE_BRANCH[{branch_name}]",
            cwd=repo_path
        )
    
    def checkout_branch(
        self,
        repo_path: str,
        branch_name: str
    ) -> Dict[str, Any]:
        """
        Switch to a branch.
        
        Args:
            repo_path: Path to repository
            branch_name: Name of branch to switch to
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Checking out branch: {branch_name} in {repo_path}")
        
        return self._run_git_command(
            command=['git', 'checkout', branch_name],
            operation_name=f"CHECKOUT_BRANCH[{branch_name}]",
            cwd=repo_path
        )
    
    def list_branches(
        self,
        repo_path: str,
        remote: bool = False
    ) -> Dict[str, Any]:
        """
        List branches.
        
        Args:
            repo_path: Path to repository
            remote: List remote branches instead of local
        
        Returns:
            Dict with success status and list of branches
        """
        self.logger.info(f"Listing branches: {repo_path}")
        
        command = ['git', 'branch']
        
        if remote:
            command.append('-r')
        
        result = self._run_git_command(
            command=command,
            operation_name=f"LIST_BRANCHES[{repo_path}]",
            cwd=repo_path
        )
        
        if result["success"]:
            # Parse branch list
            branches = []
            for line in result["stdout"].split('\n'):
                line = line.strip()
                if line:
                    # Remove * prefix from current branch
                    branch = line.lstrip('* ').strip()
                    branches.append(branch)
            
            result["branches"] = branches
        
        return result
    
    def delete_branch(
        self,
        repo_path: str,
        branch_name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a branch.
        
        Args:
            repo_path: Path to repository
            branch_name: Name of branch to delete
            force: Force deletion even if not merged
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Deleting branch: {branch_name} in {repo_path}")
        
        flag = '-D' if force else '-d'
        
        return self._run_git_command(
            command=['git', 'branch', flag, branch_name],
            operation_name=f"DELETE_BRANCH[{branch_name}]",
            cwd=repo_path
        )
    
    # ========================================
    # TAG OPERATIONS
    # ========================================
    
    def create_tag(
        self,
        repo_path: str,
        tag_name: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a tag.
        
        Args:
            repo_path: Path to repository
            tag_name: Name of tag
            message: Tag message (creates annotated tag)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Creating tag: {tag_name} in {repo_path}")
        
        if message:
            command = ['git', 'tag', '-a', tag_name, '-m', message]
        else:
            command = ['git', 'tag', tag_name]
        
        return self._run_git_command(
            command=command,
            operation_name=f"CREATE_TAG[{tag_name}]",
            cwd=repo_path
        )
    
    def list_tags(
        self,
        repo_path: str
    ) -> Dict[str, Any]:
        """
        List all tags.
        
        Args:
            repo_path: Path to repository
        
        Returns:
            Dict with success status and list of tags
        """
        self.logger.info(f"Listing tags: {repo_path}")
        
        result = self._run_git_command(
            command=['git', 'tag'],
            operation_name=f"LIST_TAGS[{repo_path}]",
            cwd=repo_path
        )
        
        if result["success"]:
            tags = result["stdout"].split('\n') if result["stdout"] else []
            result["tags"] = [t.strip() for t in tags if t.strip()]
        
        return result
    
    def delete_tag(
        self,
        repo_path: str,
        tag_name: str
    ) -> Dict[str, Any]:
        """
        Delete a tag.
        
        Args:
            repo_path: Path to repository
            tag_name: Name of tag to delete
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Deleting tag: {tag_name} in {repo_path}")
        
        return self._run_git_command(
            command=['git', 'tag', '-d', tag_name],
            operation_name=f"DELETE_TAG[{tag_name}]",
            cwd=repo_path
        )
    
    # ========================================
    # REMOTE OPERATIONS
    # ========================================
    
    def add_remote(
        self,
        repo_path: str,
        name: str,
        url: str
    ) -> Dict[str, Any]:
        """
        Add a remote repository.
        
        Args:
            repo_path: Path to repository
            name: Remote name (e.g., "origin")
            url: Remote URL
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Adding remote: {name} -> {url} in {repo_path}")
        
        # If using GitHub/GitLab token, inject into URL
        if 'github.com' in url and self.config.github_token:
            url = url.replace('https://', f'https://{self.config.github_token}@')
        elif 'gitlab.com' in url and self.config.gitlab_token:
            url = url.replace('https://', f'https://oauth2:{self.config.gitlab_token}@')
        
        return self._run_git_command(
            command=['git', 'remote', 'add', name, url],
            operation_name=f"ADD_REMOTE[{name}]",
            cwd=repo_path
        )
    
    def list_remotes(
        self,
        repo_path: str
    ) -> Dict[str, Any]:
        """
        List remote repositories.
        
        Args:
            repo_path: Path to repository
        
        Returns:
            Dict with success status and list of remotes
        """
        self.logger.info(f"Listing remotes: {repo_path}")
        
        result = self._run_git_command(
            command=['git', 'remote', '-v'],
            operation_name=f"LIST_REMOTES[{repo_path}]",
            cwd=repo_path
        )
        
        if result["success"]:
            remotes = {}
            for line in result["stdout"].split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        url = parts[1]
                        if name not in remotes:
                            remotes[name] = url
            
            result["remotes"] = remotes
        
        return result
    
    def push(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: Optional[str] = None,
        tags: bool = False,
        set_upstream: bool = False
    ) -> Dict[str, Any]:
        """
        Push commits to remote.
        
        Args:
            repo_path: Path to repository
            remote: Remote name (default: origin)
            branch: Branch to push (None = current branch)
            tags: Push tags as well
            set_upstream: Set upstream tracking
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Pushing to {remote}: {repo_path}")
        
        command = ['git', 'push']
        
        if set_upstream:
            command.append('-u')
        
        command.append(remote)
        
        if branch:
            command.append(branch)
        
        if tags:
            command.append('--tags')
        
        return self._run_git_command(
            command=command,
            operation_name=f"PUSH[{remote}]",
            cwd=repo_path,
            max_retries=3  # Network operations may fail, retry
        )
    
    def pull(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pull changes from remote.
        
        Args:
            repo_path: Path to repository
            remote: Remote name (default: origin)
            branch: Branch to pull (None = current branch)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Pulling from {remote}: {repo_path}")
        
        command = ['git', 'pull', remote]
        
        if branch:
            command.append(branch)
        
        return self._run_git_command(
            command=command,
            operation_name=f"PULL[{remote}]",
            cwd=repo_path,
            max_retries=3  # Network operations may fail, retry
        )
    
    # ========================================
    # CONVENIENCE METHODS
    # ========================================
    
    def setup_new_repo(
        self,
        repo_path: str,
        remote_url: Optional[str] = None,
        initial_files: Optional[Dict[str, str]] = None,
        initial_commit_message: str = "Initial commit"
    ) -> Dict[str, Any]:
        """
        Convenience method: Set up a new repository with initial commit.
        
        Args:
            repo_path: Path for new repository
            remote_url: Optional remote URL to add
            initial_files: Dict of {filename: content} to create
            initial_commit_message: Message for initial commit
        
        Returns:
            Dict with success status and setup details
        """
        self.logger.info(f"Setting up new repository: {repo_path}")
        
        result = {
            "success": True,
            "repo_path": repo_path,
            "steps": [],
            "errors": []
        }
        
        # 1. Initialize repo
        init_result = self.init_repo(repo_path)
        result["steps"].append({"step": "init", "success": init_result["success"]})
        
        if not init_result["success"]:
            result["success"] = False
            result["errors"].append(f"Init failed: {init_result.get('error')}")
            return result
        
        # 2. Create initial files
        if initial_files:
            for filename, content in initial_files.items():
                filepath = os.path.join(repo_path, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            result["steps"].append({"step": "create_files", "success": True, "count": len(initial_files)})
        
        # 3. Initial commit
        commit_result = self.add_and_commit(repo_path, initial_commit_message)
        result["steps"].append({"step": "commit", "success": commit_result["success"]})
        
        if commit_result["success"]:
            result["commit_hash"] = commit_result.get("commit_hash")
        
        # 4. Add remote (if provided)
        if remote_url:
            remote_result = self.add_remote(repo_path, "origin", remote_url)
            result["steps"].append({"step": "add_remote", "success": remote_result["success"]})
            
            if remote_result["success"]:
                result["remote_url"] = remote_url
        
        self.logger.info(f"Repository setup complete: {repo_path}")
        
        return result


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_git_lib(config_path: str) -> GitLib:
    """
    Convenience function to load GitLib from config file.
    
    Args:
        config_path: Path to JSON config file
    
    Returns:
        Initialized GitLib instance
    """
    config = GitConfig(config_path=config_path)
    return GitLib(config)


def load_git_lib_from_dict(config_dict: Dict) -> GitLib:
    """
    Convenience function to load GitLib from config dict.
    
    Args:
        config_dict: Config dictionary
    
    Returns:
        Initialized GitLib instance
    """
    config = GitConfig(config_dict=config_dict)
    return GitLib(config)
