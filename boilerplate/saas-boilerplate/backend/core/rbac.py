"""
rbac.py - Role-Based Access Control
=====================================

WHY: Authentication (Auth0) tells us WHO the user is.
     RBAC tells us WHAT they're allowed to do.
     Without this, any logged-in user could call admin endpoints.

HOW:
    Roles come from Auth0 JWT token claims.
    Auth0 stores roles in: token["https://teebu.io/roles"]
    (Custom claim namespace - set up in Auth0 Actions/Rules)

    Roles:
        admin    - Full access: user mgmt, billing, AI costs, system config
        user     - Standard access: use all features they've paid for
        viewer   - Read-only: dashboards, reports (no writes)

    Decorator pattern:
        @router.get("/admin/users")
        @require_role("admin")
        def list_users(current_user = Depends(get_current_user)):
            ...

    OR use as a dependency:
        @router.get("/admin/costs")
        def get_costs(user = Depends(require_role("admin"))):
            ...

SETUP REQUIRED (one-time, in Auth0 dashboard):
    1. Create roles: admin, user, viewer
    2. Add Auth0 Action to inject roles into JWT:
        exports.onExecutePostLogin = async (event, api) => {
            const namespace = 'https://teebu.io/';
            const roles = event.authorization?.roles || [];
            api.idToken.setCustomClaim(namespace + 'roles', roles);
            api.accessToken.setCustomClaim(namespace + 'roles', roles);
        };
    3. Assign roles to users in Auth0 dashboard
"""

import logging
from typing import List, Optional, Set
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# ============================================================
# ROLE DEFINITIONS
# WHY: Central definition prevents typos and drift.
#      Add new roles here + update ROLE_HIERARCHY.
# ============================================================

class Role:
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    # Internal-only role for service-to-service calls
    SERVICE = "service"


# Role hierarchy - higher roles inherit lower role permissions
# Example: admin can do everything user and viewer can
ROLE_HIERARCHY: dict[str, Set[str]] = {
    Role.ADMIN:   {Role.ADMIN, Role.USER, Role.VIEWER},
    Role.USER:    {Role.USER, Role.VIEWER},
    Role.VIEWER:  {Role.VIEWER},
    Role.SERVICE: {Role.SERVICE},
}

# Auth0 custom claim namespace for roles
# Must match what you configured in Auth0 Actions
ROLES_CLAIM_KEY = "https://teebu.io/roles"

# Bearer token extractor
security = HTTPBearer(auto_error=False)


# ============================================================
# JWT ROLE EXTRACTION
# WHY: Auth0 JWT contains roles in custom claims.
#      We extract them here once per request.
# ============================================================

def get_roles_from_token(token_payload: dict) -> Set[str]:
    """
    Extract roles from decoded Auth0 JWT payload.

    Looks in:
    1. Custom namespace claim: token["https://teebu.io/roles"]
    2. Standard roles claim: token["roles"] (fallback)

    Returns empty set if no roles found.
    """
    roles = token_payload.get(ROLES_CLAIM_KEY, [])
    if not roles:
        # Fallback for tokens without custom namespace
        roles = token_payload.get("roles", [])

    if isinstance(roles, str):
        roles = [roles]

    return set(roles)


def has_role(user_roles: Set[str], required_role: str) -> bool:
    """
    Check if user has required role (or a role that inherits it).

    Examples:
        has_role({"admin"}, "user")   → True (admin inherits user)
        has_role({"user"}, "admin")   → False
        has_role({"viewer"}, "viewer") → True
    """
    for user_role in user_roles:
        if required_role in ROLE_HIERARCHY.get(user_role, set()):
            return True
    return False


