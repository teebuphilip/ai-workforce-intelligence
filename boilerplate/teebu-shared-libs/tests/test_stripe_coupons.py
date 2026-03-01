"""
test_stripe_coupons.py — Tests for Stripe coupon & discount methods
====================================================================

Tests validate:
- create_coupon: percent-off and amount-off coupons
- create_promo_code: readable code generation
- apply_coupon_to_subscription: attach discount to subscription
- retrieve_coupon / list_coupons / delete_coupon

All tests mock stripe — no real Stripe account needed.

Run:
    pytest tests/test_stripe_coupons.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from stripe_lib import StripeLib, StripeConfig


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def stripe_lib():
    """StripeLib instance with fake key — no real Stripe calls."""
    config = StripeConfig(config_dict={
        "stripe_secret_key": "sk_test_fake_key",
        "account_name": "TestAccount",
        "log_level": "ERROR",  # Suppress log noise in tests
    })
    return StripeLib(config)


def _mock_stripe(monkeypatch, method_path, return_value):
    """Patch a stripe SDK method and return a MagicMock."""
    mock = MagicMock(return_value=return_value)
    monkeypatch.setattr(method_path, mock)
    return mock


# ============================================================
# TEST: create_coupon
# ============================================================

class TestCreateCoupon:

    def test_creates_percent_off_coupon(self, stripe_lib, monkeypatch):
        """create_coupon returns coupon data for a percent-off discount."""
        mock_coupon = {"id": "coupon_abc", "percent_off": 50.0, "duration": "once"}
        mock = _mock_stripe(monkeypatch, "stripe.Coupon.create", mock_coupon)

        result = stripe_lib.create_coupon(name="LAUNCH50", percent_off=50.0)

        assert result["success"] is True
        assert result["data"]["id"] == "coupon_abc"
        assert result["data"]["percent_off"] == 50.0
        mock.assert_called_once()
        call_kwargs = mock.call_args[1]
        assert call_kwargs["percent_off"] == 50.0
        assert call_kwargs["name"] == "LAUNCH50"

    def test_creates_amount_off_coupon(self, stripe_lib, monkeypatch):
        """create_coupon returns coupon data for a fixed amount-off discount."""
        mock_coupon = {"id": "coupon_xyz", "amount_off": 1000, "currency": "usd"}
        _mock_stripe(monkeypatch, "stripe.Coupon.create", mock_coupon)

        result = stripe_lib.create_coupon(name="FLAT10", amount_off=1000, currency="usd")

        assert result["success"] is True
        assert result["data"]["amount_off"] == 1000

    def test_returns_error_when_neither_specified(self, stripe_lib):
        """create_coupon fails without percent_off or amount_off."""
        result = stripe_lib.create_coupon(name="BAD")
        assert result["success"] is False
        assert "percent_off or amount_off" in result["error"]

    def test_returns_error_when_both_specified(self, stripe_lib):
        """create_coupon fails when both percent_off and amount_off are given."""
        result = stripe_lib.create_coupon(
            name="BAD", percent_off=20.0, amount_off=500
        )
        assert result["success"] is False
        assert "not both" in result["error"]

    def test_creates_coupon_with_max_redemptions(self, stripe_lib, monkeypatch):
        """create_coupon passes max_redemptions to Stripe."""
        mock_coupon = {"id": "coupon_limited", "max_redemptions": 100}
        mock = _mock_stripe(monkeypatch, "stripe.Coupon.create", mock_coupon)

        stripe_lib.create_coupon(name="LIMITED", percent_off=10.0, max_redemptions=100)

        call_kwargs = mock.call_args[1]
        assert call_kwargs["max_redemptions"] == 100

    def test_creates_forever_duration_coupon(self, stripe_lib, monkeypatch):
        """create_coupon supports 'forever' duration for recurring discounts."""
        _mock_stripe(monkeypatch, "stripe.Coupon.create", {"id": "c1", "duration": "forever"})
        result = stripe_lib.create_coupon(name="FOREVER30", percent_off=30.0, duration="forever")
        assert result["success"] is True


# ============================================================
# TEST: create_promo_code
# ============================================================

class TestCreatePromoCode:

    def test_creates_promo_code_with_custom_code(self, stripe_lib, monkeypatch):
        """create_promo_code creates a readable promo code."""
        mock_promo = {"id": "promo_abc", "code": "LAUNCH50", "coupon": {"id": "coupon_abc"}}
        mock = _mock_stripe(monkeypatch, "stripe.PromotionCode.create", mock_promo)

        result = stripe_lib.create_promo_code(coupon_id="coupon_abc", code="LAUNCH50")

        assert result["success"] is True
        assert result["data"]["code"] == "LAUNCH50"
        call_kwargs = mock.call_args[1]
        assert call_kwargs["coupon"] == "coupon_abc"
        assert call_kwargs["code"] == "LAUNCH50"

    def test_creates_promo_code_without_code(self, stripe_lib, monkeypatch):
        """create_promo_code lets Stripe auto-generate the code when omitted."""
        mock_promo = {"id": "promo_xyz", "code": "AUTO123"}
        mock = _mock_stripe(monkeypatch, "stripe.PromotionCode.create", mock_promo)

        stripe_lib.create_promo_code(coupon_id="coupon_abc")

        call_kwargs = mock.call_args[1]
        assert "code" not in call_kwargs  # Not passed — let Stripe generate

    def test_creates_promo_code_with_max_redemptions(self, stripe_lib, monkeypatch):
        """create_promo_code passes max_redemptions to Stripe."""
        mock = _mock_stripe(monkeypatch, "stripe.PromotionCode.create", {"id": "p1"})
        stripe_lib.create_promo_code(coupon_id="c1", code="LIMITED", max_redemptions=50)
        assert mock.call_args[1]["max_redemptions"] == 50


# ============================================================
# TEST: apply_coupon_to_subscription
# ============================================================

class TestApplyCouponToSubscription:

    def test_applies_coupon_to_subscription(self, stripe_lib, monkeypatch):
        """apply_coupon_to_subscription calls Subscription.modify with coupon."""
        mock_sub = {"id": "sub_abc", "discount": {"coupon": {"id": "coupon_abc"}}}
        mock = _mock_stripe(monkeypatch, "stripe.Subscription.modify", mock_sub)

        result = stripe_lib.apply_coupon_to_subscription(
            subscription_id="sub_abc", coupon_id="coupon_abc"
        )

        assert result["success"] is True
        call_kwargs = mock.call_args[1]
        assert call_kwargs["coupon"] == "coupon_abc"
        assert call_kwargs["sid"] == "sub_abc"


# ============================================================
# TEST: retrieve_coupon
# ============================================================

class TestRetrieveCoupon:

    def test_retrieves_coupon(self, stripe_lib, monkeypatch):
        """retrieve_coupon returns coupon data by ID."""
        mock_coupon = {"id": "coupon_abc", "percent_off": 50.0}
        mock = _mock_stripe(monkeypatch, "stripe.Coupon.retrieve", mock_coupon)

        result = stripe_lib.retrieve_coupon("coupon_abc")

        assert result["success"] is True
        assert result["data"]["id"] == "coupon_abc"
        assert mock.call_args[1]["id"] == "coupon_abc"


# ============================================================
# TEST: list_coupons
# ============================================================

class TestListCoupons:

    def test_lists_all_coupons(self, stripe_lib, monkeypatch):
        """list_coupons returns all coupons from the account."""
        mock_list = {"data": [{"id": "c1"}, {"id": "c2"}], "has_more": False}
        _mock_stripe(monkeypatch, "stripe.Coupon.list", mock_list)

        result = stripe_lib.list_coupons()

        assert result["success"] is True
        assert len(result["data"]["data"]) == 2


# ============================================================
# TEST: delete_coupon
# ============================================================

class TestDeleteCoupon:

    def test_deletes_coupon(self, stripe_lib, monkeypatch):
        """delete_coupon archives the coupon and returns confirmation."""
        mock_deleted = {"id": "coupon_abc", "deleted": True}
        mock = _mock_stripe(monkeypatch, "stripe.Coupon.delete", mock_deleted)

        result = stripe_lib.delete_coupon("coupon_abc")

        assert result["success"] is True
        assert result["data"]["deleted"] is True
        assert mock.call_args[1]["sid"] == "coupon_abc"
