"""
webhook_entitlements.py - Stripe Webhook → Entitlement Sync

WHY: Stripe fires webhooks when subscriptions change. This handler
     translates those events into entitlement grants/revocations.
     It's the ONLY place that writes to user_entitlements from Stripe.

WEBHOOK EVENTS HANDLED:
  - checkout.session.completed      → new purchase, grant entitlements
  - customer.subscription.updated   → plan change, sync entitlements
  - customer.subscription.deleted   → cancelled, revoke all
  - invoice.payment_failed          → payment failed, revoke all

SETUP:
  In Stripe dashboard → Webhooks → Add endpoint:
    URL: https://yourdomain.com/api/webhooks/stripe
    Events: checkout.session.completed, customer.subscription.updated,
            customer.subscription.deleted, invoice.payment_failed
"""

import logging
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from core.entitlements import sync_entitlements_from_stripe, revoke_all_entitlements
from core.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================
# HELPERS
# ============================================================

def _get_stripe_secret() -> str:
    """WHY: Read once, don't hardcode."""
    config = get_config()
    return config.get("stripe", {}).get("secret_key", "")


def _get_webhook_secret() -> str:
    """WHY separate from API key: Stripe uses a different secret for webhooks."""
    config = get_config()
    return config.get("stripe", {}).get("webhook_secret", "")


def _get_auth0_user_id_for_stripe_customer(
    stripe_customer_id: str,
    db: Session
) -> str:
    """
    Look up which Auth0 user owns this Stripe customer ID.
    WHY: Stripe knows the customer, we need the Auth0 user to update entitlements.

    Assumes User model has stripe_customer_id field.
    """
    from models import User  # Import here to avoid circular imports

    user = db.query(User).filter(
        User.stripe_customer_id == stripe_customer_id
    ).first()

    if not user:
        raise ValueError(f"No user found for Stripe customer: {stripe_customer_id}")

    return user.auth0_id


def _get_active_product_ids(subscription: dict) -> list:
    """
    Extract active product IDs from a Stripe subscription object.
    WHY: Subscription items contain prices which reference products.
    """
    product_ids = []
    for item in subscription.get("items", {}).get("data", []):
        price = item.get("price", {})
        product_id = price.get("product")
        if product_id:
            product_ids.append(product_id)
    return product_ids


# ============================================================
# WEBHOOK ENDPOINT
# ============================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives all Stripe webhook events.
    Verifies signature → dispatches to handler → updates entitlements.

    WHY verify signature: Prevent fake webhook calls.
    Anyone who knows your URL could fake a purchase without this.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = _get_webhook_secret()

    # Verify the webhook came from Stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        logger.error("Stripe webhook: invalid payload")
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Stripe webhook: invalid signature")
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    logger.info(f"Stripe webhook received: {event_type}")

    # Dispatch to appropriate handler
    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event["data"]["object"], db)

        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(event["data"]["object"], db)

        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event["data"]["object"], db)

        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(event["data"]["object"], db)

        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

    except ValueError as e:
        # User not found - log but don't fail (Stripe will retry otherwise)
        logger.error(f"Webhook handler error: {e}")
        return {"status": "error", "message": str(e)}

    except Exception as e:
        logger.error(f"Unexpected webhook error: {e}")
        raise HTTPException(500, "Internal error processing webhook")

    return {"status": "ok", "event": event_type}


# ============================================================
# EVENT HANDLERS
# ============================================================

async def _handle_checkout_completed(session: dict, db: Session):
    """
    New purchase completed via Stripe Checkout.
    WHY: checkout.session.completed fires once on successful payment.
    """
    stripe_customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not stripe_customer_id:
        logger.warning("checkout.session.completed: no customer ID")
        return

    # Fetch full subscription to get product IDs
    if subscription_id:
        stripe.api_key = _get_stripe_secret()
        subscription = stripe.Subscription.retrieve(subscription_id)
        active_product_ids = _get_active_product_ids(subscription)
    else:
        # One-time payment - get product from line items
        stripe.api_key = _get_stripe_secret()
        line_items = stripe.checkout.Session.list_line_items(session["id"])
        active_product_ids = [
            item["price"]["product"]
            for item in line_items.get("data", [])
            if item.get("price", {}).get("product")
        ]

    auth0_user_id = _get_auth0_user_id_for_stripe_customer(stripe_customer_id, db)

    granted = sync_entitlements_from_stripe(
        auth0_user_id=auth0_user_id,
        stripe_customer_id=stripe_customer_id,
        active_product_ids=active_product_ids,
        db=db
    )

    logger.info(f"Checkout complete: {auth0_user_id} granted {granted}")


async def _handle_subscription_updated(subscription: dict, db: Session):
    """
    Subscription changed (upgrade, downgrade, renewal).
    WHY: customer.subscription.updated fires on any subscription change.
    Sync entitlements to match current subscription state.
    """
    stripe_customer_id = subscription.get("customer")
    status = subscription.get("status")

    if not stripe_customer_id:
        logger.warning("subscription.updated: no customer ID")
        return

    auth0_user_id = _get_auth0_user_id_for_stripe_customer(stripe_customer_id, db)

    if status in ("active", "trialing"):
        # Subscription is active - sync entitlements
        active_product_ids = _get_active_product_ids(subscription)
        granted = sync_entitlements_from_stripe(
            auth0_user_id=auth0_user_id,
            stripe_customer_id=stripe_customer_id,
            active_product_ids=active_product_ids,
            db=db
        )
        logger.info(f"Subscription updated: {auth0_user_id} synced {granted}")

    elif status in ("canceled", "unpaid", "past_due"):
        # Subscription is no longer valid - revoke everything
        count = revoke_all_entitlements(auth0_user_id, db)
        logger.info(f"Subscription {status}: revoked {count} entitlements for {auth0_user_id}")


async def _handle_subscription_deleted(subscription: dict, db: Session):
    """
    Subscription cancelled entirely.
    WHY: customer.subscription.deleted fires when subscription ends.
    Always revoke all features.
    """
    stripe_customer_id = subscription.get("customer")

    if not stripe_customer_id:
        logger.warning("subscription.deleted: no customer ID")
        return

    auth0_user_id = _get_auth0_user_id_for_stripe_customer(stripe_customer_id, db)
    count = revoke_all_entitlements(auth0_user_id, db)
    logger.info(f"Subscription deleted: revoked {count} entitlements for {auth0_user_id}")


async def _handle_payment_failed(invoice: dict, db: Session):
    """
    Payment failed on renewal.
    WHY: invoice.payment_failed fires when a renewal charge fails.
    Revoke access until payment is resolved.
    Grace period decisions are a business choice - we revoke immediately.
    """
    stripe_customer_id = invoice.get("customer")

    if not stripe_customer_id:
        logger.warning("payment_failed: no customer ID")
        return

    auth0_user_id = _get_auth0_user_id_for_stripe_customer(stripe_customer_id, db)
    count = revoke_all_entitlements(auth0_user_id, db)
    logger.info(f"Payment failed: revoked {count} entitlements for {auth0_user_id}")
