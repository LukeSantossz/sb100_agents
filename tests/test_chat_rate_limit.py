"""Tests for the per-user rate limit on POST /chat (#110).

Covers the SPEC acceptance criteria: the limit key derives from the JWT
subject (with a client-IP fallback), and POST /chat returns 429 once a user
exceeds ``settings.chat_rate_limit`` — enforced independently per user.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import limiter, verify_token
from api.main import app
from api.routes.auth import create_access_token
from api.routes.chat import _rate_limit_key, _sessions
from core.config import settings
from database.db import Base, get_db
from database.models import User

CLIENT_IP = "203.0.113.7"


def _make_request(headers: dict[str, str], client_host: str = CLIENT_IP) -> Request:
    """Build a minimal ASGI ``Request`` carrying the given headers and client."""
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def _bearer(subject: str) -> dict[str, str]:
    """Authorization header carrying a valid JWT for ``subject``."""
    token = create_access_token({"sub": subject}, expires_delta=timedelta(minutes=5))
    return {"Authorization": f"Bearer {token}"}


# ----------------------------- _rate_limit_key -----------------------------


def test_rate_limit_key_returns_jwt_subject() -> None:
    """The key is the token's ``sub``: distinct users differ, the same user matches."""
    key_alice = _rate_limit_key(_make_request(_bearer("alice")))
    key_alice_again = _rate_limit_key(_make_request(_bearer("alice")))
    key_bob = _rate_limit_key(_make_request(_bearer("bob")))

    assert key_alice == "alice"
    assert key_alice == key_alice_again
    assert key_alice != key_bob


def test_rate_limit_key_falls_back_to_ip_without_token() -> None:
    """A missing or invalid bearer token yields the client address, no exception."""
    missing = _rate_limit_key(_make_request({}, client_host="198.51.100.4"))
    invalid = _rate_limit_key(
        _make_request({"Authorization": "Bearer not-a-jwt"}, client_host="198.51.100.4")
    )

    assert missing == "198.51.100.4"
    assert invalid == "198.51.100.4"


# ----------------------------- POST /chat 429 -----------------------------


def _override_verify_token() -> User:
    """JWT gate stub — returns a fixed user without hitting the database."""
    return User(id=1, username="testuser", hashed_password="x", created_at=datetime.now(UTC))


@pytest.fixture(autouse=True)
def db_setup() -> Generator[None, None, None]:
    """In-memory SQLite setup for rate limit testing, seeded with users."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed users to prevent foreign key errors
        testuser = User(id=1, username="testuser", hashed_password="x", created_at=datetime.now(UTC))
        heavy = User(id=2, username="heavy-user", hashed_password="x", created_at=datetime.now(UTC))
        usera = User(id=3, username="user-a", hashed_password="x", created_at=datetime.now(UTC))
        userb = User(id=4, username="user-b", hashed_password="x", created_at=datetime.now(UTC))
        db.add(testuser)
        db.add(heavy)
        db.add(usera)
        db.add(userb)
        db.commit()
    finally:
        db.close()

    def _get_testing_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_testing_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _reset_state() -> Generator[None, None, None]:
    """Start each test with an empty session cache and clean limiter storage."""
    _sessions.clear()
    limiter.reset()
    yield
    _sessions.clear()
    limiter.reset()


@pytest.fixture
def low_chat_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lower the per-user chat limit so the threshold is cheap to exercise."""
    monkeypatch.setattr(settings, "chat_rate_limit", "3/minute")


@pytest.fixture
def chat_client() -> Generator[TestClient, None, None]:
    """TestClient with the JWT gate and RAG pipeline mocked (no real infra)."""
    app.dependency_overrides[verify_token] = _override_verify_token
    with (
        patch("api.routes.chat.generate_embedding", return_value=[0.1] * 768),
        patch("api.routes.chat.search_context", return_value=["chunk"]),
        patch("api.routes.chat.generate", return_value="answer"),
        patch.object(settings, "verification_enabled", False),
    ):
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.clear()


_PAYLOAD = {
    "conversation_id": None,
    "question": "How to correct soil acidity?",
}


def test_exceeding_the_limit_returns_429(chat_client: TestClient, low_chat_limit: None) -> None:
    """The (limit + 1)-th request from one user within the window returns 429."""
    headers = _bearer("heavy-user")

    # Mock dynamic verify_token to return the user that matches the JWT sub to keep DB integrity
    heavy_user_model = User(id=2, username="heavy-user", hashed_password="x", created_at=datetime.now(UTC))
    app.dependency_overrides[verify_token] = lambda: heavy_user_model

    for _ in range(3):
        allowed = chat_client.post("/chat", json=_PAYLOAD, headers=headers)
        assert allowed.status_code == 200

    blocked = chat_client.post("/chat", json=_PAYLOAD, headers=headers)
    assert blocked.status_code == 429


def test_limit_is_per_user_not_per_ip(chat_client: TestClient, low_chat_limit: None) -> None:
    """One user exhausting the budget does not throttle another (same client IP)."""
    user_a_model = User(id=3, username="user-a", hashed_password="x", created_at=datetime.now(UTC))
    user_b_model = User(id=4, username="user-b", hashed_password="x", created_at=datetime.now(UTC))

    app.dependency_overrides[verify_token] = lambda: user_a_model
    for _ in range(3):
        assert (
            chat_client.post("/chat", json=_PAYLOAD, headers=_bearer("user-a")).status_code == 200
        )
    assert chat_client.post("/chat", json=_PAYLOAD, headers=_bearer("user-a")).status_code == 429

    # A different identity from the same TestClient host keeps a full budget
    app.dependency_overrides[verify_token] = lambda: user_b_model
    assert chat_client.post("/chat", json=_PAYLOAD, headers=_bearer("user-b")).status_code == 200
