"""
Backend Boilerplate Tests - Payment Routes
Tests generic payment and subscription endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

class TestPaymentRoutes:
    """Test payment and subscription endpoints"""
    
    @patch('main.analytics')
    def test_subscribe_success(self, mock_analytics):
        """Test creating subscription checkout"""
        mock_analytics.track_begin_checkout.return_value = {"success": True}
        
        response = client.post("/api/subscribe", json={
            "price_id": "price_monthly_pro",
            "user_id": "auth0|123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "payment_link" in data
        
        # Verify analytics was tracked
        mock_analytics.track_begin_checkout.assert_called_once()
    
    def test_subscribe_invalid_plan(self):
        """Test subscription with invalid plan"""
        response = client.post("/api/subscribe", json={
            "price_id": "price_invalid",
            "user_id": "auth0|123"
        })
        
        assert response.status_code == 404
        assert "Plan not found" in response.json()["detail"]
    
    @patch('main.stripe')
    @patch('main.analytics')
    def test_cancel_subscription_success(self, mock_analytics, mock_stripe):
        """Test canceling subscription"""
        mock_stripe.cancel_subscription.return_value = {
            "success": True,
            "data": {"status": "canceled"}
        }
        
        mock_analytics.track_subscription_cancel.return_value = {"success": True}
        
        response = client.post("/api/cancel-subscription", params={
            "subscription_id": "sub_123",
            "user_id": "auth0|123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        
        # Verify Stripe was called with correct params
        mock_stripe.cancel_subscription.assert_called_once_with(
            subscription_id="sub_123",
            at_period_end=True
        )
        
        # Verify analytics was tracked
        mock_analytics.track_subscription_cancel.assert_called_once()
    
    @patch('main.stripe')
    def test_cancel_subscription_failure(self, mock_stripe):
        """Test canceling subscription when Stripe fails"""
        mock_stripe.cancel_subscription.return_value = {
            "success": False,
            "error": "Subscription not found"
        }
        
        response = client.post("/api/cancel-subscription", params={
            "subscription_id": "sub_invalid",
            "user_id": "auth0|123"
        })
        
        assert response.status_code == 400
        assert "Subscription not found" in response.json()["detail"]


class TestWebhooks:
    """Test webhook endpoints"""
    
    @patch('main.stripe')
    @patch('main.analytics')
    @patch('main.auth0')
    def test_stripe_webhook_subscription_created(self, mock_auth0, mock_analytics, mock_stripe):
        """Test Stripe webhook for subscription.created"""
        # Mock webhook verification
        mock_stripe.verify_webhook_signature.return_value = {
            "success": True,
            "event": {
                "type": "customer.subscription.created",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "metadata": {"user_id": "auth0|123"}
                    }
                }
            }
        }
        
        mock_analytics.track_stripe_webhook.return_value = {"success": True}
        mock_auth0.update_user.return_value = {"success": True}
        
        response = client.post(
            "/api/webhooks/stripe",
            json={"type": "customer.subscription.created"},
            headers={"X-Webhook-Signature": "valid_signature"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify analytics tracked webhook
        mock_analytics.track_stripe_webhook.assert_called_once()
        
        # Verify user was updated in Auth0
        mock_auth0.update_user.assert_called_once()
    
    @patch('main.stripe')
    def test_stripe_webhook_invalid_signature(self, mock_stripe):
        """Test webhook with invalid signature"""
        mock_stripe.verify_webhook_signature.return_value = {
            "success": False,
            "error": "Invalid signature"
        }
        
        response = client.post(
            "/api/webhooks/stripe",
            json={"type": "test"},
            headers={"X-Webhook-Signature": "invalid"}
        )
        
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
