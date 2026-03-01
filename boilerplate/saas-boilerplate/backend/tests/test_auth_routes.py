"""
Backend Boilerplate Tests - Auth Routes
Tests generic authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

class TestAuthRoutes:
    """Test authentication endpoints"""
    
    @patch('main.auth0')
    @patch('main.mailer')
    @patch('main.analytics')
    def test_signup_success(self, mock_analytics, mock_mailer, mock_auth0):
        """Test successful user signup"""
        # Mock Auth0 user creation
        mock_auth0.create_user.return_value = {
            "success": True,
            "data": {"user_id": "auth0|123"}
        }
        
        # Mock MailerLite subscription
        mock_mailer.add_subscriber.return_value = {
            "success": True
        }
        
        # Mock analytics tracking
        mock_analytics.track_signup.return_value = {
            "success": True
        }
        
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "Test User"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["user_id"] == "auth0|123"
        
        # Verify Auth0 was called
        mock_auth0.create_user.assert_called_once()
        
        # Verify MailerLite was called
        mock_mailer.add_subscriber.assert_called_once_with(
            email="test@example.com",
            fields={"name": "Test User"}
        )
        
        # Verify analytics was tracked
        mock_analytics.track_signup.assert_called_once()
    
    @patch('main.auth0')
    def test_signup_auth0_failure(self, mock_auth0):
        """Test signup when Auth0 fails"""
        mock_auth0.create_user.return_value = {
            "success": False,
            "error": "Email already exists"
        }
        
        response = client.post("/api/auth/signup", json={
            "email": "existing@example.com",
            "password": "SecurePass123!",
            "name": "Test User"
        })
        
        assert response.status_code == 400
        assert "Email already exists" in response.json()["detail"]
    
    @patch('main.auth0')
    def test_send_verification_success(self, mock_auth0):
        """Test sending verification email"""
        mock_auth0.send_verification_email.return_value = {
            "success": True
        }
        
        response = client.post("/api/auth/send-verification", params={
            "user_id": "auth0|123"
        })
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        mock_auth0.send_verification_email.assert_called_once_with(
            user_id="auth0|123"
        )
    
    @patch('main.auth0')
    def test_password_reset_success(self, mock_auth0):
        """Test password reset request"""
        mock_auth0.send_password_reset_email.return_value = {
            "success": True
        }
        
        response = client.post("/api/auth/password-reset", params={
            "email": "test@example.com"
        })
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        mock_auth0.send_password_reset_email.assert_called_once_with(
            email="test@example.com"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
