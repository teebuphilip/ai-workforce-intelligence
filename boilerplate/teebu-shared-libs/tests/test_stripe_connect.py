"""
test_stripe_connect.py — Tests for Stripe Connect (escrow/split payments)
=========================================================================

Tests validate:
- create_connected_account: Express account creation for sellers
- create_account_onboarding_link: Onboarding URL generation
- create_payment_intent_with_split: Platform payment with fee split
- transfer_to_connected_account: Manual payout to seller
- retrieve_connected_account: Account status lookup
- list_connected_accounts: Platform account listing

All tests mock stripe — no real Stripe account needed.

Run:
    pytest tests/test_stripe_connect.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from stripe_lib import StripeConnectLib, StripeConfig, load_stripe_connect_lib


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def connect_lib():
    config = StripeConfig(config_dict={
        "stripe_secret_key": "sk_test_fake_key",
        "account_name": "TestPlatform",
        "log_level": "ERROR",
    })
    return StripeConnectLib(config)


def _mock_stripe(monkeypatch, method_path, return_value):
    mock = MagicMock(return_value=return_value)
    monkeypatch.setattr(method_path, mock)
    return mock


# ============================================================
# TEST: create_connected_account
# ============================================================

class TestCreateConnectedAccount:

    def test_creates_express_account(self, connect_lib, monkeypatch):
        """create_connected_account creates an Express Stripe Connect account."""
        mock_account = {
            "id": "acct_abc123",
            "type": "express",
            "email": "seller@example.com",
            "country": "US",
        }
        mock = _mock_stripe(monkeypatch, "stripe.Account.create", mock_account)

        result = connect_lib.create_connected_account(email="seller@example.com")

        assert result["success"] is True
        assert result["data"]["id"] == "acct_abc123"
        assert result["data"]["type"] == "express"
        call_kwargs = mock.call_args[1]
        assert call_kwargs["email"] == "seller@example.com"
        assert call_kwargs["type"] == "express"
        assert call_kwargs["country"] == "US"

    def test_creates_account_with_custom_country(self, connect_lib, monkeypatch):
        """create_connected_account respects non-US country."""
        mock = _mock_stripe(monkeypatch, "stripe.Account.create", {"id": "acct_uk"})
        connect_lib.create_connected_account(email="uk@example.com", country="GB")
        assert mock.call_args[1]["country"] == "GB"

    def test_creates_standard_account_type(self, connect_lib, monkeypatch):
        """create_connected_account supports 'standard' account type."""
        mock = _mock_stripe(monkeypatch, "stripe.Account.create", {"id": "acct_std"})
        connect_lib.create_connected_account(
            email="seller@example.com", account_type="standard"
        )
        assert mock.call_args[1]["type"] == "standard"


# ============================================================
# TEST: create_account_onboarding_link
# ============================================================

class TestCreateAccountOnboardingLink:

    def test_creates_onboarding_link(self, connect_lib, monkeypatch):
        """create_account_onboarding_link returns a Stripe-hosted onboarding URL."""
        mock_link = {
            "object": "account_link",
            "url": "https://connect.stripe.com/setup/e/acct_abc123/xyz",
            "expires_at": 1700010000,
        }
        mock = _mock_stripe(monkeypatch, "stripe.AccountLink.create", mock_link)

        result = connect_lib.create_account_onboarding_link(
            account_id="acct_abc123",
            refresh_url="https://myapp.com/onboard/refresh",
            return_url="https://myapp.com/onboard/complete",
        )

        assert result["success"] is True
        assert "stripe.com" in result["data"]["url"]
        call_kwargs = mock.call_args[1]
        assert call_kwargs["account"] == "acct_abc123"
        assert call_kwargs["type"] == "account_onboarding"
        assert call_kwargs["return_url"] == "https://myapp.com/onboard/complete"
        assert call_kwargs["refresh_url"] == "https://myapp.com/onboard/refresh"


# ============================================================
# TEST: create_payment_intent_with_split
# ============================================================

class TestCreatePaymentIntentWithSplit:

    def test_creates_split_payment_intent(self, connect_lib, monkeypatch):
        """create_payment_intent_with_split routes payment with platform fee."""
        mock_pi = {
            "id": "pi_abc",
            "amount": 10000,
            "application_fee_amount": 1000,
            "client_secret": "pi_abc_secret_xyz",
            "transfer_data": {"destination": "acct_seller"},
        }
        mock = _mock_stripe(monkeypatch, "stripe.PaymentIntent.create", mock_pi)

        result = connect_lib.create_payment_intent_with_split(
            amount=10000,
            currency="usd",
            application_fee_amount=1000,
            connected_account_id="acct_seller",
        )

        assert result["success"] is True
        assert result["data"]["amount"] == 10000
        call_kwargs = mock.call_args[1]
        assert call_kwargs["amount"] == 10000
        assert call_kwargs["application_fee_amount"] == 1000
        assert call_kwargs["transfer_data"]["destination"] == "acct_seller"
        assert call_kwargs["currency"] == "usd"

    def test_seller_receives_amount_minus_fee(self, connect_lib, monkeypatch):
        """Platform fee is separate from total — seller keeps the remainder."""
        # This validates the business logic: buyer pays 100, platform keeps 10,
        # seller receives 90. Test confirms fee is correctly parameterized.
        mock = _mock_stripe(monkeypatch, "stripe.PaymentIntent.create", {"id": "pi_1"})

        connect_lib.create_payment_intent_with_split(
            amount=10000,        # $100
            currency="usd",
            application_fee_amount=1000,  # $10 platform fee
            connected_account_id="acct_seller",
        )

        call_kwargs = mock.call_args[1]
        seller_amount = call_kwargs["amount"] - call_kwargs["application_fee_amount"]
        assert seller_amount == 9000  # $90 to seller


# ============================================================
# TEST: transfer_to_connected_account
# ============================================================

class TestTransferToConnectedAccount:

    def test_transfers_funds(self, connect_lib, monkeypatch):
        """transfer_to_connected_account creates a Stripe Transfer."""
        mock_transfer = {
            "id": "tr_abc",
            "amount": 5000,
            "destination": "acct_seller",
        }
        mock = _mock_stripe(monkeypatch, "stripe.Transfer.create", mock_transfer)

        result = connect_lib.transfer_to_connected_account(
            amount=5000,
            currency="usd",
            destination_account_id="acct_seller",
        )

        assert result["success"] is True
        assert result["data"]["amount"] == 5000
        call_kwargs = mock.call_args[1]
        assert call_kwargs["amount"] == 5000
        assert call_kwargs["destination"] == "acct_seller"
        assert call_kwargs["currency"] == "usd"

    def test_transfer_with_description(self, connect_lib, monkeypatch):
        """transfer_to_connected_account passes description when provided."""
        mock = _mock_stripe(monkeypatch, "stripe.Transfer.create", {"id": "tr_1"})
        connect_lib.transfer_to_connected_account(
            amount=2500,
            currency="usd",
            destination_account_id="acct_seller",
            description="Payout for order #1234",
        )
        assert mock.call_args[1]["description"] == "Payout for order #1234"

    def test_transfer_without_description(self, connect_lib, monkeypatch):
        """transfer_to_connected_account omits description when not provided."""
        mock = _mock_stripe(monkeypatch, "stripe.Transfer.create", {"id": "tr_1"})
        connect_lib.transfer_to_connected_account(
            amount=1000, currency="usd", destination_account_id="acct_seller"
        )
        assert "description" not in mock.call_args[1]


# ============================================================
# TEST: retrieve_connected_account
# ============================================================

class TestRetrieveConnectedAccount:

    def test_retrieves_account_details(self, connect_lib, monkeypatch):
        """retrieve_connected_account returns account details by ID."""
        mock_account = {
            "id": "acct_abc",
            "payouts_enabled": True,
            "charges_enabled": True,
        }
        mock = _mock_stripe(monkeypatch, "stripe.Account.retrieve", mock_account)

        result = connect_lib.retrieve_connected_account("acct_abc")

        assert result["success"] is True
        assert result["data"]["payouts_enabled"] is True
        assert mock.call_args[1]["id"] == "acct_abc"


# ============================================================
# TEST: list_connected_accounts
# ============================================================

class TestListConnectedAccounts:

    def test_lists_all_accounts(self, connect_lib, monkeypatch):
        """list_connected_accounts returns all platform-connected accounts."""
        mock_list = {
            "data": [{"id": "acct_1"}, {"id": "acct_2"}],
            "has_more": False,
        }
        _mock_stripe(monkeypatch, "stripe.Account.list", mock_list)

        result = connect_lib.list_connected_accounts()

        assert result["success"] is True
        assert len(result["data"]["data"]) == 2


# ============================================================
# TEST: load_stripe_connect_lib (loader function)
# ============================================================

class TestLoadStripeConnectLib:

    def test_loader_raises_without_config(self):
        """load_stripe_connect_lib raises when config file not found."""
        with pytest.raises((FileNotFoundError, ValueError)):
            load_stripe_connect_lib("/nonexistent/path/config.json")
