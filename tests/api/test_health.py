"""Tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test the root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "ChatBot Backend API" in data["message"]

    def test_health_check_endpoint(self, client: TestClient) -> None:
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Check required fields based on actual API structure
        assert "status" in data
        assert "active_connections" in data
        assert "chatbot_ready" in data

        # Check values
        assert isinstance(data["active_connections"], int)
        assert isinstance(data["chatbot_ready"], bool)

    @pytest.mark.integration
    def test_config_endpoint_not_available_in_test(self, client: TestClient) -> None:
        """Test that config endpoint returns 404 in test mode."""
        # In test mode, the config endpoint is not available
        response = client.get("/config")
        assert response.status_code == 404
