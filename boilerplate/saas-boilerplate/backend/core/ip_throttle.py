"""
ip_throttle.py - In-memory IP Rate Limiting (#35) + Bot UA Filter (#31 partial)

#31: Cloudflare Bot Management handles infrastructure-level bot blocking.
     This module adds a conservative UA blocklist for known offensive scanners
     only (sqlmap, nikto, nuclei, etc).
#35: Per-IP sliding window. In-memory. No Redis dependency.
     For multi-server deployments, swap IPThrottleCounter with a Redis backend.

auth_rate_limit_dependency():
     Strict per-IP limiter for auth endpoints (signup, password-reset, etc).
     Use as a FastAPI Depends: `Depends(auth_rate_limit_dependency)`.
     Default: 10 requests per 60 seconds per IP.
"""
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

IP_THROTTLE_LIMIT = 100   # requests per window
IP_THROTTLE_WINDOW = 60   # seconds

BOT_UA_BLOCKLIST = [
    "sqlmap",
    "nikto",
    "masscan",
    "nmap",
    "zgrab",
    "nuclei",
    "dirbuster",
    "gobuster",
    "wfuzz",
]

# /api/webhooks/stripe MUST be excluded — Stripe webhooks must never be throttled
THROTTLE_EXCLUDED_PATHS = {"/health", "/api/webhooks/stripe"}


class IPThrottleCounter:
    """Pure Python sliding window counter. Testable without HTTP context."""

    def __init__(self, limit: int = IP_THROTTLE_LIMIT, window: int = IP_THROTTLE_WINDOW):
        self._counts: dict = defaultdict(deque)
        self.limit = limit
        self.window = window

    def is_allowed(self, ip: str) -> bool:
        now = datetime.utcnow().timestamp()
        q = self._counts[ip]
        # Evict timestamps older than the window
        while q and q[0] < now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def reset(self, ip: Optional[str] = None) -> None:
        if ip:
            self._counts[ip].clear()
        else:
            self._counts.clear()


class IPThrottleMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting + bot UA filtering middleware.

    Register via:
        app.add_middleware(IPThrottleMiddleware, limit=100, window=60)

    Do NOT use app.middleware("http") — this is a BaseHTTPMiddleware subclass.
    """

    def __init__(self, app, limit: int = IP_THROTTLE_LIMIT, window: int = IP_THROTTLE_WINDOW):
        super().__init__(app)
        self.counter = IPThrottleCounter(limit=limit, window=window)

    async def dispatch(self, request, call_next):
        if request.url.path in THROTTLE_EXCLUDED_PATHS:
            return await call_next(request)

        # #31: block known malicious scanner UAs
        ua = request.headers.get("user-agent", "").lower()
        for pattern in BOT_UA_BLOCKLIST:
            if pattern in ua:
                return Response("Forbidden", status_code=403)

        # #35: per-IP sliding window
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not ip:
            ip = request.client.host if request.client else "unknown"

        if not self.counter.is_allowed(ip):
            return Response(
                "Too Many Requests",
                status_code=429,
                headers={"Retry-After": str(self.counter.window)},
            )

        return await call_next(request)


# ─── Auth-endpoint rate limiter ───────────────────────────────────────────────
# Stricter than the global middleware: 10 requests / 60 s per IP.
# Use as a FastAPI dependency on any public auth endpoint:
#   @app.post("/api/auth/signup")
#   async def signup(..., _=Depends(auth_rate_limit_dependency)):
# ──────────────────────────────────────────────────────────────────────────────

AUTH_RATE_LIMIT  = 10   # requests
AUTH_RATE_WINDOW = 60   # seconds

_auth_counter = IPThrottleCounter(limit=AUTH_RATE_LIMIT, window=AUTH_RATE_WINDOW)


async def auth_rate_limit_dependency(request: Request) -> None:
    """FastAPI dependency: 10 req/60 s per IP for auth endpoints."""
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not ip:
        ip = request.client.host if request.client else "unknown"
    if not _auth_counter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait before trying again.",
            headers={"Retry-After": str(AUTH_RATE_WINDOW)},
        )
