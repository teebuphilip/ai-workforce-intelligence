"""
AF/FO Stripe Library
====================
Shared Stripe integration library for AF portfolio businesses and FO customer deployments.

Features:
- Create subscription products and prices
- Generate payment links
- Handle webhooks
- Cancel subscriptions
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
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import stripe
except ImportError:
    raise ImportError(
        "stripe package not installed. Run: pip install stripe --break-system-packages"
    )


# ============================================================
# LOGGING SETUP
# ============================================================

class StripeLibLogger:
    """Custom logger with configurable verbosity for debugging"""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("stripe_lib")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers = []  # Clear any existing handlers
        
        # Console handler (stdout for terminal visibility)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s [STRIPE-LIB] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s [STRIPE-LIB] %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def debug(self, msg: str, extra: Optional[Dict] = None):
        """Debug level logging (verbose)"""
        if extra:
            msg = f"{msg} | {json.dumps(extra, indent=2)}"
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

class StripeConfig:
    """Configuration container for Stripe operations"""
    
    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize Stripe configuration.
        
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
        self.stripe_secret_key = self.config.get('stripe_secret_key')
        if not self.stripe_secret_key:
            raise ValueError("stripe_secret_key is required in config")
        
        # Optional fields
        self.stripe_webhook_secret = self.config.get('stripe_webhook_secret')
        self.account_name = self.config.get('account_name', 'Unknown Account')
        self.log_level = self.config.get('log_level', 'INFO')
        self.log_file = self.config.get('log_file')
        
        # Check for env var override on log level
        env_log_level = os.getenv('STRIPE_LOG_LEVEL')
        if env_log_level:
            self.log_level = env_log_level
    
    def __repr__(self):
        return f"StripeConfig(account={self.account_name}, log_level={self.log_level})"


# ============================================================
# MAIN LIBRARY CLASS
# ============================================================

class StripeLib:
    """Main Stripe library interface"""
    
    def __init__(self, config: StripeConfig):
        """
        Initialize Stripe library.
        
        Args:
            config: StripeConfig instance
        """
        self.config = config
        self.logger = StripeLibLogger(
            log_level=config.log_level,
            log_file=config.log_file
        )
        
        # Set Stripe API key
        stripe.api_key = config.stripe_secret_key
        
        self.logger.info(f"StripeLib initialized", {
            "account": config.account_name,
            "log_level": config.log_level
        })
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _retry_with_backoff(
        self,
        operation: callable,
        operation_name: str,
        max_retries: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute Stripe operation with exponential backoff retry.
        
        Args:
            operation: Callable to execute
            operation_name: Human-readable name for logging
            max_retries: Maximum retry attempts
            **kwargs: Arguments to pass to operation
        
        Returns:
            Dict with success status and data/error
        """
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                
                self.logger.debug(
                    f"{operation_name} - Attempt {attempt}/{max_retries}",
                    {"kwargs": kwargs}
                )
                
                result = operation(**kwargs)
                elapsed = time.time() - start_time
                
                self.logger.info(
                    f"{operation_name} - SUCCESS",
                    {"attempt": attempt, "elapsed_sec": round(elapsed, 3)}
                )
                
                self.logger.debug(
                    f"{operation_name} - Full response",
                    {"response": result}
                )
                
                return {
                    "success": True,
                    "data": result,
                    "attempt": attempt,
                    "elapsed_sec": round(elapsed, 3)
                }
            
            except stripe.error.StripeError as e:
                elapsed = time.time() - start_time
                
                error_data = {
                    "attempt": attempt,
                    "elapsed_sec": round(elapsed, 3),
                    "error": str(e),
                    "stripe_error_code": getattr(e, 'code', None),
                    "stripe_error_type": type(e).__name__,
                    "http_status": getattr(e, 'http_status', None),
                    "request_id": getattr(e, 'request_id', None),
                }
                
                if hasattr(e, 'json_body'):
                    error_data["stripe_error_detail"] = e.json_body
                
                self.logger.error(
                    f"{operation_name} - FAILED (attempt {attempt}/{max_retries})",
                    error_data
                )
                
                # If last attempt, return error
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "stripe_error_code": getattr(e, 'code', None),
                        "stripe_error_type": type(e).__name__,
                        "http_status": getattr(e, 'http_status', None),
                        "request_id": getattr(e, 'request_id', None),
                        "full_error": error_data,
                        "attempts": attempt
                    }
                
                # Exponential backoff: 1s, 2s, 4s
                backoff = 2 ** (attempt - 1)
                self.logger.debug(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            
            except Exception as e:
                # Non-Stripe error (shouldn't happen but catch anyway)
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
    # PRODUCT OPERATIONS
    # ========================================
    
    def create_subscription_product(
        self,
        business_name: str,
        description: str = "",
        statement_descriptor: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Product for a subscription business.
        
        Args:
            business_name: Name of the business (e.g., "InboxTamer")
            description: Product description
            statement_descriptor: What appears on customer's credit card (max 22 chars)
            metadata: Custom metadata dict
        
        Returns:
            Dict with success status and product data
        """
        self.logger.info(f"Creating subscription product: {business_name}")
        
        # Generate statement descriptor if not provided
        if not statement_descriptor:
            statement_descriptor = business_name.upper().replace(' ', '')[:22]
        
        # Default metadata
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'business_name': business_name,
            'created_by': 'stripe_lib',
            'created_at': datetime.utcnow().isoformat()
        })
        
        return self._retry_with_backoff(
            operation=stripe.Product.create,
            operation_name=f"CREATE_PRODUCT[{business_name}]",
            name=business_name,
            description=description or f"Subscription for {business_name}",
            statement_descriptor=statement_descriptor,
            metadata=metadata
        )
    
    def create_price(
        self,
        product_id: str,
        amount_cents: int,
        currency: str = "usd",
        interval: str = "month",
        interval_count: int = 1,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a Price for a Product.
        
        Args:
            product_id: Stripe product ID (prod_xxx)
            amount_cents: Price in cents (e.g., 4900 = $49.00)
            currency: Currency code (default: usd)
            interval: Billing interval (month/year)
            interval_count: Number of intervals between billings
            metadata: Custom metadata dict
        
        Returns:
            Dict with success status and price data
        """
        self.logger.info(
            f"Creating price for product {product_id}",
            {"amount_cents": amount_cents, "interval": interval}
        )
        
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'created_by': 'stripe_lib',
            'created_at': datetime.utcnow().isoformat()
        })
        
        return self._retry_with_backoff(
            operation=stripe.Price.create,
            operation_name=f"CREATE_PRICE[{product_id}]",
            product=product_id,
            unit_amount=amount_cents,
            currency=currency,
            recurring={
                'interval': interval,
                'interval_count': interval_count
            },
            metadata=metadata
        )
    
    def create_payment_link(
        self,
        price_id: str,
        quantity: int = 1,
        after_completion_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a Payment Link for easy checkout.
        
        Args:
            price_id: Stripe price ID (price_xxx)
            quantity: Quantity of items
            after_completion_url: Redirect URL after successful payment
            metadata: Custom metadata dict
        
        Returns:
            Dict with success status and payment link data
        """
        self.logger.info(f"Creating payment link for price {price_id}")
        
        params = {
            'line_items': [{
                'price': price_id,
                'quantity': quantity
            }]
        }
        
        if after_completion_url:
            params['after_completion'] = {
                'type': 'redirect',
                'redirect': {'url': after_completion_url}
            }
        
        if metadata:
            params['metadata'] = metadata
        
        return self._retry_with_backoff(
            operation=stripe.PaymentLink.create,
            operation_name=f"CREATE_PAYMENT_LINK[{price_id}]",
            **params
        )
    
    # ========================================
    # SUBSCRIPTION OPERATIONS
    # ========================================
    
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID (sub_xxx)
            at_period_end: If True, cancel at end of billing period (default)
                          If False, cancel immediately
        
        Returns:
            Dict with success status and cancellation data
        """
        self.logger.info(
            f"Canceling subscription {subscription_id}",
            {"at_period_end": at_period_end}
        )
        
        if at_period_end:
            # Cancel at period end
            return self._retry_with_backoff(
                operation=stripe.Subscription.modify,
                operation_name=f"CANCEL_SUBSCRIPTION[{subscription_id}]",
                subscription_id=subscription_id,
                cancel_at_period_end=True
            )
        else:
            # Cancel immediately
            return self._retry_with_backoff(
                operation=stripe.Subscription.delete,
                operation_name=f"CANCEL_SUBSCRIPTION_IMMEDIATE[{subscription_id}]",
                subscription_id=subscription_id
            )
    
    def create_trial_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 14,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe subscription with a trial period.

        Args:
            customer_id: Stripe customer ID (cus_xxx)
            price_id: Stripe price ID (price_xxx)
            trial_days: Number of free trial days (default: 14)
            metadata: Optional metadata dict (include user_id for webhook routing)

        Returns:
            Dict with success status and subscription data
        """
        self.logger.info(
            f"Creating trial subscription for customer {customer_id}",
            {"price_id": price_id, "trial_days": trial_days}
        )
        params: Dict[str, Any] = {
            "customer": customer_id,
            "items": [{"price": price_id}],
            "trial_period_days": trial_days,
        }
        if metadata:
            params["metadata"] = metadata
        return self._retry_with_backoff(
            operation=stripe.Subscription.create,
            operation_name=f"CREATE_TRIAL_SUBSCRIPTION[{customer_id}]",
            **params,
        )

    # ========================================
    # WEBHOOK OPERATIONS
    # ========================================

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature_header: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature.
        
        Args:
            payload: Raw request body (bytes)
            signature_header: Value of Stripe-Signature header
        
        Returns:
            Dict with success status and event data (if valid)
        """
        if not self.config.stripe_webhook_secret:
            self.logger.error("Cannot verify webhook - stripe_webhook_secret not configured")
            return {
                "success": False,
                "error": "stripe_webhook_secret not configured"
            }
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature_header,
                self.config.stripe_webhook_secret
            )
            
            self.logger.info(
                f"Webhook verified successfully",
                {"event_type": event['type'], "event_id": event['id']}
            )
            
            self.logger.debug("Webhook event details", {"event": event})
            
            return {
                "success": True,
                "event": event
            }
        
        except stripe.error.SignatureVerificationError as e:
            self.logger.error("Webhook signature verification failed", {"error": str(e)})
            return {
                "success": False,
                "error": "Invalid signature",
                "detail": str(e)
            }
        
        except Exception as e:
            self.logger.error("Webhook verification error", {"error": str(e)})
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_webhook_event(
        self,
        event: Dict[str, Any],
        handlers: Optional[Dict[str, callable]] = None
    ) -> Dict[str, Any]:
        """
        Route webhook event to appropriate handler.
        
        Args:
            event: Stripe event dict (from verify_webhook_signature)
            handlers: Dict mapping event_type to handler function
                     Example: {'customer.subscription.created': my_handler}
        
        Returns:
            Dict with success status and handler result
        """
        event_type = event.get('type')
        event_id = event.get('id')
        
        self.logger.info(f"Handling webhook event", {"type": event_type, "id": event_id})
        
        if not handlers or event_type not in handlers:
            self.logger.debug(f"No handler registered for event type: {event_type}")
            return {
                "success": True,
                "handled": False,
                "event_type": event_type,
                "message": "No handler registered"
            }
        
        handler = handlers[event_type]
        
        try:
            self.logger.debug(f"Executing handler for {event_type}")
            result = handler(event)
            
            self.logger.info(f"Handler executed successfully", {"event_type": event_type})
            
            return {
                "success": True,
                "handled": True,
                "event_type": event_type,
                "handler_result": result
            }
        
        except Exception as e:
            self.logger.error(
                f"Handler failed for {event_type}",
                {"error": str(e), "event_id": event_id}
            )
            
            return {
                "success": False,
                "handled": True,
                "event_type": event_type,
                "error": str(e)
            }
    
    # ========================================
    # CONVENIENCE METHODS
    # ========================================
    
    def create_complete_subscription_product(
        self,
        business_name: str,
        monthly_price_dollars: float,
        annual_price_dollars: Optional[float] = None,
        description: str = "",
        after_completion_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convenience method: Create product + prices + payment links in one call.
        
        Args:
            business_name: Name of business
            monthly_price_dollars: Monthly price in dollars (e.g., 49.00)
            annual_price_dollars: Annual price in dollars (optional)
            description: Product description
            after_completion_url: Post-checkout redirect URL
        
        Returns:
            Dict with all created resources
        """
        self.logger.info(f"Creating complete subscription setup for {business_name}")
        
        result = {
            "success": True,
            "business_name": business_name,
            "product": None,
            "monthly_price": None,
            "monthly_payment_link": None,
            "annual_price": None,
            "annual_payment_link": None,
            "errors": []
        }
        
        # 1. Create product
        product_result = self.create_subscription_product(
            business_name=business_name,
            description=description
        )
        
        if not product_result["success"]:
            result["success"] = False
            result["errors"].append(f"Product creation failed: {product_result.get('error')}")
            return result
        
        result["product"] = product_result["data"]
        product_id = product_result["data"]["id"]
        
        # 2. Create monthly price
        monthly_cents = int(monthly_price_dollars * 100)
        monthly_price_result = self.create_price(
            product_id=product_id,
            amount_cents=monthly_cents,
            interval="month"
        )
        
        if not monthly_price_result["success"]:
            result["success"] = False
            result["errors"].append(f"Monthly price creation failed: {monthly_price_result.get('error')}")
            return result
        
        result["monthly_price"] = monthly_price_result["data"]
        
        # 3. Create monthly payment link
        monthly_link_result = self.create_payment_link(
            price_id=monthly_price_result["data"]["id"],
            after_completion_url=after_completion_url
        )
        
        if not monthly_link_result["success"]:
            result["success"] = False
            result["errors"].append(f"Monthly payment link failed: {monthly_link_result.get('error')}")
            return result
        
        result["monthly_payment_link"] = monthly_link_result["data"]["url"]
        
        # 4. Create annual price (if specified)
        if annual_price_dollars:
            annual_cents = int(annual_price_dollars * 100)
            annual_price_result = self.create_price(
                product_id=product_id,
                amount_cents=annual_cents,
                interval="year"
            )
            
            if not annual_price_result["success"]:
                result["success"] = False
                result["errors"].append(f"Annual price creation failed: {annual_price_result.get('error')}")
                return result
            
            result["annual_price"] = annual_price_result["data"]
            
            # 5. Create annual payment link
            annual_link_result = self.create_payment_link(
                price_id=annual_price_result["data"]["id"],
                after_completion_url=after_completion_url
            )
            
            if not annual_link_result["success"]:
                result["success"] = False
                result["errors"].append(f"Annual payment link failed: {annual_link_result.get('error')}")
                return result
            
            result["annual_payment_link"] = annual_link_result["data"]["url"]
        
        self.logger.info(f"Complete subscription setup SUCCESS for {business_name}")

        return result

    # ========================================
    # COUPON & DISCOUNT OPERATIONS
    # WHY P1: Promo codes drive acquisition. Discount codes reduce churn.
    #         All coupon logic must flow through this adapter — no direct
    #         stripe.Coupon calls from business logic.
    # ========================================

    def create_coupon(
        self,
        name: str,
        percent_off: Optional[float] = None,
        amount_off: Optional[int] = None,
        currency: str = "usd",
        duration: str = "once",
        max_redemptions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe coupon for discounts.

        Must specify exactly one of percent_off OR amount_off.

        Args:
            name: Human-readable coupon name (e.g. "LAUNCH50")
            percent_off: Percentage discount (e.g. 50.0 = 50% off)
            amount_off: Fixed discount in cents (e.g. 1000 = $10 off)
            currency: Required when amount_off is set (default: usd)
            duration: 'once' | 'repeating' | 'forever'
            max_redemptions: Cap total uses (None = unlimited)

        Returns:
            Dict with success status and coupon data
        """
        if not percent_off and not amount_off:
            return {"success": False, "error": "Must specify percent_off or amount_off"}
        if percent_off and amount_off:
            return {"success": False, "error": "Specify either percent_off or amount_off, not both"}

        self.logger.info(f"Creating coupon: {name}", {
            "percent_off": percent_off, "amount_off": amount_off, "duration": duration
        })

        params: Dict[str, Any] = {"name": name, "duration": duration}
        if percent_off:
            params["percent_off"] = percent_off
        else:
            params["amount_off"] = amount_off
            params["currency"] = currency
        if max_redemptions:
            params["max_redemptions"] = max_redemptions

        return self._retry_with_backoff(
            operation=stripe.Coupon.create,
            operation_name=f"CREATE_COUPON[{name}]",
            **params,
        )

    def create_promo_code(
        self,
        coupon_id: str,
        code: Optional[str] = None,
        max_redemptions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a human-readable promo code that maps to a coupon.

        Args:
            coupon_id: Stripe coupon ID (e.g. "LAUNCH50_id")
            code: The code customers enter (e.g. "LAUNCH50"). Auto-generated if None.
            max_redemptions: Cap redemptions on this code specifically

        Returns:
            Dict with success status and promo code data
        """
        self.logger.info(f"Creating promo code for coupon {coupon_id}", {"code": code})

        params: Dict[str, Any] = {"coupon": coupon_id}
        if code:
            params["code"] = code
        if max_redemptions:
            params["max_redemptions"] = max_redemptions

        return self._retry_with_backoff(
            operation=stripe.PromotionCode.create,
            operation_name=f"CREATE_PROMO_CODE[{coupon_id}]",
            **params,
        )

    def apply_coupon_to_subscription(
        self,
        subscription_id: str,
        coupon_id: str,
    ) -> Dict[str, Any]:
        """
        Apply a coupon to an existing subscription.

        Args:
            subscription_id: Stripe subscription ID (sub_xxx)
            coupon_id: Stripe coupon ID to apply

        Returns:
            Dict with success status and updated subscription data
        """
        self.logger.info(f"Applying coupon {coupon_id} to subscription {subscription_id}")

        return self._retry_with_backoff(
            operation=stripe.Subscription.modify,
            operation_name=f"APPLY_COUPON[{subscription_id}]",
            sid=subscription_id,
            coupon=coupon_id,
        )

    def retrieve_coupon(self, coupon_id: str) -> Dict[str, Any]:
        """
        Retrieve a coupon by ID.

        Args:
            coupon_id: Stripe coupon ID

        Returns:
            Dict with success status and coupon data
        """
        self.logger.info(f"Retrieving coupon {coupon_id}")
        return self._retry_with_backoff(
            operation=stripe.Coupon.retrieve,
            operation_name=f"RETRIEVE_COUPON[{coupon_id}]",
            id=coupon_id,
        )

    def list_coupons(self) -> Dict[str, Any]:
        """
        List all coupons in the Stripe account.

        Returns:
            Dict with success status and list of coupons
        """
        self.logger.info("Listing all coupons")
        return self._retry_with_backoff(
            operation=stripe.Coupon.list,
            operation_name="LIST_COUPONS",
        )

    def delete_coupon(self, coupon_id: str) -> Dict[str, Any]:
        """
        Delete (archive) a coupon. Existing subscriptions using it are unaffected.

        Args:
            coupon_id: Stripe coupon ID to delete

        Returns:
            Dict with success status and deletion confirmation
        """
        self.logger.info(f"Deleting coupon {coupon_id}")
        return self._retry_with_backoff(
            operation=stripe.Coupon.delete,
            operation_name=f"DELETE_COUPON[{coupon_id}]",
            sid=coupon_id,
        )

    # ========================================
    # USAGE METERING OPERATIONS
    # WHY P1: Usage-based pricing allows charging by consumption
    #         (API calls, AI tokens, reports generated). Uses the
    #         Stripe Billing Meter API (stripe-python 7+).
    # ========================================

    def create_meter(
        self,
        display_name: str,
        event_name: str,
        value_settings_event_payload_key: str = "value",
        default_aggregation: str = "sum",
    ) -> Dict[str, Any]:
        """
        Create a Stripe Billing Meter — defines what we're measuring.

        Args:
            display_name: Human name for the meter (e.g. "API Calls")
            event_name: Event identifier to match MeterEvents (e.g. "api_call")
            value_settings_event_payload_key: Payload key that holds the quantity
            default_aggregation: How to aggregate events ('sum' | 'count')

        Returns:
            Dict with success status and meter data (id = meter_xxx)
        """
        self.logger.info(f"Creating billing meter: {display_name}", {
            "event_name": event_name, "aggregation": default_aggregation
        })

        return self._retry_with_backoff(
            operation=stripe.billing.Meter.create,
            operation_name=f"CREATE_METER[{event_name}]",
            display_name=display_name,
            event_name=event_name,
            default_aggregation={"formula": default_aggregation},
            value_settings={"event_payload_key": value_settings_event_payload_key},
        )

    def report_usage(
        self,
        event_name: str,
        value: int,
        stripe_customer_id: str,
        timestamp: Optional[int] = None,
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Report a usage event to Stripe Billing Metering.

        Call this after each billable action. Stripe aggregates events
        per meter and bills the customer at period end.

        Args:
            event_name: Must match the meter's event_name (e.g. "api_call")
            value: Quantity for this event (e.g. 1 per call, or token count)
            stripe_customer_id: The Stripe customer ID (cus_xxx)
            timestamp: Unix timestamp (defaults to now)
            identifier: Idempotency key to prevent duplicate reporting

        Returns:
            Dict with success status and meter event data
        """
        self.logger.info(f"Reporting usage event: {event_name}", {
            "value": value, "customer": stripe_customer_id
        })

        params: Dict[str, Any] = {
            "event_name": event_name,
            "payload": {
                "stripe_customer_id": stripe_customer_id,
                "value": str(value),
            },
        }
        if timestamp:
            params["timestamp"] = timestamp
        if identifier:
            params["identifier"] = identifier

        return self._retry_with_backoff(
            operation=stripe.billing.MeterEvent.create,
            operation_name=f"REPORT_USAGE[{event_name}]",
            **params,
        )

    def get_meter_event_summaries(
        self,
        meter_id: str,
        customer: str,
        start_time: int,
        end_time: int,
    ) -> Dict[str, Any]:
        """
        Get aggregated usage summaries for a meter and customer.

        Args:
            meter_id: Stripe meter ID (meter_xxx)
            customer: Stripe customer ID (cus_xxx)
            start_time: Period start as Unix timestamp
            end_time: Period end as Unix timestamp

        Returns:
            Dict with success status and event summary data
        """
        self.logger.info(f"Getting meter summaries for meter {meter_id}", {
            "customer": customer
        })

        return self._retry_with_backoff(
            operation=stripe.billing.Meter.list_event_summaries,
            operation_name=f"GET_METER_SUMMARIES[{meter_id}]",
            id=meter_id,
            customer=customer,
            start_time=start_time,
            end_time=end_time,
        )

    def create_metered_price(
        self,
        product_id: str,
        unit_amount: int,
        billing_scheme: str = "per_unit",
        currency: str = "usd",
    ) -> Dict[str, Any]:
        """
        Create a metered (usage-based) price for a product.

        Args:
            product_id: Stripe product ID (prod_xxx)
            unit_amount: Price per unit in cents (e.g. 1 = $0.01/unit)
            billing_scheme: 'per_unit' | 'tiered'
            currency: Currency code (default: usd)

        Returns:
            Dict with success status and metered price data
        """
        self.logger.info(f"Creating metered price for product {product_id}", {
            "unit_amount": unit_amount, "currency": currency
        })

        return self._retry_with_backoff(
            operation=stripe.Price.create,
            operation_name=f"CREATE_METERED_PRICE[{product_id}]",
            product=product_id,
            unit_amount=unit_amount,
            currency=currency,
            billing_scheme=billing_scheme,
            recurring={
                "interval": "month",
                "usage_type": "metered",
            },
        )

    def create_metered_subscription_item(
        self,
        subscription_id: str,
        price_id: str,
    ) -> Dict[str, Any]:
        """
        Add a metered price as a line item to an existing subscription.

        Args:
            subscription_id: Stripe subscription ID (sub_xxx)
            price_id: Metered price ID to add (price_xxx)

        Returns:
            Dict with success status and subscription item data
        """
        self.logger.info(f"Adding metered item to subscription {subscription_id}", {
            "price_id": price_id
        })

        return self._retry_with_backoff(
            operation=stripe.SubscriptionItem.create,
            operation_name=f"CREATE_METERED_ITEM[{subscription_id}]",
            subscription=subscription_id,
            price=price_id,
        )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_stripe_lib(config_path: str) -> StripeLib:
    """
    Convenience function to load StripeLib from config file.
    
    Args:
        config_path: Path to JSON config file
    
    Returns:
        Initialized StripeLib instance
    """
    config = StripeConfig(config_path=config_path)
    return StripeLib(config)


def load_stripe_lib_from_dict(config_dict: Dict) -> StripeLib:
    """
    Convenience function to load StripeLib from config dict.

    Args:
        config_dict: Config dictionary

    Returns:
        Initialized StripeLib instance
    """
    config = StripeConfig(config_dict=config_dict)
    return StripeLib(config)


# ============================================================
# STRIPE CONNECT — ESCROW & SPLIT PAYMENTS
# WHY P1: Marketplace businesses need to route payments to sellers/creators.
#         Stripe Connect is the only robust option for platform-level
#         payment splitting. This is the adapter — nothing calls Stripe
#         Connect APIs directly.
# ============================================================

class StripeConnectLib:
    """
    Stripe Connect adapter for marketplace escrow and split payments.

    Stripe Connect lets a platform collect payments and distribute funds
    to connected accounts (sellers, creators, service providers).

    Usage:
        connect = load_stripe_connect_lib('config/stripe_config.json')
        # Onboard a seller:
        account = connect.create_connected_account(email="seller@example.com")
        link = connect.create_account_onboarding_link(account["data"]["id"], ...)
        # Charge buyer, split payment:
        payment = connect.create_payment_intent_with_split(
            amount=10000,  # $100.00
            currency="usd",
            application_fee_amount=1000,  # $10 platform fee
            connected_account_id=account["data"]["id"],
        )
    """

    def __init__(self, config: StripeConfig):
        self.config = config
        self.logger = StripeLibLogger(
            log_level=config.log_level,
            log_file=config.log_file,
        )
        stripe.api_key = config.stripe_secret_key
        self.logger.info("StripeConnectLib initialized", {"account": config.account_name})

    def _retry(self, operation, name, **kwargs) -> Dict[str, Any]:
        """Thin retry wrapper re-using stripe error handling pattern."""
        for attempt in range(1, 4):
            try:
                start = time.time()
                result = operation(**kwargs)
                elapsed = round(time.time() - start, 3)
                self.logger.info(f"{name} SUCCESS", {"attempt": attempt, "elapsed_sec": elapsed})
                return {"success": True, "data": result, "attempt": attempt}
            except stripe.error.StripeError as e:
                self.logger.error(f"{name} FAILED attempt {attempt}", {"error": str(e)})
                if attempt == 3:
                    return {
                        "success": False,
                        "error": str(e),
                        "stripe_error_type": type(e).__name__,
                    }
                time.sleep(2 ** (attempt - 1))
            except Exception as e:
                self.logger.error(f"{name} UNEXPECTED ERROR", {"error": str(e)})
                return {"success": False, "error": str(e), "error_type": type(e).__name__}

    def create_connected_account(
        self,
        email: str,
        country: str = "US",
        account_type: str = "express",
    ) -> Dict[str, Any]:
        """
        Create a Stripe Connect account for a seller/creator.

        Express accounts are fastest to onboard (Stripe-hosted UI).
        Standard accounts give sellers full Stripe dashboard access.

        Args:
            email: Seller's email address
            country: Two-letter country code (default: US)
            account_type: 'express' (recommended) | 'standard' | 'custom'

        Returns:
            Dict with success status and account data (id = acct_xxx)
        """
        self.logger.info(f"Creating connected account for {email}", {
            "country": country, "type": account_type
        })
        return self._retry(
            operation=stripe.Account.create,
            name=f"CREATE_CONNECTED_ACCOUNT[{email}]",
            type=account_type,
            email=email,
            country=country,
        )

    def create_account_onboarding_link(
        self,
        account_id: str,
        refresh_url: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """
        Create the onboarding link for a connected account.

        Send this URL to the seller — they complete Stripe's KYC flow.
        Links expire after a few minutes; generate fresh ones on demand.

        Args:
            account_id: Connected account ID (acct_xxx)
            refresh_url: URL to redirect if the link expires
            return_url: URL to redirect after successful onboarding

        Returns:
            Dict with success status and account link (contains .url)
        """
        self.logger.info(f"Creating onboarding link for {account_id}")
        return self._retry(
            operation=stripe.AccountLink.create,
            name=f"CREATE_ONBOARDING_LINK[{account_id}]",
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )

    def create_payment_intent_with_split(
        self,
        amount: int,
        currency: str,
        application_fee_amount: int,
        connected_account_id: str,
    ) -> Dict[str, Any]:
        """
        Create a payment intent that splits revenue with a connected account.

        The buyer pays `amount`. The platform keeps `application_fee_amount`.
        The seller receives `amount - application_fee_amount`.

        Args:
            amount: Total charge in cents (e.g. 10000 = $100.00)
            currency: Currency code (e.g. 'usd')
            application_fee_amount: Platform fee in cents (e.g. 1000 = $10)
            connected_account_id: Destination connected account (acct_xxx)

        Returns:
            Dict with success status and PaymentIntent data (contains client_secret)
        """
        self.logger.info("Creating split payment intent", {
            "amount": amount, "fee": application_fee_amount,
            "destination": connected_account_id,
        })
        return self._retry(
            operation=stripe.PaymentIntent.create,
            name=f"CREATE_SPLIT_PAYMENT[{connected_account_id}]",
            amount=amount,
            currency=currency,
            application_fee_amount=application_fee_amount,
            transfer_data={"destination": connected_account_id},
        )

    def transfer_to_connected_account(
        self,
        amount: int,
        currency: str,
        destination_account_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transfer funds from the platform to a connected account.

        Use this for manual payouts or post-escrow releases.

        Args:
            amount: Amount to transfer in cents
            currency: Currency code (e.g. 'usd')
            destination_account_id: Connected account to receive funds (acct_xxx)
            description: Optional description for the transfer

        Returns:
            Dict with success status and transfer data
        """
        self.logger.info(f"Transferring {amount} to {destination_account_id}")
        params: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "destination": destination_account_id,
        }
        if description:
            params["description"] = description

        return self._retry(
            operation=stripe.Transfer.create,
            name=f"TRANSFER[{destination_account_id}]",
            **params,
        )

    def retrieve_connected_account(self, account_id: str) -> Dict[str, Any]:
        """
        Retrieve a connected account's details and payout status.

        Args:
            account_id: Connected account ID (acct_xxx)

        Returns:
            Dict with success status and account details
        """
        self.logger.info(f"Retrieving connected account {account_id}")
        return self._retry(
            operation=stripe.Account.retrieve,
            name=f"RETRIEVE_ACCOUNT[{account_id}]",
            id=account_id,
        )

    def list_connected_accounts(self) -> Dict[str, Any]:
        """
        List all connected accounts on the platform.

        Returns:
            Dict with success status and list of accounts
        """
        self.logger.info("Listing all connected accounts")
        return self._retry(
            operation=stripe.Account.list,
            name="LIST_CONNECTED_ACCOUNTS",
        )


def load_stripe_connect_lib(config_path: str) -> StripeConnectLib:
    """
    Load StripeConnectLib from a config file.

    Args:
        config_path: Path to JSON config file (same format as stripe_lib)

    Returns:
        Initialized StripeConnectLib instance
    """
    config = StripeConfig(config_path=config_path)
    return StripeConnectLib(config)
