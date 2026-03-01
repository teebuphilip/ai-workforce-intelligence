"""
Backend Boilerplate Tests - Analytics Routes
Tests analytics tracking endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

class TestAnalyticsRoutes:
    """Test analytics endpoints"""
    
    @patch('main.analytics')
    def test_track_event_success(self, mock_analytics):
        """Test tracking custom event"""
        mock_analytics.track_event.return_value = {"success": True}
        
        response = client.post("/api/analytics/track", json={
            "event_name": "button_clicked",
            "user_id": "auth0|123",
            "event_params": {"button": "save"}
        })
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify analytics was called
        mock_analytics.track_event.assert_called_once_with(
            event_name="button_clicked",
            client_id=None,
            user_id="auth0|123",
            event_params={"button": "save"}
        )
    
    @patch('main.analytics')
    def test_track_event_failure_doesnt_break(self, mock_analytics):
        """Test that analytics failures don't break the app"""
        mock_analytics.track_event.return_value = {
            "success": False,
            "error": "Network error"
        }
        
        response = client.post("/api/analytics/track", json={
            "event_name": "test_event"
        })
        
        # Should still return success (analytics is non-critical)
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    @patch('main.analytics')
    def test_track_page_view_success(self, mock_analytics):
        """Test tracking page view"""
        mock_analytics.track_page_view.return_value = {"success": True}
        
        response = client.post("/api/analytics/page-view", params={
            "page_path": "/pricing",
            "page_title": "Pricing Page",
            "user_id": "auth0|123"
        })
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify analytics was called
        mock_analytics.track_page_view.assert_called_once()
    
    @patch('main.analytics')
    def test_track_page_view_minimal_params(self, mock_analytics):
        """Test page view with minimal params"""
        mock_analytics.track_page_view.return_value = {"success": True}
        
        response = client.post("/api/analytics/page-view", params={
            "page_path": "/"
        })
        
        assert response.status_code == 200
        mock_analytics.track_page_view.assert_called_once_with(
            page_path="/",
            page_title=None,
            client_id=None,
            user_id=None
        )


class TestContactForm:
    """Test contact form endpoint"""
    
    @patch('main.mailer')
    @patch('main.analytics')
    def test_contact_form_success(self, mock_analytics, mock_mailer):
        """Test contact form submission"""
        mock_mailer.add_subscriber.return_value = {"success": True}
        mock_analytics.track_event.return_value = {"success": True}
        
        response = client.post("/api/contact", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "General Question",
            "message": "This is a test message"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "get back to you" in data["message"]
        
        # Verify MailerLite was called
        mock_mailer.add_subscriber.assert_called_once()
        
        # Verify analytics was tracked
        mock_analytics.track_event.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
