"""
Backend Boilerplate Tests - Config Loading
Tests business_config.json loading and API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app, BUSINESS_CONFIG

client = TestClient(app)

class TestConfigLoading:
    """Test configuration loading"""
    
    def test_config_loaded(self):
        """Test that business config is loaded"""
        assert BUSINESS_CONFIG is not None
        assert "business" in BUSINESS_CONFIG
        assert "branding" in BUSINESS_CONFIG
        assert "pricing" in BUSINESS_CONFIG
    
    def test_config_has_required_fields(self):
        """Test config has all required fields"""
        # Business info
        assert "name" in BUSINESS_CONFIG["business"]
        assert "tagline" in BUSINESS_CONFIG["business"]
        assert "domain" in BUSINESS_CONFIG["business"]
        
        # Branding
        assert "primary_color" in BUSINESS_CONFIG["branding"]
        assert "secondary_color" in BUSINESS_CONFIG["branding"]
        
        # Pricing
        assert "plans" in BUSINESS_CONFIG["pricing"]
        assert len(BUSINESS_CONFIG["pricing"]["plans"]) > 0


class TestConfigEndpoints:
    """Test config API endpoints"""
    
    def test_get_config(self):
        """Test GET /api/config"""
        response = client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return client-safe config
        assert "business" in data
        assert "branding" in data
        assert "home" in data
        assert "pricing" in data
        
        # Should NOT include sensitive data
        # (This test would need adjustment based on what's sensitive)
    
    def test_get_page_config_home(self):
        """Test GET /api/config/home"""
        response = client.get("/api/config/home")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hero" in data
        assert "features" in data
        assert "social_proof" in data
    
    def test_get_page_config_pricing(self):
        """Test GET /api/config/pricing"""
        response = client.get("/api/config/pricing")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "headline" in data
        assert "plans" in data
        assert len(data["plans"]) > 0
    
    def test_get_page_config_invalid(self):
        """Test GET /api/config/invalid_page"""
        response = client.get("/api/config/invalid_page")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test GET /health"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "business" in data
        assert data["business"] == BUSINESS_CONFIG["business"]["name"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
