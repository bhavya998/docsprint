"""Tests for authentication endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestRegister:
    """Test user registration."""

    def test_register_success(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "password123"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["plan"] == "free"
        assert data["user"]["api_key"].startswith("dsk_")

    def test_register_duplicate_email(self, client: TestClient):
        client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "password123"},
        )
        assert resp.status_code == 409

    def test_register_short_password(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert resp.status_code == 422


class TestLogin:
    """Test user login."""

    def test_login_success(self, client: TestClient, test_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client: TestClient, test_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert resp.status_code == 401


class TestMe:
    """Test the /auth/me endpoint."""

    def test_me_with_bearer(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["api_key"].startswith("dsk_")

    def test_me_with_api_key(self, client: TestClient, api_key_headers):
        resp = client.get("/api/v1/auth/me", headers=api_key_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"

    def test_me_no_auth(self, client: TestClient):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client: TestClient):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert resp.status_code == 401