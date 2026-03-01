"""
AF/FO Auth0 Library
===================
Shared Auth0 integration library for AF portfolio businesses and FO customer deployments.

Features:
- Manage users (create, update, delete, search)
- Manage roles and permissions
- Generate auth tokens
- Password reset flows
- Email verification
- User metadata management
- Comprehensive debug logging with configurable levels
- Config-driven for multi-account support (AF vs FO)

Author: Teebu (via Claude)
Version: 1.0.0
Date: 2025-01-21
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime


# ============================================================
# LOGGING SETUP
# ============================================================

class Auth0LibLogger:
    """Custom logger with configurable verbosity for debugging"""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("auth0_lib")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler (stdout for terminal visibility)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s [AUTH0-LIB] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s [AUTH0-LIB] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def debug(self, msg: str, extra: Optional[Dict] = None):
        """Debug level logging (verbose)"""
        if extra:
            # Redact sensitive fields
            safe_extra = self._redact_sensitive(extra)
            msg = f"{msg} | {json.dumps(safe_extra, indent=2, default=str)}"
        self.logger.debug(msg)
    
    def info(self, msg: str, extra: Optional[Dict] = None):
        """Info level logging (normal operations)"""
        if extra:
            safe_extra = self._redact_sensitive(extra)
            msg = f"{msg} | {json.dumps(safe_extra, default=str)}"
        self.logger.info(msg)
    
    def error(self, msg: str, extra: Optional[Dict] = None):
        """Error level logging (failures only)"""
        if extra:
            safe_extra = self._redact_sensitive(extra)
            msg = f"{msg} | {json.dumps(safe_extra, indent=2, default=str)}"
        self.logger.error(msg)
    
    def _redact_sensitive(self, data: Any) -> Any:
        """Redact sensitive fields from logs"""
        if isinstance(data, dict):
            redacted = {}
            sensitive_keys = ['password', 'client_secret', 'access_token', 'id_token', 'refresh_token']
            for key, value in data.items():
                if any(s in key.lower() for s in sensitive_keys):
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = self._redact_sensitive(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_sensitive(item) for item in data]
        else:
            return data


# ============================================================
# CONFIGURATION
# ============================================================

class Auth0Config:
    """Configuration container for Auth0 operations"""
    
    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize Auth0 configuration.
        
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
        
        # Required fields
        self.domain = self.config.get('auth0_domain')
        self.client_id = self.config.get('auth0_client_id')
        self.client_secret = self.config.get('auth0_client_secret')
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("auth0_domain, auth0_client_id, and auth0_client_secret are required")
        
        # Optional fields
        self.audience = self.config.get('auth0_audience')  # API identifier
        self.account_name = self.config.get('account_name', 'Unknown Account')
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_file = self.config.get('log_file')
        
        # Check for env var override on log level
        env_log_level = os.getenv('AUTH0_LOG_LEVEL')
        if env_log_level:
            self.log_level = env_log_level
        
        # Management API token (cached)
        self._management_token = None
        self._token_expires_at = 0
    
    def __repr__(self):
        return f"Auth0Config(domain={self.domain}, account={self.account_name}, log_level={self.log_level})"


# ============================================================
# MAIN LIBRARY CLASS
# ============================================================

class Auth0Lib:
    """Main Auth0 library interface"""
    
    def __init__(self, config: Auth0Config):
        """
        Initialize Auth0 library.
        
        Args:
            config: Auth0Config instance
        """
        self.config = config
        self.logger = Auth0LibLogger(
            log_level=config.log_level,
            log_file=config.log_file
        )
        
        self.base_url = f"https://{config.domain}"
        self.api_url = f"{self.base_url}/api/v2"
        
        self.logger.info(f"Auth0Lib initialized", {
            "domain": config.domain,
            "account": config.account_name,
            "log_level": config.log_level
        })
    
    # ========================================
    # AUTHENTICATION / TOKEN MANAGEMENT
    # ========================================
    
    def get_management_token(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get Management API access token (cached).
        
        Args:
            force_refresh: Force token refresh even if cached
        
        Returns:
            Dict with success status and access_token
        """
        # Check if cached token is still valid
        if not force_refresh and self.config._management_token:
            if time.time() < self.config._token_expires_at:
                self.logger.debug("Using cached management token")
                return {
                    "success": True,
                    "access_token": self.config._management_token,
                    "cached": True
                }
        
        self.logger.info("Fetching new management token")
        
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                json={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "audience": f"{self.base_url}/api/v2/",
                    "grant_type": "client_credentials"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.config._management_token = data["access_token"]
                # Set expiry to 90% of actual expiry (safety margin)
                self.config._token_expires_at = time.time() + (data["expires_in"] * 0.9)
                
                self.logger.info("Management token fetched successfully")
                
                return {
                    "success": True,
                    "access_token": data["access_token"],
                    "expires_in": data["expires_in"],
                    "cached": False
                }
            else:
                error_data = response.json() if response.content else {}
                self.logger.error("Failed to fetch management token", {
                    "status": response.status_code,
                    "error": error_data
                })
                
                return {
                    "success": False,
                    "error": error_data.get("error_description", "Token fetch failed"),
                    "status_code": response.status_code
                }
        
        except Exception as e:
            self.logger.error(f"Token fetch error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        operation_name: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Auth0 Management API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (e.g., "/users")
            operation_name: Human-readable name for logging
            data: JSON data for request body
            params: Query parameters
            max_retries: Maximum retry attempts
        
        Returns:
            Dict with success status and data/error
        """
        # Get management token
        token_result = self.get_management_token()
        if not token_result["success"]:
            return token_result
        
        access_token = token_result["access_token"]
        url = f"{self.api_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                
                self.logger.debug(
                    f"{operation_name} - Attempt {attempt}/{max_retries}",
                    {"method": method, "url": url, "data": data, "params": params}
                )
                
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=30
                )
                
                elapsed = time.time() - start_time
                
                # Check for success
                if response.status_code in [200, 201, 204]:
                    self.logger.info(
                        f"{operation_name} - SUCCESS",
                        {"attempt": attempt, "status": response.status_code, "elapsed_sec": round(elapsed, 3)}
                    )
                    
                    # Parse response (if any)
                    result_data = None
                    if response.content:
                        try:
                            result_data = response.json()
                            self.logger.debug(f"{operation_name} - Full response", {"response": result_data})
                        except:
                            result_data = {"raw": response.text}
                    
                    return {
                        "success": True,
                        "data": result_data,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "elapsed_sec": round(elapsed, 3)
                    }
                
                # Handle error responses
                error_detail = None
                try:
                    error_detail = response.json()
                except:
                    error_detail = {"raw": response.text}
                
                error_data = {
                    "attempt": attempt,
                    "status_code": response.status_code,
                    "elapsed_sec": round(elapsed, 3),
                    "error_detail": error_detail
                }
                
                self.logger.error(
                    f"{operation_name} - FAILED (attempt {attempt}/{max_retries})",
                    error_data
                )
                
                # Token expired? Refresh and retry once
                if response.status_code == 401 and attempt == 1:
                    self.logger.info("Token may be expired, refreshing...")
                    self.get_management_token(force_refresh=True)
                    continue
                
                # If last attempt or non-retryable error, return error
                if attempt == max_retries or response.status_code in [400, 401, 403, 404]:
                    return {
                        "success": False,
                        "error": error_detail.get("message", f"HTTP {response.status_code}"),
                        "status_code": response.status_code,
                        "error_detail": error_detail,
                        "attempts": attempt
                    }
                
                # Exponential backoff
                backoff = 2 ** (attempt - 1)
                self.logger.debug(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            
            except requests.exceptions.RequestException as e:
                elapsed = time.time() - start_time
                
                self.logger.error(
                    f"{operation_name} - REQUEST ERROR (attempt {attempt}/{max_retries})",
                    {"error": str(e), "elapsed_sec": round(elapsed, 3)}
                )
                
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "attempts": attempt
                    }
                
                backoff = 2 ** (attempt - 1)
                time.sleep(backoff)
            
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
    # USER OPERATIONS
    # ========================================
    
    def create_user(
        self,
        email: str,
        password: str,
        connection: str = "Username-Password-Authentication",
        email_verified: bool = False,
        user_metadata: Optional[Dict] = None,
        app_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            email: User email address
            password: User password
            connection: Auth0 connection name (database name)
            email_verified: Mark email as verified
            user_metadata: User-specific metadata (editable by user)
            app_metadata: Application metadata (not editable by user)
        
        Returns:
            Dict with success status and user data
        """
        self.logger.info(f"Creating user: {email}")
        
        data = {
            "email": email,
            "password": password,
            "connection": connection,
            "email_verified": email_verified
        }
        
        if user_metadata:
            data["user_metadata"] = user_metadata
        
        if app_metadata:
            data["app_metadata"] = app_metadata
        
        return self._make_request(
            method="POST",
            endpoint="/users",
            operation_name=f"CREATE_USER[{email}]",
            data=data
        )
    
    def get_user(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get user by ID.
        
        Args:
            user_id: Auth0 user ID (e.g., "auth0|123456")
        
        Returns:
            Dict with success status and user data
        """
        self.logger.info(f"Getting user: {user_id}")
        
        return self._make_request(
            method="GET",
            endpoint=f"/users/{user_id}",
            operation_name=f"GET_USER[{user_id}]"
        )
    
    def get_user_by_email(
        self,
        email: str
    ) -> Dict[str, Any]:
        """
        Search for user by email.
        
        Args:
            email: Email address to search
        
        Returns:
            Dict with success status and user data (if found)
        """
        self.logger.info(f"Searching user by email: {email}")
        
        result = self._make_request(
            method="GET",
            endpoint="/users-by-email",
            operation_name=f"SEARCH_USER[{email}]",
            params={"email": email}
        )
        
        # Extract first user if found
        if result["success"] and result["data"]:
            users = result["data"]
            if isinstance(users, list) and len(users) > 0:
                result["data"] = users[0]
            else:
                result["success"] = False
                result["error"] = "User not found"
        
        return result
    
    def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        email_verified: Optional[bool] = None,
        user_metadata: Optional[Dict] = None,
        app_metadata: Optional[Dict] = None,
        blocked: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update user properties.
        
        Args:
            user_id: Auth0 user ID
            email: New email address
            email_verified: Email verification status
            user_metadata: User metadata to update
            app_metadata: App metadata to update
            blocked: Block/unblock user
        
        Returns:
            Dict with success status and updated user data
        """
        self.logger.info(f"Updating user: {user_id}")
        
        data = {}
        
        if email is not None:
            data["email"] = email
        
        if email_verified is not None:
            data["email_verified"] = email_verified
        
        if user_metadata is not None:
            data["user_metadata"] = user_metadata
        
        if app_metadata is not None:
            data["app_metadata"] = app_metadata
        
        if blocked is not None:
            data["blocked"] = blocked
        
        return self._make_request(
            method="PATCH",
            endpoint=f"/users/{user_id}",
            operation_name=f"UPDATE_USER[{user_id}]",
            data=data
        )
    
    def delete_user(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Delete a user.
        
        Args:
            user_id: Auth0 user ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Deleting user: {user_id}")
        
        return self._make_request(
            method="DELETE",
            endpoint=f"/users/{user_id}",
            operation_name=f"DELETE_USER[{user_id}]"
        )
    
    def list_users(
        self,
        page: int = 0,
        per_page: int = 50,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List users with optional search.
        
        Args:
            page: Page number (0-indexed)
            per_page: Results per page (max 100)
            search_query: Lucene query (e.g., "email:*@example.com")
        
        Returns:
            Dict with success status and users list
        """
        self.logger.info("Listing users")
        
        params = {
            "page": page,
            "per_page": min(per_page, 100)
        }
        
        if search_query:
            params["q"] = search_query
            params["search_engine"] = "v3"
        
        return self._make_request(
            method="GET",
            endpoint="/users",
            operation_name="LIST_USERS",
            params=params
        )
    
    # ========================================
    # PASSWORD OPERATIONS
    # ========================================
    
    def send_password_reset_email(
        self,
        email: str,
        connection: str = "Username-Password-Authentication"
    ) -> Dict[str, Any]:
        """
        Send password reset email to user.
        
        Args:
            email: User email address
            connection: Auth0 connection name
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Sending password reset email to: {email}")
        
        try:
            response = requests.post(
                f"{self.base_url}/dbconnections/change_password",
                json={
                    "client_id": self.config.client_id,
                    "email": email,
                    "connection": connection
                },
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                self.logger.info(f"Password reset email sent successfully")
                return {
                    "success": True,
                    "message": "Password reset email sent"
                }
            else:
                error_data = response.json() if response.content else {}
                self.logger.error("Password reset failed", {"status": response.status_code, "error": error_data})
                
                return {
                    "success": False,
                    "error": error_data.get("message", "Password reset failed"),
                    "status_code": response.status_code
                }
        
        except Exception as e:
            self.logger.error(f"Password reset error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def change_user_password(
        self,
        user_id: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user's password (admin operation).
        
        Args:
            user_id: Auth0 user ID
            new_password: New password
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Changing password for user: {user_id}")
        
        return self._make_request(
            method="PATCH",
            endpoint=f"/users/{user_id}",
            operation_name=f"CHANGE_PASSWORD[{user_id}]",
            data={"password": new_password}
        )
    
    # ========================================
    # EMAIL VERIFICATION
    # ========================================
    
    def send_verification_email(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Send email verification to user.
        
        Args:
            user_id: Auth0 user ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Sending verification email to user: {user_id}")
        
        return self._make_request(
            method="POST",
            endpoint="/jobs/verification-email",
            operation_name=f"SEND_VERIFICATION[{user_id}]",
            data={"user_id": user_id}
        )
    
    # ========================================
    # ROLE OPERATIONS
    # ========================================
    
    def list_roles(self) -> Dict[str, Any]:
        """
        List all roles.
        
        Returns:
            Dict with success status and roles list
        """
        self.logger.info("Listing roles")
        
        return self._make_request(
            method="GET",
            endpoint="/roles",
            operation_name="LIST_ROLES"
        )
    
    def create_role(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new role.
        
        Args:
            name: Role name
            description: Role description
        
        Returns:
            Dict with success status and role data
        """
        self.logger.info(f"Creating role: {name}")
        
        data = {"name": name}
        if description:
            data["description"] = description
        
        return self._make_request(
            method="POST",
            endpoint="/roles",
            operation_name=f"CREATE_ROLE[{name}]",
            data=data
        )
    
    def assign_roles_to_user(
        self,
        user_id: str,
        role_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Assign roles to user.
        
        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to assign
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Assigning {len(role_ids)} roles to user: {user_id}")
        
        return self._make_request(
            method="POST",
            endpoint=f"/users/{user_id}/roles",
            operation_name=f"ASSIGN_ROLES[{user_id}]",
            data={"roles": role_ids}
        )
    
    def get_user_roles(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get roles assigned to user.
        
        Args:
            user_id: Auth0 user ID
        
        Returns:
            Dict with success status and roles list
        """
        self.logger.info(f"Getting roles for user: {user_id}")
        
        return self._make_request(
            method="GET",
            endpoint=f"/users/{user_id}/roles",
            operation_name=f"GET_USER_ROLES[{user_id}]"
        )
    
    # ========================================
    # CONVENIENCE METHODS
    # ========================================
    
    def setup_basic_auth(
        self,
        business_name: str
    ) -> Dict[str, Any]:
        """
        Convenience method: Set up basic authentication structure.
        
        Args:
            business_name: Name of business
        
        Returns:
            Dict with roles created and setup status
        """
        self.logger.info(f"Setting up basic auth for {business_name}")
        
        result = {
            "success": True,
            "business_name": business_name,
            "roles": {},
            "errors": []
        }
        
        # Create basic roles
        basic_roles = [
            ("user", "Standard user access"),
            ("admin", "Administrator access"),
            ("premium", "Premium user access")
        ]
        
        for role_name, role_desc in basic_roles:
            role_result = self.create_role(
                name=f"{business_name}_{role_name}",
                description=role_desc
            )
            
            if role_result["success"]:
                result["roles"][role_name] = role_result["data"]
            else:
                # Role might already exist, that's ok
                if "already exists" not in str(role_result.get("error", "")).lower():
                    result["errors"].append(f"Failed to create role {role_name}: {role_result.get('error')}")
        
        self.logger.info(f"Basic auth setup complete for {business_name}")
        
        return result


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_auth0_lib(config_path: str) -> Auth0Lib:
    """
    Convenience function to load Auth0Lib from config file.
    
    Args:
        config_path: Path to JSON config file
    
    Returns:
        Initialized Auth0Lib instance
    """
    config = Auth0Config(config_path=config_path)
    return Auth0Lib(config)


def load_auth0_lib_from_dict(config_dict: Dict) -> Auth0Lib:
    """
    Convenience function to load Auth0Lib from config dict.
    
    Args:
        config_dict: Config dictionary
    
    Returns:
        Initialized Auth0Lib instance
    """
    config = Auth0Config(config_dict=config_dict)
    return Auth0Lib(config)
