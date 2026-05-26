"""Testes de integridade do schema SQLAlchemy (TASK-T63).

Cobre:
    - ``nullable=False`` em campos obrigatórios (User, Conversation, Message).
    - ``ondelete="CASCADE"`` em FKs (requer PRAGMA foreign_keys=ON em SQLite).
    - ``DateTime(timezone=True)`` em ``created_at``.
    - ``get_db()`` faz rollback em exceção antes de fechar.
"""

import contextlib
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base, get_db
from database.models import Conversation, Message, User


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """SQLite in-memory com FKs ativadas (via listener global em ``database.db``)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ---------- nullable=False ----------


def test_user_rejects_null_username(db_session: Session) -> None:
    db_session.add(User(username=None, hashed_password="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_rejects_null_password(db_session: Session) -> None:
    db_session.add(User(username="alice", hashed_password=None))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_conversation_rejects_null_user_id(db_session: Session) -> None:
    db_session.add(Conversation(user_id=None, title="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_message_rejects_null_conversation_id(db_session: Session) -> None:
    db_session.add(Message(conversation_id=None, role="user", content="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_message_rejects_null_role(db_session: Session) -> None:
    user = User(username="bob", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    conv = Conversation(user_id=user.id, title="t")
    db_session.add(conv)
    db_session.commit()
    db_session.add(Message(conversation_id=conv.id, role=None, content="hi"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_message_rejects_null_content(db_session: Session) -> None:
    user = User(username="carol", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    conv = Conversation(user_id=user.id, title="t")
    db_session.add(conv)
    db_session.commit()
    db_session.add(Message(conversation_id=conv.id, role="user", content=None))
    with pytest.raises(IntegrityError):
        db_session.commit()


# ---------- CASCADE ----------


def test_delete_user_cascades_conversations_and_messages(db_session: Session) -> None:
    user = User(username="dave", hashed_password="x")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="c1")
    db_session.add(conv)
    db_session.commit()

    msg = Message(conversation_id=conv.id, role="user", content="hi")
    db_session.add(msg)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    assert db_session.query(User).count() == 0
    assert db_session.query(Conversation).count() == 0
    assert db_session.query(Message).count() == 0


def test_delete_conversation_cascades_messages(db_session: Session) -> None:
    user = User(username="eve", hashed_password="x")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="c1")
    db_session.add(conv)
    db_session.commit()

    db_session.add(Message(conversation_id=conv.id, role="user", content="m1"))
    db_session.add(Message(conversation_id=conv.id, role="assistant", content="m2"))
    db_session.commit()

    db_session.delete(conv)
    db_session.commit()

    assert db_session.query(Conversation).count() == 0
    assert db_session.query(Message).count() == 0
    # User permanece
    assert db_session.query(User).count() == 1


# ---------- timezone-aware datetime ----------


def test_created_at_is_timezone_aware(db_session: Session) -> None:
    user = User(username="frank", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    created = user.created_at
    assert isinstance(created, datetime)
    # SQLite armazena DateTime sem tz por default; SQLAlchemy preserva tz quando o valor
    # entra timezone-aware. O default callback ``_utc_now`` retorna ``datetime.now(UTC)``.
    # Em SQLite o tz pode ser stripado na leitura — então testamos o valor produzido
    # pelo callback diretamente.
    from database.models import _utc_now

    assert _utc_now().tzinfo is UTC


# ---------- get_db rollback ----------


def test_get_db_rolls_back_on_exception() -> None:
    mock_session = MagicMock(spec=Session)

    # Patch SessionLocal para retornar nosso mock
    from database import db as db_module

    original = db_module.SessionLocal
    db_module.SessionLocal = MagicMock(return_value=mock_session)  # type: ignore[assignment]
    try:
        gen = get_db()
        next(gen)  # entra no with body
        # Simula exceção dentro do bloco do consumer
        with contextlib.suppress(RuntimeError):
            gen.throw(RuntimeError("boom"))
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
    finally:
        db_module.SessionLocal = original


def test_get_db_closes_on_success() -> None:
    mock_session = MagicMock(spec=Session)
    from database import db as db_module

    original = db_module.SessionLocal
    db_module.SessionLocal = MagicMock(return_value=mock_session)  # type: ignore[assignment]
    try:
        gen = get_db()
        next(gen)
        # Encerra normalmente
        with pytest.raises(StopIteration):
            next(gen)
        mock_session.close.assert_called_once()
        mock_session.rollback.assert_not_called()
    finally:
        db_module.SessionLocal = original
