"""Pytest configuration and fixtures."""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base, get_db, User
from main import app
from auth import hash_password, create_access_token


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    database_url = "sqlite:///./test.db"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Create a test database session."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create a test admin user."""
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_token(test_user):
    """Create a test JWT token."""
    return create_access_token(test_user.id, test_user.username)


@pytest.fixture
def admin_token(admin_user):
    """Create a test admin JWT token."""
    return create_access_token(admin_user.id, admin_user.username)


@pytest.fixture
def auth_headers(test_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """Create admin authorization headers."""
    return {"Authorization": f"Bearer {admin_token}"}
