"""
monitoring.py - FastAPI Error Tracking Middleware
==================================================

WHY: This is the thin FastAPI-specific wiring layer for Sentry.
     The actual Sentry adapter lives in teebu-shared-libs/lib/sentry_lib.py.

     This module's only job:
     1. init_monitoring(app) — adds FastAPI + SQLAlchemy integrations, then calls sentry_lib.init_sentry()
     2. monitoring_middleware — FastAPI middleware that calls sentry_lib.set_tenant_context() per request

     All other Sentry functions (capture_error, set_tenant_context, etc.) are re-exported
     from sentry_lib so callers don't need to import from two places.

USAGE:
    # In main.py startup:
    from core.monitoring import init_monitoring
    init_monitoring(app)

    # Middleware (registered in main.py):
    from core.monitoring import monitoring_middleware
    app.middleware("http")(monitoring_middleware)

    # In any route or service:
    from core.monitoring import capture_error, set_feature_context
    capture_error(e, extra={"tenant_id": tenant_id})
"""

import os
import sys
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# IMPORT SENTRY_LIB ADAPTER
# WHY: sentry_lib lives in teebu-shared-libs/lib/ — add to path.
# ============================================================

# Resolve path to teebu-shared-libs/lib/ relative to this file
import pathlib
_SHARED_LIBS = pathlib.Path(__file__).parent.parent.parent.parent / "teebu-shared-libs" / "lib"
if str(_SHARED_LIBS) not in sys.path:
    sys.path.insert(0, str(_SHARED_LIBS))

from sentry_lib import (
    init_sentry,
    default_before_send_filter,
    set_tenant_context,
    set_feature_context,
    capture_error,
    capture_message,
    sentry_health_check,
)

# Re-export for backward compatibility — callers can import from core.monitoring
# without needing to know that sentry_lib exists.
__all__ = [
    "init_monitoring",
    "monitoring_middleware",
    "set_tenant_context",
    "set_feature_context",
    "capture_error",
    "capture_message",
    "sentry_health_check",
    # Legacy name used in test_p0_capabilities.py
    "_before_send_filter",
]

# Alias for backward compat with existing tests
_before_send_filter = default_before_send_filter


# ============================================================
# FASTAPI-SPECIFIC INITIALIZATION
# WHY: FastAPI + SQLAlchemy integrations require sentry-sdk[fastapi].
#      They live here (not in sentry_lib) because sentry_lib should
#      be framework-agnostic and usable in scripts/workers.
# ============================================================

def init_monitoring(app=None) -> bool:
    """
    Initialize Sentry with FastAPI + SQLAlchemy integrations.
    Call once in main.py @app.on_event("startup").

    Args:
        app: FastAPI app instance (for automatic route-level tracing)

    Returns:
        True if Sentry initialized, False if SENTRY_DSN not set.
    """
    fastapi_integrations = []

    try:
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        fastapi_integrations = [
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ]
    except ImportError:
        # sentry-sdk[fastapi] not installed — fall back to base init
        logger.warning(
            "sentry-sdk[fastapi] not installed. "
            "FastAPI/SQLAlchemy integrations unavailable. "
            "Run: pip install 'sentry-sdk[fastapi]' --break-system-packages"
        )

    return init_sentry(
        dsn=os.getenv("SENTRY_DSN"),
        environment=os.getenv("ENV", "production"),
        release=os.getenv("APP_VERSION", "unknown"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        integrations=fastapi_integrations,
        before_send=default_before_send_filter,
    )


# ============================================================
# FASTAPI MIDDLEWARE
# WHY: Automatically attaches tenant context to every request
#      so all Sentry errors show which tenant was affected.
#      Must run AFTER tenant_middleware (which sets the ContextVar).
# ============================================================

async def monitoring_middleware(request, call_next):
    """
    FastAPI middleware: sets Sentry tenant context per request.

    Register in main.py BEFORE tenant_middleware so it runs after it:
        app.middleware("http")(monitoring_middleware)  # registered first → runs second
        app.middleware("http")(tenant_middleware)       # registered second → runs first
    """
    from core.tenancy import get_current_tenant_id

    tenant_id = get_current_tenant_id()
    if tenant_id:
        set_tenant_context(tenant_id)

    response = await call_next(request)
    return response
