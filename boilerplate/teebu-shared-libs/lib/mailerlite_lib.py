"""
AF/FO MailerLite Library
=========================
Shared MailerLite integration library for AF portfolio businesses and FO customer deployments.

Features:
- Manage subscribers (add, update, remove, unsubscribe)
- Manage groups/segments
- Send campaigns
- Manage automation workflows
- Track campaign stats
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

class MailerLiteLibLogger:
    """Custom logger with configurable verbosity for debugging"""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("mailerlite_lib")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler (stdout for terminal visibility)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s [MAILERLITE-LIB] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s [MAILERLITE-LIB] %(levelname)s - %(message)s',
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

class MailerLiteConfig:
    """Configuration container for MailerLite operations"""
    
    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize MailerLite configuration.
        
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
        self.api_key = self.config.get('mailerlite_api_key')
        if not self.api_key:
            raise ValueError("mailerlite_api_key is required in config")
        
        # Optional fields
        self.account_name = self.config.get('account_name', 'Unknown Account')
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_file = self.config.get('log_file')
        
        # Check for env var override on log level
        env_log_level = os.getenv('MAILERLITE_LOG_LEVEL')
        if env_log_level:
            self.log_level = env_log_level
    
    def __repr__(self):
        return f"MailerLiteConfig(account={self.account_name}, log_level={self.log_level})"


# ============================================================
# MAIN LIBRARY CLASS
# ============================================================

class MailerLiteLib:
    """Main MailerLite library interface"""
    
    BASE_URL = "https://connect.mailerlite.com/api"
    
    def __init__(self, config: MailerLiteConfig):
        """
        Initialize MailerLite library.
        
        Args:
            config: MailerLiteConfig instance
        """
        self.config = config
        self.logger = MailerLiteLibLogger(
            log_level=config.log_level,
            log_file=config.log_file
        )
        
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        self.logger.info(f"MailerLiteLib initialized", {
            "account": config.account_name,
            "log_level": config.log_level
        })
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
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
        Make HTTP request to MailerLite API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/subscribers")
            operation_name: Human-readable name for logging
            data: JSON data for request body
            params: Query parameters
            max_retries: Maximum retry attempts
        
        Returns:
            Dict with success status and data/error
        """
        url = f"{self.BASE_URL}{endpoint}"
        
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
                    headers=self.headers,
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
    # SUBSCRIBER OPERATIONS
    # ========================================
    
    def add_subscriber(
        self,
        email: str,
        fields: Optional[Dict[str, str]] = None,
        groups: Optional[List[str]] = None,
        status: str = "active",
        subscribed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add or update a subscriber.
        
        Args:
            email: Subscriber email address
            fields: Custom fields dict (e.g., {"name": "John", "last_name": "Doe"})
            groups: List of group IDs to add subscriber to
            status: Subscriber status (active, unsubscribed, bounced, junk)
            subscribed_at: ISO timestamp of subscription (optional)
        
        Returns:
            Dict with success status and subscriber data
        """
        self.logger.info(f"Adding subscriber: {email}")
        
        data = {
            "email": email,
            "status": status
        }
        
        if fields:
            data["fields"] = fields
        
        if groups:
            data["groups"] = groups
        
        if subscribed_at:
            data["subscribed_at"] = subscribed_at
        
        return self._make_request(
            method="POST",
            endpoint="/subscribers",
            operation_name=f"ADD_SUBSCRIBER[{email}]",
            data=data
        )
    
    def update_subscriber(
        self,
        subscriber_id: str,
        fields: Optional[Dict[str, str]] = None,
        groups: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing subscriber.
        
        Args:
            subscriber_id: MailerLite subscriber ID
            fields: Custom fields to update
            groups: List of group IDs
            status: New status
        
        Returns:
            Dict with success status and updated subscriber data
        """
        self.logger.info(f"Updating subscriber: {subscriber_id}")
        
        data = {}
        
        if fields:
            data["fields"] = fields
        
        if groups:
            data["groups"] = groups
        
        if status:
            data["status"] = status
        
        return self._make_request(
            method="PUT",
            endpoint=f"/subscribers/{subscriber_id}",
            operation_name=f"UPDATE_SUBSCRIBER[{subscriber_id}]",
            data=data
        )
    
    def get_subscriber(
        self,
        subscriber_id: str
    ) -> Dict[str, Any]:
        """
        Get subscriber by ID.
        
        Args:
            subscriber_id: MailerLite subscriber ID
        
        Returns:
            Dict with success status and subscriber data
        """
        self.logger.info(f"Getting subscriber: {subscriber_id}")
        
        return self._make_request(
            method="GET",
            endpoint=f"/subscribers/{subscriber_id}",
            operation_name=f"GET_SUBSCRIBER[{subscriber_id}]"
        )
    
    def get_subscriber_by_email(
        self,
        email: str
    ) -> Dict[str, Any]:
        """
        Search for subscriber by email.
        
        Args:
            email: Email address to search
        
        Returns:
            Dict with success status and subscriber data (if found)
        """
        self.logger.info(f"Searching subscriber by email: {email}")
        
        result = self._make_request(
            method="GET",
            endpoint="/subscribers",
            operation_name=f"SEARCH_SUBSCRIBER[{email}]",
            params={"filter[email]": email}
        )
        
        # Extract first subscriber if found
        if result["success"] and result["data"]:
            subscribers = result["data"].get("data", [])
            if subscribers:
                result["data"] = subscribers[0]
            else:
                result["success"] = False
                result["error"] = "Subscriber not found"
        
        return result
    
    def unsubscribe_subscriber(
        self,
        subscriber_id: str
    ) -> Dict[str, Any]:
        """
        Unsubscribe a subscriber.
        
        Args:
            subscriber_id: MailerLite subscriber ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Unsubscribing subscriber: {subscriber_id}")
        
        return self.update_subscriber(
            subscriber_id=subscriber_id,
            status="unsubscribed"
        )
    
    def delete_subscriber(
        self,
        subscriber_id: str
    ) -> Dict[str, Any]:
        """
        Permanently delete a subscriber.
        
        Args:
            subscriber_id: MailerLite subscriber ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Deleting subscriber: {subscriber_id}")
        
        return self._make_request(
            method="DELETE",
            endpoint=f"/subscribers/{subscriber_id}",
            operation_name=f"DELETE_SUBSCRIBER[{subscriber_id}]"
        )
    
    # ========================================
    # GROUP OPERATIONS
    # ========================================
    
    def create_group(
        self,
        name: str
    ) -> Dict[str, Any]:
        """
        Create a new subscriber group.
        
        Args:
            name: Group name
        
        Returns:
            Dict with success status and group data
        """
        self.logger.info(f"Creating group: {name}")
        
        return self._make_request(
            method="POST",
            endpoint="/groups",
            operation_name=f"CREATE_GROUP[{name}]",
            data={"name": name}
        )
    
    def list_groups(
        self,
        limit: int = 25,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        List all groups.
        
        Args:
            limit: Number of results per page (max 100)
            page: Page number
        
        Returns:
            Dict with success status and groups list
        """
        self.logger.info("Listing groups")
        
        return self._make_request(
            method="GET",
            endpoint="/groups",
            operation_name="LIST_GROUPS",
            params={"limit": limit, "page": page}
        )
    
    def delete_group(
        self,
        group_id: str
    ) -> Dict[str, Any]:
        """
        Delete a group.
        
        Args:
            group_id: MailerLite group ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Deleting group: {group_id}")
        
        return self._make_request(
            method="DELETE",
            endpoint=f"/groups/{group_id}",
            operation_name=f"DELETE_GROUP[{group_id}]"
        )
    
    def add_subscriber_to_group(
        self,
        subscriber_id: str,
        group_id: str
    ) -> Dict[str, Any]:
        """
        Add subscriber to a group.
        
        Args:
            subscriber_id: MailerLite subscriber ID
            group_id: MailerLite group ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Adding subscriber {subscriber_id} to group {group_id}")
        
        return self._make_request(
            method="POST",
            endpoint=f"/subscribers/{subscriber_id}/groups/{group_id}",
            operation_name=f"ADD_TO_GROUP[{subscriber_id}->{group_id}]"
        )
    
    # ========================================
    # CAMPAIGN OPERATIONS
    # ========================================
    
    def list_campaigns(
        self,
        limit: int = 25,
        page: int = 1,
        filter_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List campaigns.
        
        Args:
            limit: Number of results per page (max 100)
            page: Page number
            filter_status: Filter by status (draft, ready, sent)
        
        Returns:
            Dict with success status and campaigns list
        """
        self.logger.info("Listing campaigns")
        
        params = {"limit": limit, "page": page}
        if filter_status:
            params["filter[status]"] = filter_status
        
        return self._make_request(
            method="GET",
            endpoint="/campaigns",
            operation_name="LIST_CAMPAIGNS",
            params=params
        )
    
    def get_campaign(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Get campaign details.
        
        Args:
            campaign_id: MailerLite campaign ID
        
        Returns:
            Dict with success status and campaign data
        """
        self.logger.info(f"Getting campaign: {campaign_id}")
        
        return self._make_request(
            method="GET",
            endpoint=f"/campaigns/{campaign_id}",
            operation_name=f"GET_CAMPAIGN[{campaign_id}]"
        )
    
    def get_campaign_stats(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Get campaign statistics.
        
        Args:
            campaign_id: MailerLite campaign ID
        
        Returns:
            Dict with success status and stats (opens, clicks, etc)
        """
        self.logger.info(f"Getting campaign stats: {campaign_id}")
        
        # Get campaign which includes stats
        result = self.get_campaign(campaign_id)
        
        if result["success"] and result["data"]:
            stats = {
                "sent": result["data"].get("emails_count", 0),
                "opened": result["data"].get("open_count", 0),
                "clicked": result["data"].get("click_count", 0),
                "open_rate": result["data"].get("open_rate", {}).get("float", 0),
                "click_rate": result["data"].get("click_rate", {}).get("float", 0),
            }
            result["stats"] = stats
        
        return result
    
    # ========================================
    # FIELD OPERATIONS
    # ========================================
    
    def list_fields(self) -> Dict[str, Any]:
        """
        List all custom fields.
        
        Returns:
            Dict with success status and fields list
        """
        self.logger.info("Listing custom fields")
        
        return self._make_request(
            method="GET",
            endpoint="/fields",
            operation_name="LIST_FIELDS"
        )
    
    def create_field(
        self,
        name: str,
        field_type: str = "TEXT"
    ) -> Dict[str, Any]:
        """
        Create a custom field.
        
        Args:
            name: Field name (e.g., "company")
            field_type: Field type (TEXT, NUMBER, DATE)
        
        Returns:
            Dict with success status and field data
        """
        self.logger.info(f"Creating custom field: {name}")
        
        return self._make_request(
            method="POST",
            endpoint="/fields",
            operation_name=f"CREATE_FIELD[{name}]",
            data={"name": name, "type": field_type}
        )
    
    # ========================================
    # AUTOMATION OPERATIONS
    # ========================================
    
    def list_automations(
        self,
        limit: int = 25,
        page: int = 1,
        filter_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List automations.
        
        Args:
            limit: Number of results per page (max 100)
            page: Page number
            filter_status: Filter by status (enabled, disabled)
        
        Returns:
            Dict with success status and automations list
        """
        self.logger.info("Listing automations")
        
        params = {"limit": limit, "page": page}
        if filter_status:
            params["filter[status]"] = filter_status
        
        return self._make_request(
            method="GET",
            endpoint="/automations",
            operation_name="LIST_AUTOMATIONS",
            params=params
        )
    
    def get_automation(
        self,
        automation_id: str
    ) -> Dict[str, Any]:
        """
        Get automation details.
        
        Args:
            automation_id: MailerLite automation ID
        
        Returns:
            Dict with success status and automation data
        """
        self.logger.info(f"Getting automation: {automation_id}")
        
        return self._make_request(
            method="GET",
            endpoint=f"/automations/{automation_id}",
            operation_name=f"GET_AUTOMATION[{automation_id}]"
        )
    
    # ========================================
    # WEBHOOK OPERATIONS
    # ========================================
    
    def create_webhook(
        self,
        url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """
        Create a webhook.
        
        Args:
            url: Webhook URL
            events: List of events to subscribe to
                   (subscriber.created, subscriber.updated, subscriber.unsubscribed,
                    campaign.sent, automation.triggered, etc)
        
        Returns:
            Dict with success status and webhook data
        """
        self.logger.info(f"Creating webhook: {url}")
        
        return self._make_request(
            method="POST",
            endpoint="/webhooks",
            operation_name=f"CREATE_WEBHOOK[{url}]",
            data={"url": url, "events": events}
        )
    
    def list_webhooks(self) -> Dict[str, Any]:
        """
        List all webhooks.
        
        Returns:
            Dict with success status and webhooks list
        """
        self.logger.info("Listing webhooks")
        
        return self._make_request(
            method="GET",
            endpoint="/webhooks",
            operation_name="LIST_WEBHOOKS"
        )
    
    def delete_webhook(
        self,
        webhook_id: str
    ) -> Dict[str, Any]:
        """
        Delete a webhook.
        
        Args:
            webhook_id: MailerLite webhook ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Deleting webhook: {webhook_id}")
        
        return self._make_request(
            method="DELETE",
            endpoint=f"/webhooks/{webhook_id}",
            operation_name=f"DELETE_WEBHOOK[{webhook_id}]"
        )
    
    # ========================================
    # CONVENIENCE METHODS
    # ========================================
    
    def setup_welcome_automation(
        self,
        business_name: str,
        welcome_group_name: str = "New Subscribers"
    ) -> Dict[str, Any]:
        """
        Convenience method: Set up basic welcome email automation.
        
        Args:
            business_name: Name of business
            welcome_group_name: Name of group for new subscribers
        
        Returns:
            Dict with group_id and setup status
        """
        self.logger.info(f"Setting up welcome automation for {business_name}")
        
        result = {
            "success": True,
            "business_name": business_name,
            "group": None,
            "errors": []
        }
        
        # Create welcome group
        group_result = self.create_group(name=welcome_group_name)
        
        if not group_result["success"]:
            result["success"] = False
            result["errors"].append(f"Failed to create group: {group_result.get('error')}")
            return result
        
        result["group"] = group_result["data"]
        
        self.logger.info(f"Welcome automation setup complete for {business_name}")

        return result

    # ========================================
    # TRANSACTIONAL EMAIL CONVENIENCE METHODS
    # WHY P1: System-triggered emails (welcome, billing, cancellation)
    #         must fire reliably on specific lifecycle events.
    #         These methods standardize the trigger pattern so business
    #         logic never has to assemble subscriber payloads manually.
    # ========================================

    def send_welcome_email(
        self,
        email: str,
        name: str,
        group_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a welcome email for a new subscriber.

        Adds the subscriber (or updates if exists) and places them in the
        welcome group, which should have a MailerLite automation attached.

        Args:
            email: New subscriber's email address
            name: New subscriber's display name
            group_id: ID of the group linked to your welcome automation

        Returns:
            Dict with success status and subscriber data
        """
        self.logger.info(f"Sending welcome email to {email}")

        fields = {"name": name, "signup_source": "welcome_flow"}
        groups = [group_id] if group_id else []

        return self.add_subscriber(
            email=email,
            fields=fields,
            groups=groups,
        )

    def send_subscription_confirmation(
        self,
        email: str,
        name: str,
        plan_name: str,
    ) -> Dict[str, Any]:
        """
        Notify a subscriber that their paid subscription is active.

        Updates subscriber record with plan metadata. Wire a MailerLite
        automation to trigger on field update for 'plan_name'.

        Args:
            email: Subscriber's email address
            name: Subscriber's display name
            plan_name: The plan they subscribed to (e.g. "Pro", "Basic")

        Returns:
            Dict with success status and subscriber data
        """
        self.logger.info(f"Sending subscription confirmation to {email}", {
            "plan": plan_name
        })

        return self.add_subscriber(
            email=email,
            fields={
                "name": name,
                "plan_name": plan_name,
                "subscribed_at": datetime.utcnow().isoformat(),
            },
        )

    def send_subscription_cancelled(
        self,
        email: str,
        name: str,
    ) -> Dict[str, Any]:
        """
        Notify a subscriber that their subscription has been cancelled.

        Updates their record with cancellation metadata. Wire a MailerLite
        automation to trigger on 'subscription_status' = 'cancelled'.

        Args:
            email: Subscriber's email address
            name: Subscriber's display name

        Returns:
            Dict with success status and subscriber data
        """
        self.logger.info(f"Sending cancellation email to {email}")

        return self.add_subscriber(
            email=email,
            fields={
                "name": name,
                "subscription_status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
            },
        )

    def send_payment_failed_notification(
        self,
        email: str,
        name: str,
        amount: float,
    ) -> Dict[str, Any]:
        """
        Notify a subscriber of a failed payment attempt.

        Updates their record with payment failure metadata. Wire a MailerLite
        automation to trigger on 'last_payment_status' = 'failed'.

        Args:
            email: Subscriber's email address
            name: Subscriber's display name
            amount: The payment amount that failed (in dollars, e.g. 49.00)

        Returns:
            Dict with success status and subscriber data
        """
        self.logger.info(f"Sending payment failed notification to {email}", {
            "amount": amount
        })

        return self.add_subscriber(
            email=email,
            fields={
                "name": name,
                "last_payment_status": "failed",
                "last_failed_amount": str(amount),
                "last_failed_at": datetime.utcnow().isoformat(),
            },
        )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_mailerlite_lib(config_path: str) -> MailerLiteLib:
    """
    Convenience function to load MailerLiteLib from config file.
    
    Args:
        config_path: Path to JSON config file
    
    Returns:
        Initialized MailerLiteLib instance
    """
    config = MailerLiteConfig(config_path=config_path)
    return MailerLiteLib(config)


def load_mailerlite_lib_from_dict(config_dict: Dict) -> MailerLiteLib:
    """
    Convenience function to load MailerLiteLib from config dict.
    
    Args:
        config_dict: Config dictionary
    
    Returns:
        Initialized MailerLiteLib instance
    """
    config = MailerLiteConfig(config_dict=config_dict)
    return MailerLiteLib(config)
