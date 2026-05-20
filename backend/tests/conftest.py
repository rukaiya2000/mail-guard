"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from main import app
from auth import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_token():
    return create_access_token(
        google_id="test-google-id",
        username="testuser",
        email="test@example.com",
    )


@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}
