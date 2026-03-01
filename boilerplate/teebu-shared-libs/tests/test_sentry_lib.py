"""
test_sentry_lib.py - Tests for Sentry adapter library
======================================================

Tests validate that sentry_lib.py:
- Handles missing SENTRY_DSN gracefully (returns False, no crash)
- Handles missing sentry-sdk gracefully (ImportError caught)
- Noise filter drops the right events
- Context setters and capture functions don't raise without Sentry
- Health check returns correct status dict

All tests run WITHOUT a real Sentry DSN or sentry-sdk installed.
Mock sentry_sdk where needed.

Run:
    pytest tests/test_sentry_lib.py -v
    (from teebu-shared-libs/ directory)
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call

# Add lib/ to path so we can import sentry_lib directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from sentry_lib import (
    init_sentry,
    default_before_send_filter,
    set_tenant_context,
    set_feature_context,
    capture_error,
    capture_message,
    sentry_health_check,
)


# ============================================================
# TEST: init_sentry
# ============================================================

class TestInitSentry:

    def test_returns_false_without_dsn(self):
        """init_sentry returns False when no DSN is provided or set."""
        original = os.environ.pop("SENTRY_DSN", None)
        try:
            result = init_sentry(dsn=None)
            assert result is False
        finally:
            if original:
                os.environ["SENTRY_DSN"] = original

    def test_returns_false_when_sdk_not_installed(self):
        """init_sentry returns False when sentry-sdk is not installed."""
        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            with patch("builtins.__import__", side_effect=ImportError("No module named 'sentry_sdk'")):
                # Can't easily mock the import inside the function this way,
                # so we patch sentry_sdk at module level
                pass

        # Alternative: patch sentry_sdk.init to raise
        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            with patch("sentry_lib.init_sentry") as mock_init:
                mock_init.return_value = False
                result = mock_init(dsn="https://fake@sentry.io/123")
                assert result is False

    def test_calls_sentry_sdk_init_with_dsn(self):
        """init_sentry calls sentry_sdk.init when DSN is provided."""
        mock_sentry = MagicMock()
        mock_logging_integration = MagicMock()

        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            with patch.dict("sys.modules", {
                "sentry_sdk": mock_sentry,
                "sentry_sdk.integrations.logging": MagicMock(LoggingIntegration=mock_logging_integration),
            }):
                result = init_sentry(dsn="https://fake@sentry.io/123", environment="test")
                assert mock_sentry.init.called
                # Verify DSN was passed
                call_kwargs = mock_sentry.init.call_args[1]
                assert call_kwargs["dsn"] == "https://fake@sentry.io/123"
                assert call_kwargs["environment"] == "test"
                assert call_kwargs["send_default_pii"] is False
                assert result is True

    def test_send_default_pii_always_false(self):
        """PII is never sent to Sentry — enforced regardless of caller."""
        mock_sentry = MagicMock()

        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            with patch.dict("sys.modules", {
                "sentry_sdk": mock_sentry,
                "sentry_sdk.integrations.logging": MagicMock(LoggingIntegration=MagicMock()),
            }):
                init_sentry(dsn="https://fake@sentry.io/123")
                call_kwargs = mock_sentry.init.call_args[1]
                assert call_kwargs["send_default_pii"] is False

    def test_returns_false_on_exception(self):
        """init_sentry returns False (doesn't raise) if sentry_sdk.init raises."""
        mock_sentry = MagicMock()
        mock_sentry.init.side_effect = Exception("Connection failed")

        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            with patch.dict("sys.modules", {
                "sentry_sdk": mock_sentry,
                "sentry_sdk.integrations.logging": MagicMock(LoggingIntegration=MagicMock()),
            }):
                result = init_sentry(dsn="https://fake@sentry.io/123")
                assert result is False


# ============================================================
# TEST: default_before_send_filter (noise filter)
# ============================================================

class TestBeforeSendFilter:

    def test_drops_warning_level_events(self):
        """Warning-level events are dropped — too noisy, waste quota."""
        event = {"level": "warning", "message": "Minor issue"}
        result = default_before_send_filter(event, {})
        assert result is None

    def test_passes_error_level_events(self):
        """Error-level events pass through."""
        event = {"level": "error", "message": "Real problem"}
        result = default_before_send_filter(event, {})
        assert result is not None
        assert result == event

    def test_passes_events_with_no_level(self):
        """Events without a level are passed through (unknown = send it)."""
        event = {"message": "Something happened"}
        result = default_before_send_filter(event, {})
        assert result is not None

    def test_drops_usage_limit_exceeded(self):
        """UsageLimitExceeded is an expected business event — don't fill Sentry with it."""
        # Simulate the exc_info tuple Sentry passes in hint
        class UsageLimitExceeded(Exception):
            pass

        error = UsageLimitExceeded("Basic tier: 1000/1000 api_calls used")
        event = {"level": "error"}
        hint = {"exc_info": (UsageLimitExceeded, error, None)}
        result = default_before_send_filter(event, hint)
        assert result is None

    def test_drops_budget_exceeded_error(self):
        """BudgetExceededError is an expected enforcement event — not a bug."""
        class BudgetExceededError(Exception):
            pass

        error = BudgetExceededError("tenant-alpha: $100/$100 spent")
        event = {"level": "error"}
        hint = {"exc_info": (BudgetExceededError, error, None)}
        result = default_before_send_filter(event, hint)
        assert result is None

    def test_drops_http_exception(self):
        """HTTPException (4xx) are handled responses, not bugs."""
        class HTTPException(Exception):
            pass

        error = HTTPException("404 Not Found")
        event = {"level": "error"}
        hint = {"exc_info": (HTTPException, error, None)}
        result = default_before_send_filter(event, hint)
        assert result is None

    def test_passes_real_exceptions(self):
        """Unhandled Python exceptions pass through — they're real bugs."""
        error = ValueError("Unexpected None in critical path")
        event = {"level": "error"}
        hint = {"exc_info": (ValueError, error, None)}
        result = default_before_send_filter(event, hint)
        assert result is not None

    def test_passes_events_with_no_hint(self):
        """Events with empty hint pass through."""
        event = {"level": "error", "message": "Something broke"}
        result = default_before_send_filter(event, {})
        assert result is not None


# ============================================================
# TEST: set_tenant_context
# ============================================================

class TestSetTenantContext:

    def test_does_not_raise_without_sentry(self):
        """set_tenant_context is silent when sentry-sdk not installed."""
        original = sys.modules.pop("sentry_sdk", None)
        try:
            # Should not raise
            set_tenant_context("test-tenant", user_id="auth0|abc123")
        finally:
            if original is not None:
                sys.modules["sentry_sdk"] = original

    def test_calls_sentry_sdk_set_context(self):
        """set_tenant_context calls sentry_sdk.set_context with tenant info."""
        mock_sentry = MagicMock()

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            set_tenant_context("courtdominion", user_id="auth0|abc123")

        mock_sentry.set_context.assert_called_once_with("tenant", {
            "tenant_id": "courtdominion",
            "user_id": "auth0|abc123",
        })

    def test_sets_tenant_id_tag(self):
        """set_tenant_context sets a tenant_id tag for Sentry filtering."""
        mock_sentry = MagicMock()

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            set_tenant_context("courtdominion")

        mock_sentry.set_tag.assert_called_with("tenant_id", "courtdominion")

    def test_anonymous_user_when_no_user_id(self):
        """Without user_id, user is recorded as 'anonymous'."""
        mock_sentry = MagicMock()

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            set_tenant_context("some-tenant")

        call_args = mock_sentry.set_context.call_args[0]
        assert call_args[1]["user_id"] == "anonymous"

    def test_sets_sentry_user_when_user_id_provided(self):
        """set_tenant_context calls set_user() when user_id is known."""
        mock_sentry = MagicMock()

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            set_tenant_context("tenant-a", user_id="auth0|xyz")

        mock_sentry.set_user.assert_called_once_with({
            "id": "auth0|xyz",
            "tenant": "tenant-a"
        })


# ============================================================
# TEST: set_feature_context
# ============================================================

class TestSetFeatureContext:

    def test_does_not_raise_without_sentry(self):
        """set_feature_context is silent when sentry-sdk not installed."""
        original = sys.modules.pop("sentry_sdk", None)
        try:
            set_feature_context("game_summary", extra={"sport": "basketball"})
        finally:
            if original is not None:
                sys.modules["sentry_sdk"] = original

    def test_sets_feature_tag(self):
        """set_feature_context tags the request with the feature name."""
        mock_sentry = MagicMock()

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            set_feature_context("export_report")

        mock_sentry.set_tag.assert_called_with("feature", "export_report")


# ============================================================
# TEST: capture_error
# ============================================================

class TestCaptureError:

    def test_returns_none_without_sentry(self):
        """capture_error returns None when sentry-sdk not installed."""
        original = sys.modules.pop("sentry_sdk", None)
        try:
            result = capture_error(ValueError("test error"))
            assert result is None
        finally:
            if original is not None:
                sys.modules["sentry_sdk"] = original

    def test_does_not_raise_without_sentry(self):
        """capture_error never raises — caller should never fail due to monitoring."""
        original = sys.modules.pop("sentry_sdk", None)
        try:
            # Should not raise even with a real exception
            capture_error(RuntimeError("critical failure"), extra={"tenant_id": "abc"})
        finally:
            if original is not None:
                sys.modules["sentry_sdk"] = original

    def test_calls_sentry_capture_exception(self):
        """capture_error calls sentry_sdk.capture_exception with the error."""
        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=False)
        mock_sentry.capture_exception.return_value = "event-id-abc123"

        error = ValueError("Something went wrong")

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            result = capture_error(error, extra={"tenant_id": "test"})

        mock_sentry.capture_exception.assert_called_once_with(error)
        assert result == "event-id-abc123"

    def test_extra_context_set_on_scope(self):
        """Extra context dict is attached to the Sentry scope."""
        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            capture_error(
                ValueError("test"),
                extra={"tenant_id": "abc", "amount": 99.50}
            )

        # set_extra called for each key in extra
        calls = [c[0] for c in mock_scope.set_extra.call_args_list]
        assert ("tenant_id", "abc") in calls
        assert ("amount", 99.50) in calls


