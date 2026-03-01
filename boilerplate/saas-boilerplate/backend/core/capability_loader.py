"""
capability_loader.py - Capability Registry Loader & Enforcement
================================================================

WHY: Central config for all 20 platform capabilities (13 P0, 7 P1).
     Without this, capabilities are sprinkled across code with no
     single source of truth. This creates:
     - Per-tenant overrides (tenant A gets early P2 access)
     - Auto-validation on startup (P0 capabilities must be configured)
     - Runtime capability checks in middleware

HOW:
    1. On startup: load_capabilities() reads capabilities.json
    2. validate_p0_capabilities() warns about missing P0 setup
    3. is_capability_enabled() checks per-tenant overrides
    4. require_capability() dependency raises 403 if capability disabled

USAGE:
    # Check if capability is enabled for a tenant:
    from core.capability_loader import is_capability_enabled

    if is_capability_enabled("social_posting", tenant_id="courtdominion"):
        post_to_social_media()

    # In a route - block access if capability disabled:
    from core.capability_loader import require_capability

    @router.post("/api/social/post")
    def post_to_social(
        _=Depends(require_capability("social_posting"))
    ):
        ...
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# CAPABILITY STORE - loaded once at startup, cached in memory
# WHY: Reading JSON file on every request is wasteful.
#      Capabilities don't change at runtime.
# ============================================================

_capabilities: Dict[str, Any] = {}
_loaded = False

CAPABILITIES_CONFIG_PATH = Path(__file__).parent.parent / "config" / "capabilities.json"


def load_capabilities(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load capabilities from JSON config file.
    Call once at app startup. Returns the capabilities dict.

    Args:
        config_path: Override default path (useful for testing)

    Returns:
        Dict of all capabilities keyed by capability ID
    """
    global _capabilities, _loaded
    path = config_path or CAPABILITIES_CONFIG_PATH

    if not path.exists():
        logger.error(
            f"capabilities.json not found at {path}. "
            "Create it or copy from saas-boilerplate/backend/config/capabilities.json"
        )
        return {}

    try:
        with open(path) as f:
            config = json.load(f)

        _capabilities = config.get("capabilities", {})
        _loaded = True
        logger.info(
            f"✓ Capability registry loaded: {len(_capabilities)} capabilities "
            f"({sum(1 for c in _capabilities.values() if c.get('priority') == 'P0')} P0, "
            f"{sum(1 for c in _capabilities.values() if c.get('priority') == 'P1')} P1, "
            f"{sum(1 for c in _capabilities.values() if c.get('priority') == 'P2')} P2)"
        )
        return _capabilities

    except json.JSONDecodeError as e:
        logger.error(f"capabilities.json parse error: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load capabilities.json: {e}")
        return {}


def get_capabilities() -> Dict[str, Any]:
    """Get all capabilities. Auto-loads if not loaded yet."""
    if not _loaded:
        load_capabilities()
    return _capabilities


def get_capability(capability_id: str) -> Optional[Dict[str, Any]]:
    """Get a single capability definition by ID. Returns None if not found."""
    return get_capabilities().get(capability_id)


# ============================================================
# P0 VALIDATION
# WHY: Catch missing setup BEFORE first customer hits an error.
#      Run on startup. Warn loudly about unconfigured P0 capabilities.
# ============================================================

