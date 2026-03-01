"""
sentry_lib.py - Sentry Error Tracking Adapter
===============================================

WHY: Platform Rule #2 requires every capability to have a single adapter library.
     This is the Sentry adapter. Nothing in the platform calls sentry_sdk directly —
     everything goes through this module.

     Keeping Sentry access here means:
     - Swap Sentry for another error tracker by editing only this file
     - All context-setting follows the same API regardless of underlying tool
     - Tests mock this module, not sentry_sdk internals

HOW:
    1. Call init_sentry() once at app startup
    2. Call set_tenant_context() per request (via monitoring middleware)
    3. Errors are auto-captured by Sentry SDK
    4. Use capture_error() for handled exceptions you still want tracked

USAGE:
    from sentry_lib import init_sentry, set_tenant_context, capture_error

    # App startup:
    init_sentry(
        dsn=os.getenv("SENTRY_DSN"),
        environment="production",
        release="1.0.0"
    )

    # Per request (in middleware):
    set_tenant_context(tenant_id="courtdominion", user_id="auth0|abc123")

    # For handled errors you still want visibility on:
    try:
        stripe.charge(...)
    except StripeError as e:
        capture_error(e, extra={"tenant_id": tenant_id, "amount": amount})
"""

import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


# ============================================================
# INITIALIZATION
# WHY: Core init without FastAPI-specific integrations.
#      monitoring.py adds those on top. This way sentry_lib
#      can be used in non-FastAPI contexts (scripts, workers).
# ============================================================

def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "production",
    release: str = "unknown",
    traces_sample_rate: float = 0.1,
    integrations: Optional[List] = None,
    before_send=None,
) -> bool:
    """
    Initialize Sentry error tracking.

    Args:
        dsn: Sentry DSN. If None, reads SENTRY_DSN env var.
        environment: deployment environment (production, staging, development)
        release: app version/release tag
        traces_sample_rate: % of requests to trace (0.1 = 10%). Keep low on free tier.
        integrations: extra Sentry SDK integrations (e.g. FastApiIntegration)
        before_send: optional filter function — return None to drop event

    Returns:
        True if Sentry initialized successfully, False otherwise.
    """
    dsn = dsn or os.getenv("SENTRY_DSN")

    if not dsn:
        logger.warning(
            "SENTRY_DSN not set — error tracking disabled. "
            "Get your DSN from sentry.io (free 5K errors/month)."
        )
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        all_integrations = [
            LoggingIntegration(
                level=logging.WARNING,    # WARNING+ goes to breadcrumbs
                event_level=logging.ERROR # ERROR creates a Sentry event
            ),
        ]
        if integrations:
            all_integrations.extend(integrations)

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            integrations=all_integrations,
            send_default_pii=False,  # Never send PII to Sentry
            before_send=before_send or default_before_send_filter,
        )

        logger.info(f"✓ Sentry initialized (env={environment} release={release})")
        return True

    except ImportError:
        logger.error(
            "sentry-sdk not installed. "
            "Run: pip install 'sentry-sdk[fastapi]' --break-system-packages"
        )
        return False
    except Exception as e:
        logger.error(f"Sentry initialization failed: {e}")
        return False


# ============================================================
# NOISE FILTER
# WHY: Sentry free tier has 5K errors/month. Don't waste quota
#      on expected events like usage limits and budget exceeded.
# ============================================================

def default_before_send_filter(event: dict, hint: dict) -> Optional[dict]:
    """
    Drop noisy/expected events before sending to Sentry.
    Returns None to drop, or the event dict to send.

    Drops:
    - Warning-level log events (too noisy, fills quota fast)
    - Expected business exceptions (UsageLimitExceeded, BudgetExceededError, 4xx HTTPExceptions)
    """
    # Drop warning-level events — they're breadcrumbs, not bugs
    if event.get("level") == "warning":
        return None

    # Drop known/expected exceptions that aren't bugs
    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type = exc_info[0]
        if exc_type and exc_type.__name__ in (
            "UsageLimitExceeded",     # Expected: user hit their plan limit
            "BudgetExceededError",    # Expected: tenant hit AI spend limit
            "HTTPException",          # Expected: handled 4xx responses
        ):
            return None

    return event


# ============================================================
# CONTEXT SETTING
# WHY: Every Sentry error should show which tenant was affected.
#      Without tenant context you can't answer "who was impacted?"
# ============================================================

