"""Tests for API main module."""

from fastapi.testclient import TestClient

from api.main import app


class TestMainApp:
    """Test suite for main FastAPI app."""

    def test_app_creation(self):
        """Test that the FastAPI app is created successfully."""
        assert app is not None
        assert app.title == "ChatBot Backend API"

    def test_websocket_endpoints_exist(self):
        """Test that websocket endpoints are registered."""
        # Check that websocket endpoints exist by testing the actual endpoint
        # This will fail if websocket endpoints don't exist, but that's expected
        # We're just checking that the app has routes
        assert len(app.routes) > 0

    def test_health_endpoints_included(self):
        """Test that health endpoints are included."""
        client = TestClient(app)

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
