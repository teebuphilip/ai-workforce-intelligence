"""
Analytics Library (Google Analytics 4)
=======================================
Shared Google Analytics 4 integration library for tracking events and user behavior.

Features:
- Server-side event tracking (Measurement Protocol API)
- Page view tracking
- E-commerce tracking (purchases, subscriptions)
- User identification
- Custom event tracking
- Comprehensive debug logging with configurable levels
- Config-driven for multi-property support

Author: Teebu (via Claude)
Version: 1.0.0
Date: 2025-01-31
"""

import os
import json
import logging
import time
import requests
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime


# ============================================================
# LOGGING SETUP
# ============================================================

class AnalyticsLibLogger:
    """Custom logger with configurable verbosity for debugging"""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("analytics_lib")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler (stdout for terminal visibility)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s [ANALYTICS-LIB] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s [ANALYTICS-LIB] %(levelname)s - %(message)s',
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

class AnalyticsConfig:
    """Configuration container for Analytics operations"""
    
    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize Analytics configuration.
        
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
        self.measurement_id = self.config.get('ga4_measurement_id')
        self.api_secret = self.config.get('ga4_api_secret')
        
        if not self.measurement_id:
            raise ValueError("ga4_measurement_id is required in config")
        
        if not self.api_secret:
            raise ValueError("ga4_api_secret is required in config")
        
        # Optional fields
        self.account_name = self.config.get('account_name', 'Unknown Account')
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_file = self.config.get('log_file')
        self.debug_mode = self.config.get('debug_mode', False)  # GA4 debug mode
        
        # Check for env var override on log level
        env_log_level = os.getenv('ANALYTICS_LOG_LEVEL')
        if env_log_level:
            self.log_level = env_log_level
    
    def __repr__(self):
        return f"AnalyticsConfig(account={self.account_name}, measurement_id={self.measurement_id[:10]}..., log_level={self.log_level})"


# ============================================================
# MAIN LIBRARY CLASS
# ============================================================