def set_tenant_context(tenant_id: str, user_id: Optional[str] = None) -> None:
    """
    Attach tenant info to all Sentry errors in the current request.

    Call this in your request middleware after establishing tenant identity.
    This context appears in Sentry under "Additional Data" → "tenant".

    Args:
        tenant_id: The tenant identifier (e.g. "courtdominion")
        user_id: Auth0 user_id if known (e.g. "auth0|abc123")
    """
    try:
        import sentry_sdk

        sentry_sdk.set_context("tenant", {
            "tenant_id": tenant_id,
            "user_id": user_id or "anonymous",
        })

        # Tag allows filtering Sentry issues by tenant in the dashboard
        sentry_sdk.set_tag("tenant_id", tenant_id)

        if user_id:
            sentry_sdk.set_user({"id": user_id, "tenant": tenant_id})

    except ImportError:
        pass  # Sentry not installed — silent fail, don't break the request
    except Exception as e:
        logger.debug(f"Could not set Sentry tenant context: {e}")


def set_feature_context(feature: str, extra: Optional[Dict] = None) -> None:
    """
    Tag the current request with the feature being executed.
    Helps answer "which feature caused this error?" in Sentry.

    Args:
        feature: feature name (e.g. "game_summary", "export_report")
        extra: optional additional context dict
    """
    try:
        import sentry_sdk
        sentry_sdk.set_tag("feature", feature)
        if extra:
            sentry_sdk.set_context("feature_context", extra)
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Could not set Sentry feature context: {e}")


# ============================================================
# MANUAL ERROR CAPTURE
# WHY: For handled exceptions that indicate real problems.
#      Auto-capture covers crashes; this covers degraded states.
# ============================================================

def capture_error(
    error: Exception,
    extra: Optional[Dict[str, Any]] = None,
    level: str = "error",
) -> Optional[str]:
    """
    Manually send a caught exception to Sentry.

    Use this for exceptions you handle (so they don't crash the request)
    but still want visibility on. Example: Stripe API flakiness.

    Args:
        error: The exception instance
        extra: Extra context dict (tenant_id, amount, etc.)
        level: Sentry level: "error" | "warning" | "info"

    Returns:
        Sentry event ID string (for support tickets), or None if unavailable.

    Usage:
        try:
            stripe.charge(amount)
        except StripeError as e:
            capture_error(e, extra={"tenant_id": tenant_id, "amount": amount})
            # Continue with fallback behavior
    """
    try:
        import sentry_sdk

        with sentry_sdk.new_scope() as scope:
            scope.level = level
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            event_id = sentry_sdk.capture_exception(error)
            logger.debug(f"Error captured in Sentry: event_id={event_id}")
            return event_id

    except ImportError:
        # Sentry not installed — fall back to plain logging
        logger.error(f"[UNTRACKED] {type(error).__name__}: {error}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to capture error in Sentry: {e}")
        return None


def capture_message(
    message: str,
    level: str = "info",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Send a non-exception message to Sentry.
    Use for significant events (budget alerts, milestone tracking).

    Args:
        message: Human-readable message
        level: "info" | "warning" | "error"
        extra: Optional extra context
    """
    try:
        import sentry_sdk
        with sentry_sdk.new_scope() as scope:
            scope.level = level
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_message(message)
    except ImportError:
        logger.info(f"[SENTRY MESSAGE] {level.upper()}: {message}")
    except Exception:
        pass  # Never fail the caller due to monitoring


# ============================================================
# HEALTH CHECK
# WHY: /health endpoint and admin dashboard need to report
#      whether error tracking is active.
# ============================================================

def sentry_health_check() -> Dict[str, Any]:
    """
    Report whether Sentry is configured and active.
    Safe to call at any time — does NOT send a test event.

    Returns dict suitable for inclusion in /health endpoint response.
    """
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        return {
            "sentry": "disabled",
            "reason": "SENTRY_DSN not set",
            "fix": "Add SENTRY_DSN to .env (get it from sentry.io)"
        }

    try:
        import sentry_sdk
        client = sentry_sdk.get_client()
        if client and client.options.get("dsn"):
            return {
                "sentry": "enabled",
                "environment": os.getenv("ENV", "production"),
                "dsn_configured": True,
            }
        return {
            "sentry": "dsn_set_but_not_initialized",
            "fix": "Call init_sentry() at app startup"
        }
    except ImportError:
        return {
            "sentry": "sdk_not_installed",
            "fix": "pip install 'sentry-sdk[fastapi]' --break-system-packages"
        }
