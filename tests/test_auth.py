"""Testes da pipeline de autenticação (TASK-T60).

Cobre:
    - Hashing bcrypt (formato, salt aleatório, verify timing-safe).
    - Validação de :class:`UserCreate` (regex, comprimentos).
    - Endpoints ``/auth/register`` e ``/auth/token``.
    - Gate JWT no endpoint ``/chat`` (ausente, inválido, expirado, usuário inexistente).
    - Rate-limit do slowapi em registro e login.
"""

from collections.abc import Generator
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import ALGORITHM, limiter
from api.main import app
from api.routes.auth import (
    UserCreate,
    create_access_token,
    get_password_hash,
    verify_password,
)
from core.config import settings
from database.db import Base, get_db
from database.models import User

# ----------------------------- fixtures -----------------------------


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Banco SQLite in-memory isolado por teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # SQLite :memory: precisa de pool único por engine
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient com ``get_db`` redirecionado para o session in-memory."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> Generator[None, None, None]:
    """Garante que o storage do slowapi começa limpo a cada teste."""
    limiter.reset()
    yield
    limiter.reset()


# ----------------------------- hashing -----------------------------


def test_get_password_hash_uses_bcrypt_prefix() -> None:
    hashed = get_password_hash("my-password-123")
    assert hashed.startswith("$2")
    assert hashed != "my-password-123"


def test_get_password_hash_generates_distinct_salts() -> None:
    first = get_password_hash("same-password")
    second = get_password_hash("same-password")
    assert first != second


def test_verify_password_accepts_correct_password() -> None:
    hashed = get_password_hash("correct-password")
    assert verify_password("correct-password", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = get_password_hash("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_handles_corrupted_hash() -> None:
    assert verify_password("any-password", "not-a-valid-hash") is False


# ----------------------------- JWT -----------------------------


def test_create_access_token_encodes_sub_and_exp() -> None:
    token = create_access_token({"sub": "alice"}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] == "alice"
    assert "exp" in payload


# ----------------------------- UserCreate -----------------------------


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="alice", password="short")


def test_user_create_rejects_username_with_special_chars() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="alice@example", password="long-enough-pw")


def test_user_create_rejects_username_over_max_length() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="a" * 51, password="long-enough-pw")


def test_user_create_accepts_valid_payload() -> None:
    user = UserCreate(username="alice_99-prod", password="strong-pw-12")
    assert user.username == "alice_99-prod"
    assert user.password == "strong-pw-12"


# ----------------------------- /auth/register -----------------------------


def test_register_creates_user_with_bcrypt_hash(client: TestClient, db_session: Session) -> None:
    resp = client.post(
        "/auth/register",
        json={"username": "alice", "password": "long-enough-pw"},
    )
    assert resp.status_code == 201
    stored = db_session.query(User).filter(User.username == "alice").first()
    assert stored is not None
    assert str(stored.hashed_password).startswith("$2")


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    payload = {"username": "bob", "password": "long-enough-pw"}
    assert client.post("/auth/register", json=payload).status_code == 201
    resp = client.post(
        "/auth/register",
        json={"username": "bob", "password": "different-pw-12"},
    )
    assert resp.status_code == 400


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post(
        "/auth/register",
        json={"username": "carol", "password": "short"},
    )
    assert resp.status_code == 422


def test_register_rejects_invalid_username(client: TestClient) -> None:
    resp = client.post(
        "/auth/register",
        json={"username": "carol@x", "password": "long-enough-pw"},
    )
    assert resp.status_code == 422


# ----------------------------- /auth/token -----------------------------


def test_login_returns_jwt_for_valid_credentials(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"username": "dave", "password": "long-enough-pw"},
    )
    resp = client.post(
        "/auth/token",
        data={"username": "dave", "password": "long-enough-pw"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    payload = jwt.decode(body["access_token"], settings.jwt_secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] == "dave"


def test_login_rejects_invalid_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"username": "eve", "password": "long-enough-pw"},
    )
    resp = client.post(
        "/auth/token",
        data={"username": "eve", "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_rejects_unknown_user(client: TestClient) -> None:
    resp = client.post(
        "/auth/token",
        data={"username": "ghost", "password": "long-enough-pw"},
    )
    assert resp.status_code == 401


# ----------------------------- /chat gate -----------------------------


def _chat_payload(session_id: str) -> dict[str, object]:
    return {
        "session_id": session_id,
        "question": "ping",
        "profile": {"name": "tester", "expertise": "beginner"},
    }


def test_chat_requires_authorization_header(client: TestClient) -> None:
    resp = client.post("/chat", json=_chat_payload("s1"))
    assert resp.status_code == 401


def test_chat_rejects_invalid_token(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        json=_chat_payload("s2"),
        headers={"Authorization": "Bearer invalid-token-xyz"},
    )
    assert resp.status_code == 401


def test_chat_rejects_expired_token(client: TestClient) -> None:
    expired = create_access_token({"sub": "alice"}, expires_delta=timedelta(minutes=-1))
    resp = client.post(
        "/chat",
        json=_chat_payload("s3"),
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert resp.status_code == 401


def test_chat_rejects_token_for_missing_user(client: TestClient) -> None:
    token = create_access_token({"sub": "nonexistent"}, expires_delta=timedelta(minutes=5))
    resp = client.post(
        "/chat",
        json=_chat_payload("s4"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


# ----------------------------- rate-limit -----------------------------


def test_rate_limit_register_blocks_after_threshold(client: TestClient) -> None:
    """3 registros/hora; o 4º deve receber 429."""
    for index in range(3):
        resp = client.post(
            "/auth/register",
            json={"username": f"rl_user_{index}", "password": "long-enough-pw"},
        )
        assert resp.status_code == 201
    resp = client.post(
        "/auth/register",
        json={"username": "rl_overflow", "password": "long-enough-pw"},
    )
    assert resp.status_code == 429


def test_rate_limit_token_blocks_after_threshold(client: TestClient) -> None:
    """5 tentativas/15min; a 6ª deve receber 429."""
    client.post(
        "/auth/register",
        json={"username": "rl_login", "password": "long-enough-pw"},
    )
    for _ in range(5):
        client.post(
            "/auth/token",
            data={"username": "rl_login", "password": "long-enough-pw"},
        )
    resp = client.post(
        "/auth/token",
        data={"username": "rl_login", "password": "long-enough-pw"},
    )
    assert resp.status_code == 429