class AnalyticsLib:
    """Main Analytics library interface"""
    
    # GA4 Measurement Protocol endpoint
    BASE_URL = "https://www.google-analytics.com/mp/collect"
    DEBUG_URL = "https://www.google-analytics.com/debug/mp/collect"
    
    def __init__(self, config: AnalyticsConfig):
        """
        Initialize Analytics library.
        
        Args:
            config: AnalyticsConfig instance
        """
        self.config = config
        self.logger = AnalyticsLibLogger(
            log_level=config.log_level,
            log_file=config.log_file
        )
        
        self.logger.info(f"AnalyticsLib initialized", {
            "account": config.account_name,
            "measurement_id": config.measurement_id[:15] + "...",
            "log_level": config.log_level,
            "debug_mode": config.debug_mode
        })
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _generate_client_id(self) -> str:
        """
        Generate a client ID for GA4.
        Format: UUID-based random string
        
        Returns:
            Client ID string
        """
        return str(uuid.uuid4())
    
    def _send_event(
        self,
        client_id: str,
        events: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        user_properties: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Send event(s) to GA4 Measurement Protocol.
        
        Args:
            client_id: GA4 client ID (generated or from cookie)
            events: List of event dicts
            user_id: Optional user ID for identification
            user_properties: Optional user properties
            max_retries: Number of retry attempts
        
        Returns:
            Dict with success status
        """
        # Choose endpoint based on debug mode
        url = self.DEBUG_URL if self.config.debug_mode else self.BASE_URL
        
        # Build payload
        payload = {
            "client_id": client_id,
            "events": events
        }
        
        if user_id:
            payload["user_id"] = user_id
        
        if user_properties:
            payload["user_properties"] = user_properties
        
        # Add measurement_id and api_secret as query params
        params = {
            "measurement_id": self.config.measurement_id,
            "api_secret": self.config.api_secret
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                
                self.logger.debug(
                    f"Sending {len(events)} event(s) - Attempt {attempt}/{max_retries}",
                    {"payload": payload, "params": params}
                )
                
                response = requests.post(
                    url,
                    params=params,
                    json=payload,
                    timeout=10
                )
                
                elapsed = time.time() - start_time
                
                # GA4 returns 204 No Content on success
                if response.status_code in [200, 204]:
                    self.logger.info(
                        f"Events sent successfully",
                        {"count": len(events), "attempt": attempt, "elapsed_sec": round(elapsed, 3)}
                    )
                    
                    # In debug mode, log validation messages
                    if self.config.debug_mode and response.content:
                        try:
                            debug_response = response.json()
                            self.logger.debug("GA4 debug response", {"response": debug_response})
                        except:
                            pass
                    
                    return {
                        "success": True,
                        "events_sent": len(events),
                        "attempt": attempt,
                        "elapsed_sec": round(elapsed, 3)
                    }
                
                # Handle errors
                error_data = {
                    "attempt": attempt,
                    "status_code": response.status_code,
                    "elapsed_sec": round(elapsed, 3)
                }
                
                if response.content:
                    try:
                        error_data["response"] = response.json()
                    except:
                        error_data["response"] = response.text
                
                self.logger.error(
                    f"Failed to send events (attempt {attempt}/{max_retries})",
                    error_data
                )
                
                # If last attempt, return error
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "status_code": response.status_code,
                        "attempts": attempt
                    }
                
                # Exponential backoff
                backoff = 2 ** (attempt - 1)
                self.logger.debug(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            
            except requests.exceptions.RequestException as e:
                elapsed = time.time() - start_time
                
                self.logger.error(
                    f"Request error (attempt {attempt}/{max_retries})",
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
                    f"Unexpected error",
                    {"error": str(e), "type": type(e).__name__}
                )
                
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "attempts": attempt
                }
    
    # ========================================
    # EVENT TRACKING
    # ========================================
    
    def track_event(
        self,
        event_name: str,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_params: Optional[Dict[str, Any]] = None,
        user_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track a custom event.
        
        Args:
            event_name: Name of event (e.g., "signup", "purchase", "button_click")
            client_id: GA4 client ID (generated if not provided)
            user_id: Optional user ID for identification
            event_params: Event parameters (e.g., {"button_name": "cta"})
            user_properties: User properties (e.g., {"plan": "premium"})
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking event: {event_name}")
        
        # Generate client_id if not provided
        if not client_id:
            client_id = self._generate_client_id()
        
        # Build event
        event = {
            "name": event_name
        }
        
        if event_params:
            event["params"] = event_params
        
        return self._send_event(
            client_id=client_id,
            events=[event],
            user_id=user_id,
            user_properties=user_properties
        )
    
    def track_page_view(
        self,
        page_path: str,
        page_title: Optional[str] = None,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a page view.
        
        Args:
            page_path: Page path (e.g., "/pricing")
            page_title: Page title (e.g., "Pricing")
            client_id: GA4 client ID
            user_id: Optional user ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking page view: {page_path}")
        
        # Generate client_id if not provided
        if not client_id:
            client_id = self._generate_client_id()
        
        # Build page_view event
        event_params = {
            "page_path": page_path
        }
        
        if page_title:
            event_params["page_title"] = page_title
        
        return self.track_event(
            event_name="page_view",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params
        )
    
    # ========================================
    # USER LIFECYCLE EVENTS
    # ========================================
    
    def track_signup(
        self,
        user_id: str,
        client_id: Optional[str] = None,
        signup_method: Optional[str] = None,
        user_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track user signup.
        
        Args:
            user_id: User ID (from Auth0 or your system)
            client_id: GA4 client ID
            signup_method: Method used (e.g., "email", "google", "github")
            user_properties: User properties (e.g., {"plan": "free"})
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking signup: {user_id}")
        
        event_params = {}
        
        if signup_method:
            event_params["method"] = signup_method
        
        return self.track_event(
            event_name="sign_up",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params,
            user_properties=user_properties
        )
    
    def track_login(
        self,
        user_id: str,
        client_id: Optional[str] = None,
        login_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track user login.
        
        Args:
            user_id: User ID
            client_id: GA4 client ID
            login_method: Method used (e.g., "email", "google")
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking login: {user_id}")
        
        event_params = {}
        
        if login_method:
            event_params["method"] = login_method
        
        return self.track_event(
            event_name="login",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params
        )
    
    # ========================================
    # E-COMMERCE EVENTS
    # ========================================
    
    def track_purchase(
        self,
        transaction_id: str,
        value: float,
        currency: str = "USD",
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        coupon: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a purchase (for Stripe payments).
        
        Args:
            transaction_id: Stripe charge/payment ID
            value: Purchase amount in dollars (e.g., 49.00)
            currency: Currency code (default: USD)
            client_id: GA4 client ID
            user_id: User ID
            items: List of item dicts (e.g., [{"item_id": "sub_monthly", "item_name": "Monthly Plan", "price": 49.00}])
            coupon: Coupon code (if used)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking purchase: {transaction_id} (${value})")
        
        event_params = {
            "transaction_id": transaction_id,
            "value": value,
            "currency": currency
        }
        
        if items:
            event_params["items"] = items
        
        if coupon:
            event_params["coupon"] = coupon
        
        return self.track_event(
            event_name="purchase",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params
        )
    
    def track_begin_checkout(
        self,
        value: float,
        currency: str = "USD",
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Track when user begins checkout (clicks "Subscribe" button).
        
        Args:
            value: Cart value
            currency: Currency code
            client_id: GA4 client ID
            user_id: User ID
            items: Cart items
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking begin checkout: ${value}")
        
        event_params = {
            "value": value,
            "currency": currency
        }
        
        if items:
            event_params["items"] = items
        
        return self.track_event(
            event_name="begin_checkout",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params
        )
    
    def track_subscription_start(
        self,
        subscription_id: str,
        plan_name: str,
        value: float,
        currency: str = "USD",
        client_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track subscription start (custom event).
        
        Args:
            subscription_id: Stripe subscription ID
            plan_name: Plan name (e.g., "Monthly Pro")
            value: Subscription value
            currency: Currency code
            client_id: GA4 client ID
            user_id: User ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking subscription start: {plan_name}")
        
        event_params = {
            "subscription_id": subscription_id,
            "plan_name": plan_name,
            "value": value,
            "currency": currency
        }
        
        return self.track_event(
            event_name="subscription_start",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params
        )
    
    def track_subscription_cancel(
        self,
        subscription_id: str,
        plan_name: str,
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track subscription cancellation (custom event).
        
        Args:
            subscription_id: Stripe subscription ID
            plan_name: Plan name
            client_id: GA4 client ID
            user_id: User ID
            reason: Cancellation reason (if provided)
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking subscription cancel: {plan_name}")
        
        event_params = {
            "subscription_id": subscription_id,
            "plan_name": plan_name
        }
        
        if reason:
            event_params["reason"] = reason
        
        return self.track_event(
            event_name="subscription_cancel",
            client_id=client_id,
            user_id=user_id,
            event_params=event_params
        )
    
    # ========================================
    # BATCH TRACKING
    # ========================================
    
    def track_events_batch(
        self,
        events: List[Dict[str, Any]],
        client_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track multiple events in one request (max 25 events per request).
        
        Args:
            events: List of event dicts (each with "name" and optional "params")
            client_id: GA4 client ID
            user_id: User ID
            user_properties: User properties
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking batch: {len(events)} events")
        
        # Generate client_id if not provided
        if not client_id:
            client_id = self._generate_client_id()
        
        # GA4 limit is 25 events per request
        if len(events) > 25:
            self.logger.warning(f"Batch size {len(events)} exceeds GA4 limit of 25. Sending first 25.")
            events = events[:25]
        
        return self._send_event(
            client_id=client_id,
            events=events,
            user_id=user_id,
            user_properties=user_properties
        )
    
    # ========================================
    # CONVENIENCE METHODS
    # ========================================
    
    def track_stripe_webhook(
        self,
        event_type: str,
        stripe_event: Dict[str, Any],
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convenience method: Track Stripe webhook events.
        
        Args:
            event_type: Stripe event type (e.g., "charge.succeeded")
            stripe_event: Full Stripe event object
            client_id: GA4 client ID
        
        Returns:
            Dict with success status
        """
        self.logger.info(f"Tracking Stripe webhook: {event_type}")
        
        # Extract relevant data based on event type
        if event_type == "charge.succeeded":
            charge = stripe_event.get("data", {}).get("object", {})
            return self.track_purchase(
                transaction_id=charge.get("id"),
                value=charge.get("amount", 0) / 100.0,  # Convert cents to dollars
                currency=charge.get("currency", "usd").upper(),
                client_id=client_id,
                user_id=charge.get("metadata", {}).get("user_id")
            )
        
        elif event_type == "customer.subscription.created":
            subscription = stripe_event.get("data", {}).get("object", {})
            plan = subscription.get("items", {}).get("data", [{}])[0].get("plan", {})
            return self.track_subscription_start(
                subscription_id=subscription.get("id"),
                plan_name=plan.get("nickname", "Unknown Plan"),
                value=plan.get("amount", 0) / 100.0,
                currency=plan.get("currency", "usd").upper(),
                client_id=client_id,
                user_id=subscription.get("metadata", {}).get("user_id")
            )
        
        elif event_type == "customer.subscription.deleted":
            subscription = stripe_event.get("data", {}).get("object", {})
            plan = subscription.get("items", {}).get("data", [{}])[0].get("plan", {})
            return self.track_subscription_cancel(
                subscription_id=subscription.get("id"),
                plan_name=plan.get("nickname", "Unknown Plan"),
                client_id=client_id,
                user_id=subscription.get("metadata", {}).get("user_id")
            )
        
        else:
            # Track as generic event
            return self.track_event(
                event_name=f"stripe_{event_type}",
                client_id=client_id,
                event_params={"event_type": event_type}
            )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_analytics_lib(config_path: str) -> AnalyticsLib:
    """
    Convenience function to load AnalyticsLib from config file.
    
    Args:
        config_path: Path to JSON config file
    
    Returns:
        Initialized AnalyticsLib instance
    """
    config = AnalyticsConfig(config_path=config_path)
    return AnalyticsLib(config)


def load_analytics_lib_from_dict(config_dict: Dict) -> AnalyticsLib:
    """
    Convenience function to load AnalyticsLib from config dict.
    
    Args:
        config_dict: Config dictionary
    
    Returns:
        Initialized AnalyticsLib instance
    """
    config = AnalyticsConfig(config_dict=config_dict)
    return AnalyticsLib(config)
