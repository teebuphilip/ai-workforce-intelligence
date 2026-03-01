"""
betteruptime_lib.py - BetterUptime Uptime Monitoring Adapter
=============================================================

WHY: Platform Rule #2 — every capability needs a single adapter library.
     This is the BetterUptime adapter. Nothing in the platform calls the
     BetterUptime API directly; everything goes through this module.

     Centralizing uptime monitoring here means:
     - Swap BetterUptime for another uptime tool by editing only this file
     - Monitor creation and status checks follow the same API everywhere
     - Tests mock this module, not raw requests calls

HOW:
    1. Set BETTERUPTIME_API_KEY in your .env
    2. Call create_monitor() for each service /health endpoint at app startup
    3. Check betteruptime_health_check() from your /health endpoint
    4. Use list_incidents() in admin dashboard to show current outages

USAGE:
    from betteruptime_lib import BetterUptimeLib, BetterUptimeConfig

    config = BetterUptimeConfig()  # reads BETTERUPTIME_API_KEY from env
    uptime = BetterUptimeLib(config)

    # Create a monitor for your app's health endpoint:
    uptime.create_monitor(
        name="CourtDominion API",
        url="https://api.courtdominion.com/health",
    )

BETTERUPTIME FREE TIER:
    - 3 monitors
    - 3-minute check frequency
    - Email + Slack alerts
    - Status pages

    Upgrade for: more monitors, SMS/phone alerts, < 1min checks.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

class BetterUptimeConfig:
    """
    Configuration for BetterUptime API.

    Reads from environment by default — no config file needed since
    BetterUptime is a platform-level tool (one account for all 25 businesses).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://betteruptime.com/api/v2",
    ):
        """
        Initialize BetterUptime configuration.

        Args:
            api_key: BetterUptime API token. Falls back to BETTERUPTIME_API_KEY env var.
            base_url: BetterUptime API base URL (default: v2 API)
        """
        self.api_key = api_key or os.getenv("BETTERUPTIME_API_KEY")
        self.base_url = base_url

    @property
    def is_configured(self) -> bool:
        """True when an API key is available."""
        return bool(self.api_key)


# ============================================================
# MAIN LIBRARY CLASS
# ============================================================

