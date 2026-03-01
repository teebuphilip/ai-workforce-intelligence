"""
test_betteruptime_lib.py — Tests for BetterUptime uptime monitoring adapter
============================================================================

Tests validate:
- create_monitor: monitor creation with correct params
- list_monitors: listing all monitors
- delete_monitor: monitor deletion
- get_monitor_status: single monitor status
- list_incidents: incident listing with and without filters
- betteruptime_health_check: health check dict for /health endpoint
- Graceful degradation when API key is not configured

All tests mock requests — no real BetterUptime account needed.

Run:
    pytest tests/test_betteruptime_lib.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from betteruptime_lib import BetterUptimeLib, BetterUptimeConfig, load_betteruptime_lib


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def uptime():
    """BetterUptimeLib with a fake API key."""
    config = BetterUptimeConfig(api_key="fake_betteruptime_key")
    return BetterUptimeLib(config)


@pytest.fixture
def uptime_no_key():
    """BetterUptimeLib without an API key — simulates unconfigured state."""
    config = BetterUptimeConfig(api_key=None)
    # Clear env var too
    os.environ.pop("BETTERUPTIME_API_KEY", None)
    return BetterUptimeLib(config)


def _mock_response(status_code=200, json_body=None):
    """Build a mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.content = b"ok" if json_body is None else b"data"
    mock.json.return_value = json_body or {}
    mock.text = str(json_body)
    return mock


# ============================================================
# TEST: BetterUptimeConfig
# ============================================================

class TestBetterUptimeConfig:

    def test_reads_api_key_from_arg(self):
        """Config reads API key from constructor argument."""
        config = BetterUptimeConfig(api_key="my_key")
        assert config.api_key == "my_key"
        assert config.is_configured is True

    def test_reads_api_key_from_env(self, monkeypatch):
        """Config reads API key from BETTERUPTIME_API_KEY env var."""
        monkeypatch.setenv("BETTERUPTIME_API_KEY", "env_key")
        config = BetterUptimeConfig()
        assert config.api_key == "env_key"
        assert config.is_configured is True

    def test_not_configured_without_key(self, monkeypatch):
        """Config reports not configured when no key is set."""
        monkeypatch.delenv("BETTERUPTIME_API_KEY", raising=False)
        config = BetterUptimeConfig()
        assert config.is_configured is False

    def test_arg_takes_precedence_over_env(self, monkeypatch):
        """Explicit API key takes precedence over environment variable."""
        monkeypatch.setenv("BETTERUPTIME_API_KEY", "env_key")
        config = BetterUptimeConfig(api_key="explicit_key")
        assert config.api_key == "explicit_key"


# ============================================================
# TEST: create_monitor
# ============================================================

class TestCreateMonitor:

    def test_creates_monitor(self, uptime):
        """create_monitor posts to /monitors with correct body."""
        mock_response_data = {
            "data": {
                "id": "12345",
                "attributes": {
                    "pronounceable_name": "My API",
                    "url": "https://api.example.com/health",
                    "monitor_type": "status",
                }
            }
        }

        with patch("requests.request", return_value=_mock_response(201, mock_response_data)) as mock_req:
            result = uptime.create_monitor(
                name="My API",
                url="https://api.example.com/health",
            )

        assert result["success"] is True
        assert result["data"] == mock_response_data
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["method"] == "POST"
        assert "/monitors" in call_kwargs["url"]
        assert call_kwargs["json"]["pronounceable_name"] == "My API"
        assert call_kwargs["json"]["url"] == "https://api.example.com/health"
        assert call_kwargs["json"]["monitor_type"] == "status"

    def test_create_monitor_default_frequency(self, uptime):
        """create_monitor defaults to 180s (3 min) check frequency."""
        with patch("requests.request", return_value=_mock_response(201, {})) as mock_req:
            uptime.create_monitor(name="Test", url="https://example.com/health")
        assert mock_req.call_args[1]["json"]["check_frequency"] == 180

    def test_create_monitor_custom_frequency(self, uptime):
        """create_monitor accepts custom check_frequency."""
        with patch("requests.request", return_value=_mock_response(201, {})) as mock_req:
            uptime.create_monitor(
                name="Test", url="https://example.com/health", check_frequency=60
            )
        assert mock_req.call_args[1]["json"]["check_frequency"] == 60

    def test_returns_error_without_api_key(self, uptime_no_key):
        """create_monitor returns error dict when API key is missing."""
        result = uptime_no_key.create_monitor(
            name="Test", url="https://example.com/health"
        )
        assert result["success"] is False
        assert "BETTERUPTIME_API_KEY" in result["error"]


# ============================================================
# TEST: list_monitors
# ============================================================

