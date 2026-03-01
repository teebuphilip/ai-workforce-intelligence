"""
test_stripe_metering.py — Tests for Stripe usage metering methods
==================================================================

Tests validate (Stripe Billing Meter API — stripe-python 7+):
- create_meter: creates a billing meter definition
- report_usage: submits meter events to Stripe
- get_meter_event_summaries: retrieves aggregated usage summaries
- create_metered_price: creates usage-based price (legacy metered)
- create_metered_subscription_item: adds metered line to subscription

All tests mock stripe — no real Stripe account needed.

Run:
    pytest tests/test_stripe_metering.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from stripe_lib import StripeLib, StripeConfig


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def stripe_lib():
    config = StripeConfig(config_dict={
        "stripe_secret_key": "sk_test_fake_key",
        "account_name": "TestAccount",
        "log_level": "ERROR",
    })
    return StripeLib(config)


# ============================================================
# TEST: create_meter
# ============================================================

class TestCreateMeter:

    def test_creates_billing_meter(self, stripe_lib):
        """create_meter calls billing.Meter.create with correct params."""
        mock_meter = {
            "id": "meter_abc",
            "display_name": "API Calls",
            "event_name": "api_call",
            "status": "active",
        }

        with patch("stripe.billing.Meter.create", return_value=mock_meter) as mock:
            result = stripe_lib.create_meter(
                display_name="API Calls",
                event_name="api_call",
            )

        assert result["success"] is True
        assert result["data"]["id"] == "meter_abc"
        call_kwargs = mock.call_args[1]
        assert call_kwargs["display_name"] == "API Calls"
        assert call_kwargs["event_name"] == "api_call"
        assert call_kwargs["default_aggregation"] == {"formula": "sum"}

    def test_creates_meter_with_custom_aggregation(self, stripe_lib):
        """create_meter supports non-default aggregation formulas."""
        with patch("stripe.billing.Meter.create", return_value={"id": "m1"}) as mock:
            stripe_lib.create_meter(
                display_name="Seat Count",
                event_name="seat_added",
                default_aggregation="count",
            )
        assert mock.call_args[1]["default_aggregation"] == {"formula": "count"}

    def test_creates_meter_with_custom_payload_key(self, stripe_lib):
        """create_meter passes the correct value settings payload key."""
        with patch("stripe.billing.Meter.create", return_value={"id": "m1"}) as mock:
            stripe_lib.create_meter(
                display_name="Reports",
                event_name="report_generated",
                value_settings_event_payload_key="count",
            )
        assert mock.call_args[1]["value_settings"] == {"event_payload_key": "count"}


# ============================================================
# TEST: report_usage
# ============================================================

class TestReportUsage:

    def test_reports_usage_event(self, stripe_lib):
        """report_usage calls billing.MeterEvent.create with event and customer."""
        mock_event = {
            "identifier": "evt_abc",
            "event_name": "api_call",
        }

        with patch("stripe.billing.MeterEvent.create", return_value=mock_event) as mock:
            result = stripe_lib.report_usage(
                event_name="api_call",
                value=1,
                stripe_customer_id="cus_abc123",
            )

        assert result["success"] is True
        call_kwargs = mock.call_args[1]
        assert call_kwargs["event_name"] == "api_call"
        assert call_kwargs["payload"]["stripe_customer_id"] == "cus_abc123"
        assert call_kwargs["payload"]["value"] == "1"

    def test_reports_usage_with_timestamp(self, stripe_lib):
        """report_usage passes timestamp when provided."""
        with patch("stripe.billing.MeterEvent.create", return_value={"identifier": "e1"}) as mock:
            stripe_lib.report_usage(
                event_name="api_call",
                value=5,
                stripe_customer_id="cus_abc",
                timestamp=1700000000,
            )
        assert mock.call_args[1]["timestamp"] == 1700000000

    def test_reports_usage_no_timestamp_by_default(self, stripe_lib):
        """report_usage omits timestamp when not provided (Stripe uses current time)."""
        with patch("stripe.billing.MeterEvent.create", return_value={"identifier": "e1"}) as mock:
            stripe_lib.report_usage(
                event_name="api_call", value=1, stripe_customer_id="cus_abc"
            )
        assert "timestamp" not in mock.call_args[1]

    def test_reports_usage_with_idempotency_key(self, stripe_lib):
        """report_usage passes identifier for idempotency."""
        with patch("stripe.billing.MeterEvent.create", return_value={"identifier": "e1"}) as mock:
            stripe_lib.report_usage(
                event_name="api_call",
                value=1,
                stripe_customer_id="cus_abc",
                identifier="req_12345",
            )
        assert mock.call_args[1]["identifier"] == "req_12345"

    def test_reports_usage_value_as_string_in_payload(self, stripe_lib):
        """Stripe MeterEvent requires value as a string in payload."""
        with patch("stripe.billing.MeterEvent.create", return_value={"identifier": "e1"}) as mock:
            stripe_lib.report_usage(
                event_name="api_call", value=42, stripe_customer_id="cus_abc"
            )
        assert mock.call_args[1]["payload"]["value"] == "42"


# ============================================================
# TEST: get_meter_event_summaries
# ============================================================

class TestGetMeterEventSummaries:

    def test_gets_usage_summaries(self, stripe_lib):
        """get_meter_event_summaries returns aggregated usage data."""
        mock_summaries = {
            "data": [{"aggregated_value": 150, "start_time": 1700000000}],
            "has_more": False,
        }

        with patch("stripe.billing.Meter.list_event_summaries", return_value=mock_summaries) as mock:
            result = stripe_lib.get_meter_event_summaries(
                meter_id="meter_abc",
                customer="cus_abc",
                start_time=1700000000,
                end_time=1702678400,
            )

        assert result["success"] is True
        assert result["data"]["data"][0]["aggregated_value"] == 150
        call_kwargs = mock.call_args[1]
        assert call_kwargs["id"] == "meter_abc"
        assert call_kwargs["customer"] == "cus_abc"
        assert call_kwargs["start_time"] == 1700000000
        assert call_kwargs["end_time"] == 1702678400


# ============================================================
# TEST: create_metered_price
# ============================================================

class TestCreateMeteredPrice:

    def test_creates_metered_price(self, stripe_lib, monkeypatch):
        """create_metered_price calls Price.create with metered recurring config."""
        mock_price = {
            "id": "price_meter_abc",
            "billing_scheme": "per_unit",
            "recurring": {"interval": "month", "usage_type": "metered"},
        }
        mock = MagicMock(return_value=mock_price)
        monkeypatch.setattr("stripe.Price.create", mock)

        result = stripe_lib.create_metered_price(
            product_id="prod_abc",
            unit_amount=1,
        )

        assert result["success"] is True
        assert result["data"]["id"] == "price_meter_abc"
        call_kwargs = mock.call_args[1]
        assert call_kwargs["product"] == "prod_abc"
        assert call_kwargs["unit_amount"] == 1
        assert call_kwargs["recurring"]["usage_type"] == "metered"
        assert call_kwargs["recurring"]["interval"] == "month"

    def test_metered_price_uses_per_unit_billing_scheme(self, stripe_lib, monkeypatch):
        """create_metered_price defaults to per_unit billing scheme."""
        mock = MagicMock(return_value={"id": "p1"})
        monkeypatch.setattr("stripe.Price.create", mock)
        stripe_lib.create_metered_price(product_id="prod_abc", unit_amount=5)
        assert mock.call_args[1]["billing_scheme"] == "per_unit"

    def test_metered_price_passes_currency(self, stripe_lib, monkeypatch):
        """create_metered_price passes the currency to Stripe."""
        mock = MagicMock(return_value={"id": "p1"})
        monkeypatch.setattr("stripe.Price.create", mock)
        stripe_lib.create_metered_price(
            product_id="prod_abc", unit_amount=10, currency="eur"
        )
        assert mock.call_args[1]["currency"] == "eur"


# ============================================================
# TEST: create_metered_subscription_item
# ============================================================

class TestCreateMeteredSubscriptionItem:

    def test_adds_metered_item_to_subscription(self, stripe_lib, monkeypatch):
        """create_metered_subscription_item adds a metered price to a subscription."""
        mock_item = {
            "id": "si_new",
            "subscription": "sub_abc",
            "price": {"id": "price_meter_abc"},
        }
        mock = MagicMock(return_value=mock_item)
        monkeypatch.setattr("stripe.SubscriptionItem.create", mock)

        result = stripe_lib.create_metered_subscription_item(
            subscription_id="sub_abc",
            price_id="price_meter_abc",
        )

        assert result["success"] is True
        assert result["data"]["id"] == "si_new"
        call_kwargs = mock.call_args[1]
        assert call_kwargs["subscription"] == "sub_abc"
        assert call_kwargs["price"] == "price_meter_abc"