class BetterUptimeLib:
    """
    BetterUptime adapter for uptime monitoring and incident management.

    All methods return {"success": bool, "data": ..., "error": ...} dicts
    following the same pattern as stripe_lib and mailerlite_lib.
    """

    def __init__(self, config: BetterUptimeConfig):
        """
        Initialize BetterUptime library.

        Args:
            config: BetterUptimeConfig instance
        """
        self.config = config
        if not config.is_configured:
            logger.warning(
                "BETTERUPTIME_API_KEY not set — uptime monitoring disabled. "
                "Get your API key from betteruptime.com → Settings → API."
            )

    # ========================================
    # HELPER METHODS
    # ========================================

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to the BetterUptime API.

        Args:
            method: HTTP verb (GET, POST, PATCH, DELETE)
            endpoint: API path (e.g. "/monitors")
            data: JSON body for POST/PATCH
            params: Query string parameters
            max_retries: Retry attempts with exponential backoff

        Returns:
            Dict with success status and data/error
        """
        if not self.config.is_configured:
            return {
                "success": False,
                "error": "BETTERUPTIME_API_KEY not configured",
                "fix": "Set BETTERUPTIME_API_KEY in your .env",
            }

        url = f"{self.config.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(1, max_retries + 1):
            try:
                start = time.time()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=15,
                )
                elapsed = round(time.time() - start, 3)

                if response.status_code in (200, 201, 204):
                    response_data = None
                    if response.content:
                        try:
                            response_data = response.json()
                        except Exception:
                            response_data = {"raw": response.text}
                    logger.debug(f"BetterUptime {method} {endpoint} OK ({elapsed}s)")
                    return {"success": True, "data": response_data, "attempt": attempt}

                # Non-2xx — don't retry for 4xx
                error_body = {}
                try:
                    error_body = response.json()
                except Exception:
                    pass

                if response.status_code < 500:
                    return {
                        "success": False,
                        "error": error_body.get("errors", response.text),
                        "http_status": response.status_code,
                    }

                # 5xx — retry
                logger.warning(
                    f"BetterUptime {method} {endpoint} {response.status_code} "
                    f"(attempt {attempt}/{max_retries})"
                )
                if attempt < max_retries:
                    time.sleep(2 ** (attempt - 1))

            except requests.exceptions.RequestException as e:
                logger.error(f"BetterUptime request error (attempt {attempt}): {e}")
                if attempt == max_retries:
                    return {"success": False, "error": str(e), "error_type": "RequestException"}
                time.sleep(2 ** (attempt - 1))

        return {"success": False, "error": "Max retries exceeded"}

    # ========================================
    # MONITOR OPERATIONS
    # ========================================

    def create_monitor(
        self,
        name: str,
        url: str,
        monitor_type: str = "status",
        check_frequency: int = 180,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an uptime monitor for a URL.

        Free tier: 3 monitors, 3-minute minimum check frequency.

        Args:
            name: Human-readable name (e.g. "CourtDominion API")
            url: URL to monitor (e.g. "https://api.courtdominion.com/health")
            monitor_type: 'status' (HTTP check) | 'ping' | 'tcp_port' | 'keyword'
            check_frequency: Seconds between checks (default: 180 = 3 minutes)
            email: Alert email override (uses account default if None)

        Returns:
            Dict with success status and monitor data (id, url, status)
        """
        logger.info(f"Creating monitor: {name} → {url}")

        body: Dict[str, Any] = {
            "monitor_type": monitor_type,
            "url": url,
            "pronounceable_name": name,
            "check_frequency": check_frequency,
        }
        if email:
            body["email"] = email

        return self._request("POST", "/monitors", data=body)

    def list_monitors(self) -> Dict[str, Any]:
        """
        List all monitors in the BetterUptime account.

        Returns:
            Dict with success status and list of monitor objects
        """
        logger.info("Listing all monitors")
        return self._request("GET", "/monitors")

    def delete_monitor(self, monitor_id: str) -> Dict[str, Any]:
        """
        Delete (remove) a monitor.

        Args:
            monitor_id: BetterUptime monitor ID

        Returns:
            Dict with success status (no data body on delete)
        """
        logger.info(f"Deleting monitor {monitor_id}")
        return self._request("DELETE", f"/monitors/{monitor_id}")

    def get_monitor_status(self, monitor_id: str) -> Dict[str, Any]:
        """
        Get the current status and uptime percentage for a monitor.

        Args:
            monitor_id: BetterUptime monitor ID

        Returns:
            Dict with success status and monitor detail (availability, last_checked_at)
        """
        logger.info(f"Getting status for monitor {monitor_id}")
        return self._request("GET", f"/monitors/{monitor_id}")

    # ========================================
    # INCIDENT OPERATIONS
    # ========================================

    def list_incidents(
        self,
        monitor_id: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        List incidents (outages) from BetterUptime.

        Args:
            monitor_id: Filter by specific monitor (None = all monitors)
            resolved: True = show resolved only, False = show active only, None = all

        Returns:
            Dict with success status and list of incident objects
        """
        logger.info("Listing incidents", {
            "monitor_id": monitor_id, "resolved": resolved
        })

        params: Dict[str, Any] = {}
        if monitor_id:
            params["monitor_id"] = monitor_id
        if resolved is not None:
            params["resolved"] = str(resolved).lower()

        return self._request("GET", "/incidents", params=params or None)

    # ========================================
    # HEALTH CHECK
    # ========================================

    def betteruptime_health_check(self) -> Dict[str, Any]:
        """
        Report whether BetterUptime is configured and the API is reachable.
        Safe to call from /health endpoint — does NOT create or modify monitors.

        Returns:
            Dict suitable for inclusion in /health endpoint response.
        """
        if not self.config.is_configured:
            return {
                "uptime_monitoring": "disabled",
                "reason": "BETTERUPTIME_API_KEY not set",
                "fix": "Add BETTERUPTIME_API_KEY to .env (get it from betteruptime.com)",
            }

        result = self.list_monitors()
        if result["success"]:
            monitors = result.get("data", {}).get("data", [])
            return {
                "uptime_monitoring": "enabled",
                "monitor_count": len(monitors),
                "api_reachable": True,
            }

        return {
            "uptime_monitoring": "error",
            "api_reachable": False,
            "error": result.get("error"),
        }


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def load_betteruptime_lib(api_key: Optional[str] = None) -> BetterUptimeLib:
    """
    Load BetterUptimeLib.

    Args:
        api_key: Optional API key override. Falls back to BETTERUPTIME_API_KEY env var.

    Returns:
        Initialized BetterUptimeLib instance
    """
    config = BetterUptimeConfig(api_key=api_key)
    return BetterUptimeLib(config)
