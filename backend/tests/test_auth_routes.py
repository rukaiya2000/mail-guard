"""Tests for authentication routes."""

import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestRegister:
    """Tests for user registration."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "weak"
            }
        )
        assert response.status_code == 400
        assert "Password must be at least 8 characters" in response.json()["detail"]

    def test_register_password_no_uppercase(self, client):
        """Test registration with password missing uppercase."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "lowercase123!"
            }
        )
        assert response.status_code == 400
        assert "uppercase" in response.json()["detail"]

    def test_register_password_no_digit(self, client):
        """Test registration with password missing digit."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "NoDigits!"
            }
        )
        assert response.status_code == 400
        assert "digit" in response.json()["detail"]

    def test_register_password_no_special(self, client):
        """Test registration with password missing special character."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "NoSpecial123"
            }
        )
        assert response.status_code == 400
        assert "special character" in response.json()["detail"]

    def test_register_invalid_username(self, client):
        """Test registration with invalid username."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "ab",
                "email": "new@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "newuser",
                "email": "not-an-email",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 422

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with existing username."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": test_user.username,
                "email": "different@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 400
        assert "Username already exists" in response.json()["detail"]

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email."""
        response = client.post(
            "/api/v1/register",
            json={
                "username": "differentuser",
                "email": test_user.email,
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 400
        assert "Email already exists" in response.json()["detail"]


@pytest.mark.unit
class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/login",
            json={
                "username": test_user.username,
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert "access_token" in data

    def test_login_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post(
            "/api/v1/login",
            json={
                "username": "nonexistent",
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/login",
            json={
                "username": test_user.username,
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_empty_password(self, client, test_user):
        """Test login with empty password."""
        response = client.post(
            "/api/v1/login",
            json={
                "username": test_user.username,
                "password": ""
            }
        )
        assert response.status_code == 401


@pytest.mark.unit
class TestGetMe:
    """Tests for get current user endpoint."""

    def test_get_me_authenticated(self, client, test_user, auth_headers):
        """Test getting current user info when authenticated."""
        response = client.get("/api/v1/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id

    def test_get_me_unauthenticated(self, client):
        """Test getting current user info when not authenticated."""
        response = client.get("/api/v1/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self, client):
        """Test getting current user info with invalid token."""
        response = client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 403