class TestListMonitors:

    def test_lists_monitors(self, uptime):
        """list_monitors returns all monitors from the account."""
        mock_data = {"data": [{"id": "1"}, {"id": "2"}]}

        with patch("requests.request", return_value=_mock_response(200, mock_data)):
            result = uptime.list_monitors()

        assert result["success"] is True
        assert len(result["data"]["data"]) == 2

    def test_returns_error_without_api_key(self, uptime_no_key):
        """list_monitors returns error when unconfigured."""
        result = uptime_no_key.list_monitors()
        assert result["success"] is False


# ============================================================
# TEST: delete_monitor
# ============================================================

class TestDeleteMonitor:

    def test_deletes_monitor(self, uptime):
        """delete_monitor sends DELETE to /monitors/{id}."""
        with patch("requests.request", return_value=_mock_response(204)) as mock_req:
            result = uptime.delete_monitor("12345")

        assert result["success"] is True
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["method"] == "DELETE"
        assert "/monitors/12345" in call_kwargs["url"]


# ============================================================
# TEST: get_monitor_status
# ============================================================

class TestGetMonitorStatus:

    def test_gets_monitor_status(self, uptime):
        """get_monitor_status returns monitor detail by ID."""
        mock_data = {
            "data": {
                "id": "12345",
                "attributes": {"availability": 99.9, "last_checked_at": "2026-02-22T10:00:00Z"}
            }
        }

        with patch("requests.request", return_value=_mock_response(200, mock_data)) as mock_req:
            result = uptime.get_monitor_status("12345")

        assert result["success"] is True
        assert result["data"]["data"]["attributes"]["availability"] == 99.9
        assert "/monitors/12345" in mock_req.call_args[1]["url"]


# ============================================================
# TEST: list_incidents
# ============================================================

class TestListIncidents:

    def test_lists_all_incidents(self, uptime):
        """list_incidents returns all incidents without filters."""
        mock_data = {"data": [{"id": "inc_1"}, {"id": "inc_2"}]}

        with patch("requests.request", return_value=_mock_response(200, mock_data)) as mock_req:
            result = uptime.list_incidents()

        assert result["success"] is True
        assert len(result["data"]["data"]) == 2
        assert mock_req.call_args[1]["params"] is None

    def test_filters_by_monitor_id(self, uptime):
        """list_incidents passes monitor_id as a query param."""
        with patch("requests.request", return_value=_mock_response(200, {"data": []})) as mock_req:
            uptime.list_incidents(monitor_id="12345")

        assert mock_req.call_args[1]["params"]["monitor_id"] == "12345"

    def test_filters_by_resolved_status(self, uptime):
        """list_incidents passes resolved filter as a query param."""
        with patch("requests.request", return_value=_mock_response(200, {"data": []})) as mock_req:
            uptime.list_incidents(resolved=True)

        assert mock_req.call_args[1]["params"]["resolved"] == "true"

    def test_filters_unresolved(self, uptime):
        """list_incidents supports filtering for active (unresolved) incidents."""
        with patch("requests.request", return_value=_mock_response(200, {"data": []})) as mock_req:
            uptime.list_incidents(resolved=False)

        assert mock_req.call_args[1]["params"]["resolved"] == "false"


# ============================================================
# TEST: betteruptime_health_check
# ============================================================

class TestBetterUptimeHealthCheck:

    def test_returns_disabled_without_key(self, uptime_no_key):
        """Health check reports disabled when API key is not set."""
        result = uptime_no_key.betteruptime_health_check()
        assert result["uptime_monitoring"] == "disabled"
        assert "fix" in result

    def test_returns_enabled_when_configured_and_api_ok(self, uptime):
        """Health check reports enabled when API key is set and API is reachable."""
        mock_data = {"data": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}

        with patch("requests.request", return_value=_mock_response(200, mock_data)):
            result = uptime.betteruptime_health_check()

        assert result["uptime_monitoring"] == "enabled"
        assert result["api_reachable"] is True
        assert result["monitor_count"] == 3

    def test_returns_error_when_api_fails(self, uptime):
        """Health check reports error when API call fails."""
        with patch("requests.request", return_value=_mock_response(500, {"error": "server error"})):
            result = uptime.betteruptime_health_check()

        assert result["uptime_monitoring"] == "error"
        assert result["api_reachable"] is False


# ============================================================
# TEST: load_betteruptime_lib
# ============================================================

class TestLoadBetterUptimeLib:

    def test_loads_with_api_key(self):
        """load_betteruptime_lib creates a configured instance."""
        lib = load_betteruptime_lib(api_key="test_key")
        assert lib.config.is_configured is True

    def test_loads_from_env(self, monkeypatch):
        """load_betteruptime_lib reads from env when no key given."""
        monkeypatch.setenv("BETTERUPTIME_API_KEY", "env_key")
        lib = load_betteruptime_lib()
        assert lib.config.api_key == "env_key"