# ============================================================
# CURRENT USER EXTRACTION
# WHY: Centralizes JWT decoding. Routes use get_current_user()
#      as a dependency to get validated user info.
# ============================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None,
) -> dict:
    """
    FastAPI dependency: validates JWT and returns user info.

    Returns:
        {
            "sub": "auth0|abc123",
            "email": "user@example.com",
            "roles": {"admin"},
            "tenant_id": "courtdominion",
            "org_id": "org_abc123"
        }

    Raises:
        401 if no token
        401 if invalid token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = _decode_jwt(token)

    roles = get_roles_from_token(payload)
    tenant_id = payload.get("org_id") or payload.get("https://teebu.io/tenant_id")

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email") or payload.get("https://teebu.io/email"),
        "roles": roles,
        "tenant_id": tenant_id,
        "org_id": payload.get("org_id"),
        "raw_payload": payload,  # Available if routes need other claims
    }


def _decode_jwt(token: str) -> dict:
    """
    Decode and validate Auth0 JWT token.

    Uses PyJWT with Auth0 JWKS for signature verification.
    Raises HTTPException on any validation failure.
    """
    import os
    import jwt
    from jwt import PyJWKClient

    auth0_domain = os.getenv("AUTH0_DOMAIN")
    auth0_audience = os.getenv("AUTH0_AUDIENCE")

    if not auth0_domain or not auth0_audience:
        # DEV MODE: decode payload without signature verification so tests/local
        # dev can pass a self-signed token.  A malformed/absent token still gets
        # a 401 — never a free admin grant.
        # WARNING: NEVER set ENV=development in a public-facing environment.
        if os.getenv("ENV", "production") == "development":
            logger.warning("AUTH0 not configured — skipping JWT signature verification (dev mode only)")
            import base64
            import json
            try:
                payload_b64 = token.split(".")[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                return json.loads(base64.urlsafe_b64decode(payload_b64))
            except Exception:
                # Malformed token in dev mode → 401, never a fallback admin grant
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 not configured. Set AUTH0_DOMAIN and AUTH0_AUDIENCE env vars."
        )

    try:
        jwks_url = f"https://{auth0_domain}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=auth0_audience,
            issuer=f"https://{auth0_domain}/",
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again."
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


# ============================================================
# ROLE ENFORCEMENT - the main interface
# WHY: Two ways to enforce roles - pick whichever fits the route.
# ============================================================

def require_role(required_role: str):
    """
    FastAPI dependency factory: raises 403 if user lacks required role.

    Usage:
        @router.get("/admin/users")
        def list_users(user = Depends(require_role("admin"))):
            # Only admins reach here
            return users

        @router.get("/reports")
        def get_reports(user = Depends(require_role("viewer"))):
            # Viewers, users, and admins can access
            return reports
    """
    async def _require_role(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_roles = current_user.get("roles", set())

        if not has_role(user_roles, required_role):
            logger.warning(
                f"Access denied: user={current_user.get('sub')} "
                f"has roles={user_roles} but needs={required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return current_user

    return _require_role


def require_any_role(required_roles: List[str]):
    """
    Require ANY of the listed roles (OR logic).

    Usage:
        @router.get("/billing")
        def get_billing(user = Depends(require_any_role(["admin", "billing"]))):
            ...
    """
    async def _require_any_role(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_roles = current_user.get("roles", set())

        for role in required_roles:
            if has_role(user_roles, role):
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required one of: {required_roles}"
        )

    return _require_any_role


# ============================================================
# CONVENIENCE DEPENDENCIES - named shortcuts
# WHY: Cleaner route signatures than require_role("admin") everywhere
# ============================================================

require_admin = require_role(Role.ADMIN)
require_user = require_role(Role.USER)
require_viewer = require_role(Role.VIEWER)


# ============================================================
# SESSION MANAGEMENT
# WHY: JWT validation, expiry checking, and refresh token handling.
#      Extends the auth0_lib.py with middleware-level concerns.
# ============================================================

class SessionManager:
    """
    Manages user session state.

    WHY: Auth0 handles the heavy lifting (JWT issuance, refresh).
         This class handles:
         - Caching JWKS to avoid per-request network calls
         - Token refresh detection (letting frontend know when to refresh)
         - Session context propagation to downstream services
    """

    def __init__(self):
        self._jwks_cache: Optional[dict] = None
        self._jwks_cache_time: float = 0
        self._jwks_cache_ttl: int = 3600  # 1 hour - JWKS changes rarely

    def should_refresh_token(self, payload: dict, refresh_buffer_seconds: int = 300) -> bool:
        """
        Returns True if token expires within refresh_buffer_seconds.
        Frontend should pre-emptively refresh before hard expiry.

        WHY: Better UX than failing mid-request with expired token.
        """
        import time
        exp = payload.get("exp", 0)
        return (exp - time.time()) < refresh_buffer_seconds

    def get_session_info(self, user: dict) -> dict:
        """
        Return session metadata for the client.
        Included in API responses to help frontend manage token lifecycle.
        """
        import time
        payload = user.get("raw_payload", {})
        exp = payload.get("exp", 0)
        return {
            "user_id": user.get("sub"),
            "email": user.get("email"),
            "roles": list(user.get("roles", [])),
            "tenant_id": user.get("tenant_id"),
            "token_expires_at": exp,
            "should_refresh": self.should_refresh_token(payload),
            "seconds_remaining": max(0, int(exp - time.time())),
        }


# Module-level singleton
session_manager = SessionManager()
