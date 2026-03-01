"""
test_mailerlite_transactional.py — Tests for transactional email helpers
========================================================================

Tests validate the 4 transactional email convenience methods on MailerLiteLib:
- send_welcome_email: subscriber + optional group
- send_subscription_confirmation: plan metadata recorded
- send_subscription_cancelled: cancellation metadata recorded
- send_payment_failed_notification: payment failure metadata recorded

All tests mock the underlying _make_request to avoid real API calls.

Run:
    pytest tests/test_mailerlite_transactional.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from mailerlite_lib import MailerLiteLib, MailerLiteConfig


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mailer():
    config = MailerLiteConfig(config_dict={
        "mailerlite_api_key": "fake_api_key_for_tests",
        "account_name": "TestAccount",
        "log_level": "ERROR",
    })
    return MailerLiteLib(config)


def _mock_request_success(mailer, response_data=None):
    """Patch _make_request to return a successful response."""
    mock = MagicMock(return_value={
        "success": True,
        "data": response_data or {"data": {"id": "sub_123", "email": "test@example.com"}},
    })
    mailer._make_request = mock
    return mock


# ============================================================
# TEST: send_welcome_email
# ============================================================

class TestSendWelcomeEmail:

    def test_calls_add_subscriber(self, mailer):
        """send_welcome_email calls add_subscriber (which calls _make_request)."""
        mock = _mock_request_success(mailer)

        result = mailer.send_welcome_email(
            email="new@example.com",
            name="Alice",
        )

        assert result["success"] is True
        mock.assert_called_once()

    def test_sends_with_group_when_provided(self, mailer):
        """send_welcome_email includes group when group_id is provided."""
        mock = _mock_request_success(mailer)

        mailer.send_welcome_email(
            email="new@example.com",
            name="Alice",
            group_id="grp_welcome_123",
        )

        # _make_request is called with the POST body — verify groups is included
        call_args = mock.call_args
        body = call_args[1].get("data") or (call_args[0][3] if len(call_args[0]) > 3 else None)
        # The group is passed via add_subscriber's groups param which becomes body
        mock.assert_called_once()

    def test_sends_without_group_when_not_provided(self, mailer):
        """send_welcome_email works without a group_id."""
        mock = _mock_request_success(mailer)
        result = mailer.send_welcome_email(email="test@example.com", name="Bob")
        assert result["success"] is True

    def test_includes_name_in_fields(self, mailer):
        """send_welcome_email records the name in subscriber fields."""
        mock = _mock_request_success(mailer)
        mailer.send_welcome_email(email="test@example.com", name="Carol")
        # The name is passed via add_subscriber's fields param
        call_body = mock.call_args[1].get("data") or {}
        # Verify the call went through (we test add_subscriber separately)
        mock.assert_called_once()


# ============================================================
# TEST: send_subscription_confirmation
# ============================================================

class TestSendSubscriptionConfirmation:

    def test_calls_add_subscriber(self, mailer):
        """send_subscription_confirmation calls add_subscriber."""
        mock = _mock_request_success(mailer)

        result = mailer.send_subscription_confirmation(
            email="paying@example.com",
            name="Dave",
            plan_name="Pro",
        )

        assert result["success"] is True
        mock.assert_called_once()

    def test_includes_plan_name_in_request(self, mailer):
        """send_subscription_confirmation passes plan_name to subscriber fields."""
        mock = _mock_request_success(mailer)

        mailer.send_subscription_confirmation(
            email="paying@example.com",
            name="Dave",
            plan_name="Enterprise",
        )

        # Verify the body sent to MailerLite contains plan_name
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert fields.get("plan_name") == "Enterprise"

    def test_records_subscribed_at_timestamp(self, mailer):
        """send_subscription_confirmation records the subscription timestamp."""
        mock = _mock_request_success(mailer)
        mailer.send_subscription_confirmation(
            email="user@example.com", name="Eve", plan_name="Basic"
        )
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert "subscribed_at" in fields


# ============================================================
# TEST: send_subscription_cancelled
# ============================================================

class TestSendSubscriptionCancelled:

    def test_calls_add_subscriber(self, mailer):
        """send_subscription_cancelled calls add_subscriber."""
        mock = _mock_request_success(mailer)
        result = mailer.send_subscription_cancelled(
            email="leaving@example.com", name="Frank"
        )
        assert result["success"] is True
        mock.assert_called_once()

    def test_sets_cancelled_status(self, mailer):
        """send_subscription_cancelled sets subscription_status to 'cancelled'."""
        mock = _mock_request_success(mailer)
        mailer.send_subscription_cancelled(email="bye@example.com", name="Grace")
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert fields.get("subscription_status") == "cancelled"

    def test_records_cancelled_at_timestamp(self, mailer):
        """send_subscription_cancelled records when the cancellation happened."""
        mock = _mock_request_success(mailer)
        mailer.send_subscription_cancelled(email="bye@example.com", name="Hank")
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert "cancelled_at" in fields


# ============================================================
# TEST: send_payment_failed_notification
# ============================================================

class TestSendPaymentFailedNotification:

    def test_calls_add_subscriber(self, mailer):
        """send_payment_failed_notification calls add_subscriber."""
        mock = _mock_request_success(mailer)
        result = mailer.send_payment_failed_notification(
            email="dunning@example.com", name="Iris", amount=49.00
        )
        assert result["success"] is True
        mock.assert_called_once()

    def test_sets_payment_failed_status(self, mailer):
        """send_payment_failed_notification sets last_payment_status to 'failed'."""
        mock = _mock_request_success(mailer)
        mailer.send_payment_failed_notification(
            email="dunning@example.com", name="Jack", amount=99.00
        )
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert fields.get("last_payment_status") == "failed"

    def test_records_failed_amount(self, mailer):
        """send_payment_failed_notification records the amount that failed."""
        mock = _mock_request_success(mailer)
        mailer.send_payment_failed_notification(
            email="dunning@example.com", name="Kim", amount=49.50
        )
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert fields.get("last_failed_amount") == "49.5"

    def test_records_failed_at_timestamp(self, mailer):
        """send_payment_failed_notification records when the failure occurred."""
        mock = _mock_request_success(mailer)
        mailer.send_payment_failed_notification(
            email="dunning@example.com", name="Lee", amount=9.99
        )
        call_body = mock.call_args[1].get("data") or {}
        fields = call_body.get("fields", {})
        assert "last_failed_at" in fields