def validate_p0_capabilities() -> Dict[str, Any]:
    """
    Check that all P0 capabilities are properly configured.
    Logs warnings for each unconfigured P0 capability.

    Returns:
        {
            "p0_count": 13,
            "configured": 10,
            "warnings": ["SENTRY_DSN not set", ...],
            "ready_for_production": False
        }

    Call in main.py startup event.
    """
    capabilities = get_capabilities()
    warnings = []

    # P0 capabilities and their required env vars / setup
    p0_checks = {
        "authentication":        {"env": ["AUTH0_DOMAIN", "AUTH0_AUDIENCE", "AUTH0_CLIENT_ID"]},
        "billing":               {"env": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"]},
        "error_tracking":        {"env": ["SENTRY_DSN"]},
        "multi_tenancy":         {"env": []},  # Code-only, no env required
        "ai_cost_tracking":      {"env": ["ANTHROPIC_API_KEY"]},
        "ai_budget_enforcement": {"env": []},  # Code-only
        "ai_model_routing":      {"env": []},  # Code-only
        "entitlements":          {"env": []},  # Code-only
        "usage_limits":          {"env": []},  # Code-only
        "role_based_access":     {"env": ["AUTH0_DOMAIN"]},
        "session_management":    {"env": ["AUTH0_DOMAIN"]},
        "backups_recovery":      {"env": []},  # Railway dashboard config
        "capability_registry":   {"env": []},  # This file!
    }

    p0_count = 0
    configured_count = 0

    for cap_id, cap_data in capabilities.items():
        if cap_data.get("priority") != "P0":
            continue
        p0_count += 1

        checks = p0_checks.get(cap_id, {"env": []})
        missing_vars = [
            var for var in checks.get("env", [])
            if not os.getenv(var)
        ]

        if missing_vars:
            msg = f"P0 UNCONFIGURED: {cap_id} - missing env vars: {missing_vars}"
            logger.warning(msg)
            warnings.append(msg)
        else:
            configured_count += 1

    # Special checks
    if not os.getenv("DATABASE_URL"):
        warnings.append("DATABASE_URL not set - using SQLite (OK for dev, NOT for production)")

    if not os.getenv("SENTRY_DSN"):
        warnings.append("SENTRY_DSN not set - error tracking disabled (required for production)")

    production_ready = len(warnings) == 0

    if production_ready:
        logger.info("✓ All P0 capabilities configured - platform is production-ready")
    else:
        logger.warning(
            f"⚠ Platform NOT production-ready: {len(warnings)} P0 configuration issues"
        )

    return {
        "p0_count": p0_count,
        "configured": configured_count,
        "warnings": warnings,
        "ready_for_production": production_ready,
    }


# ============================================================
# PER-TENANT CAPABILITY CHECKING
# WHY: Basic tier shouldn't access P2 features.
#      Enterprise customer might get early access to new features.
# ============================================================

def is_capability_enabled(
    capability_id: str,
    tenant_id: Optional[str] = None,
    tier: str = "basic",
    tenant_config_overrides: Optional[Dict] = None,
) -> bool:
    """
    Check if a capability is enabled for a tenant.

    Rules (in order):
    1. If capability doesn't exist → False
    2. If P0 capability → always True (required)
    3. Check per-tenant override (can enable/disable any capability)
    4. Check tier availability (P2 features only for pro+)
    5. Default: enabled_by_default value

    Args:
        capability_id: ID from capabilities.json
        tenant_id: Tenant making the request (for logging)
        tier: Tenant's plan tier
        tenant_config_overrides: From tenant.config_overrides DB column

    Returns:
        True if capability is enabled for this tenant/tier
    """
    cap = get_capability(capability_id)

    if not cap:
        logger.warning(f"Unknown capability: {capability_id}")
        return False

    # P0 capabilities are always enabled - they're required
    if cap.get("priority") == "P0":
        return True

    # Per-tenant override takes precedence over everything else
    if tenant_config_overrides:
        cap_overrides = tenant_config_overrides.get("capabilities", {})
        if capability_id in cap_overrides:
            override_value = cap_overrides[capability_id]
            logger.debug(
                f"Capability override: tenant={tenant_id} cap={capability_id} "
                f"override={override_value}"
            )
            return bool(override_value)

    # Check tier availability
    tier_availability = cap.get("tier_availability", [])
    if tier_availability and tier not in tier_availability:
        logger.debug(
            f"Capability not available for tier: cap={capability_id} tier={tier} "
            f"available={tier_availability}"
        )
        return False

    # Check P2 features - disabled by default unless tier is pro+
    if cap.get("priority") == "P2":
        return tier in ("pro", "enterprise")

    # Use default
    return cap.get("enabled_by_default", False)


def get_enabled_capabilities(
    tier: str = "basic",
    tenant_config_overrides: Optional[Dict] = None,
) -> Dict[str, bool]:
    """
    Get all capabilities and their enabled status for a tier.
    Used in dashboard to show what's enabled/disabled.

    Returns dict: {capability_id: True/False}
    """
    result = {}
    for cap_id in get_capabilities():
        result[cap_id] = is_capability_enabled(
            cap_id,
            tier=tier,
            tenant_config_overrides=tenant_config_overrides,
        )
    return result


# ============================================================
# FASTAPI DEPENDENCY - capability enforcement in routes
# WHY: Block access to disabled capabilities at the route level.
#      Cleaner than if-statements in every route.
# ============================================================

def require_capability(capability_id: str):
    """
    FastAPI dependency factory: raises 403 if capability disabled for tenant.

    Usage:
        @router.post("/api/social/post")
        def post_to_social(
            _=Depends(require_capability("social_posting")),
            user=Depends(get_current_user)
        ):
            ...

        @router.get("/api/marketplace/listings")
        def list_items(
            _=Depends(require_capability("listing_crud")),
        ):
            ...
    """
    from fastapi import Depends, HTTPException, Request, status

    async def _require_capability(request: Request) -> None:
        from core.tenancy import get_current_tenant_id
        from core.database import SessionLocal

        tenant_id = get_current_tenant_id()
        tier = "pro"  # Default - should come from tenant record
        overrides = None

        # Try to load tenant record for tier and overrides
        if tenant_id:
            try:
                from core.tenancy import Tenant
                db = SessionLocal()
                try:
                    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
                    if tenant:
                        tier = tenant.tier
                        overrides = tenant.config_overrides or {}
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Could not load tenant for capability check: {e}")

        if not is_capability_enabled(capability_id, tenant_id, tier, overrides):
            cap = get_capability(capability_id)
            cap_name = cap.get("name", capability_id) if cap else capability_id

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Capability '{cap_name}' is not available on your plan. "
                    f"Upgrade at /pricing to unlock this feature."
                )
            )

    return _require_capability


# ============================================================
# STATUS REPORTING
# WHY: /health endpoint and admin dashboard need capability status
# ============================================================

def get_platform_status() -> Dict[str, Any]:
    """
    Get comprehensive platform status for health endpoint and admin dashboard.

    Returns:
        {
            "capabilities_loaded": True,
            "total_capabilities": 20,
            "p0_count": 13,
            "p0_complete": 13,
            "p1_count": 7,
            "p2_count": 12,
            "production_ready": True,
            "validation": {...}
        }
    """
    caps = get_capabilities()
    p0 = [c for c in caps.values() if c.get("priority") == "P0"]
    p1 = [c for c in caps.values() if c.get("priority") == "P1"]
    p2 = [c for c in caps.values() if c.get("priority") == "P2"]
    p0_complete = [c for c in p0 if c.get("status") == "complete"]

    validation = validate_p0_capabilities()

    return {
        "capabilities_loaded": _loaded,
        "total_capabilities": len(caps),
        "p0_count": len(p0),
        "p0_complete": len(p0_complete),
        "p1_count": len(p1),
        "p2_count": len(p2),
        "production_ready": validation["ready_for_production"],
        "validation_warnings": validation["warnings"],
    }
