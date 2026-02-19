"""
Integration tests for the Auth API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthCheck:
    """Test the health check endpoint."""
    
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication flow."""
    
    async def test_register_user(self, client: AsyncClient):
        """Test user registration."""
        user_data = {
            "email": "testuser@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User",
            "role": "analyst",
        }
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test that duplicate email registration fails."""
        user_data = {
            "email": "duplicate@example.com",
            "password": "StrongPass123!",
            "full_name": "Duplicate User",
            "role": "analyst",
        }
        # First registration
        await client.post("/api/v1/auth/register", json=user_data)
        # Second registration with same email
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400

    async def test_login_success(self, client: AsyncClient):
        """Test successful login returns JWT."""
        # Register first
        user_data = {
            "email": "logintest@example.com",
            "password": "TestPass123!",
            "full_name": "Login Test",
            "role": "admin",
        }
        await client.post("/api/v1/auth/register", json=user_data)
        
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "logintest@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "logintest@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 400

    async def test_get_current_user(self, client: AsyncClient):
        """Test /auth/me returns current user from token."""
        # Register and login
        user_data = {
            "email": "metest@example.com",
            "password": "MePass123!",
            "full_name": "Me Test",
            "role": "manager",
        }
        await client.post("/api/v1/auth/register", json=user_data)
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "metest@example.com", "password": "MePass123!"},
        )
        token = login_resp.json()["access_token"]
        
        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "metest@example.com"

    async def test_protected_route_without_token(self, client: AsyncClient):
        """Test that protected routes require authentication."""
        response = await client.get("/api/v1/risks/")
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
class TestRiskEndpoints:
    """Test risk management endpoints."""

    async def _get_token(self, client: AsyncClient) -> str:
        """Helper: register + login and return token."""
        user_data = {
            "email": "risktest@example.com",
            "password": "RiskPass123!",
            "full_name": "Risk Tester",
            "role": "admin",
        }
        await client.post("/api/v1/auth/register", json=user_data)
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "risktest@example.com", "password": "RiskPass123!"},
        )
        return login_resp.json()["access_token"]

    async def test_list_risks_empty(self, client: AsyncClient):
        """Test listing risks when none exist."""
        token = await self._get_token(client)
        response = await client.get(
            "/api/v1/risks/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
