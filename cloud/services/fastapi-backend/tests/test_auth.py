"""Tests for the ILEWS authentication endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.users import User
from app.utils.security import create_access_token, hash_password

TEST_PASSWORD = "s3cure-pass!"
_HASHED = hash_password(TEST_PASSWORD)


def _make_user(**overrides):
    """Build a mock User object with sensible defaults."""
    user = MagicMock(spec=User)
    defaults = {
        "user_id": "USR001",
        "email": "test@ilews.io",
        "name": "Test User",
        "role": "operator",
        "is_active": True,
        "password_hash": _HASHED,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _override_db(user=None):
    """Return a get_db override whose session.execute always returns *user*."""

    async def _get_db():
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = user
        session.execute.return_value = result
        yield session

    return _get_db


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


# ── Login ────────────────────────────────────────────────────────────────


def test_login_success():
    user = _make_user()
    app.dependency_overrides[get_db] = _override_db(user)
    client = TestClient(app)

    resp = client.post(
        "/auth/token",
        data={"username": "test@ilews.io", "password": TEST_PASSWORD},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_login_invalid_password():
    user = _make_user()
    app.dependency_overrides[get_db] = _override_db(user)
    client = TestClient(app)

    resp = client.post(
        "/auth/token",
        data={"username": "test@ilews.io", "password": "wrong-password"},
    )

    assert resp.status_code == 401


# ── Protected endpoint (/auth/me) ───────────────────────────────────────


def test_protected_endpoint_without_token():
    client = TestClient(app)

    resp = client.get("/auth/me")

    assert resp.status_code == 401


def test_protected_endpoint_with_valid_token():
    user = _make_user()
    app.dependency_overrides[get_db] = _override_db(user)
    client = TestClient(app)

    token = create_access_token({"sub": "USR001", "role": "operator"})
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "USR001"
    assert body["email"] == "test@ilews.io"
    assert body["role"] == "operator"