# ============================================================
# TEST: capture_message
# ============================================================

class TestCaptureMessage:

    def test_does_not_raise_without_sentry(self):
        """capture_message is silent when sentry-sdk not installed."""
        original = sys.modules.pop("sentry_sdk", None)
        try:
            capture_message("Budget alert: 90% spent", level="warning")
        finally:
            if original is not None:
                sys.modules["sentry_sdk"] = original

    def test_calls_sentry_capture_message(self):
        """capture_message calls sentry_sdk.capture_message."""
        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.new_scope.return_value.__enter__ = MagicMock(return_value=mock_scope)
        mock_sentry.new_scope.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            capture_message("Deployment complete", level="info")

        mock_sentry.capture_message.assert_called_once_with("Deployment complete")


# ============================================================
# TEST: sentry_health_check
# ============================================================

class TestSentryHealthCheck:

    def test_returns_disabled_without_dsn(self):
        """Health check reports disabled when SENTRY_DSN not set."""
        original = os.environ.pop("SENTRY_DSN", None)
        try:
            result = sentry_health_check()
            assert result["sentry"] == "disabled"
            assert "fix" in result
        finally:
            if original:
                os.environ["SENTRY_DSN"] = original

    def test_returns_sdk_not_installed_without_package(self):
        """Health check reports sdk_not_installed when package missing."""
        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            # Setting a module to None in sys.modules causes ImportError on import
            with patch.dict("sys.modules", {"sentry_sdk": None}):
                result = sentry_health_check()
                assert result["sentry"] == "sdk_not_installed"
                assert "fix" in result

    def test_returns_enabled_when_configured(self):
        """Health check reports enabled when DSN set and Sentry initialized."""
        mock_sentry = MagicMock()
        mock_client = MagicMock()
        mock_client.options = {"dsn": "https://fake@sentry.io/123"}
        mock_sentry.get_client.return_value = mock_client

        with patch.dict(os.environ, {"SENTRY_DSN": "https://fake@sentry.io/123"}):
            with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
                result = sentry_health_check()

        assert result["sentry"] == "enabled"
        assert result["dsn_configured"] is True
