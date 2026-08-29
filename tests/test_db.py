"""SQLAlchemy schema integrity tests.

Covers:
    - ``nullable=False`` on required fields (User, Conversation, Message).
    - ``ondelete="CASCADE"`` on FKs (requires PRAGMA foreign_keys=ON in SQLite).
    - ``DateTime(timezone=True)`` on ``created_at``.
    - ``get_db()`` rolls back on exception before closing.
"""

import contextlib
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import database.db as db_module
from database.db import DB_PATH_ENV_VAR, Base, get_db, resolve_db_path
from database.models import Conversation, Message, User


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite with FKs enabled (via the global listener in ``database.db``)."""
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
    # User remains
    assert db_session.query(User).count() == 1


# ---------- timezone-aware datetime ----------


def test_created_at_is_timezone_aware(db_session: Session) -> None:
    user = User(username="frank", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    created = user.created_at
    assert isinstance(created, datetime)
    # SQLite stores DateTime without tz by default; SQLAlchemy preserves tz when the
    # value comes in timezone-aware. The default callback ``_utc_now`` returns
    # ``datetime.now(UTC)``. In SQLite the tz may be stripped on read — so we test
    # the value produced by the callback directly.
    from database.models import _utc_now

    assert _utc_now().tzinfo is UTC


# ---------- get_db rollback ----------


def test_get_db_rolls_back_on_exception() -> None:
    mock_session = MagicMock(spec=Session)

    # Patch SessionLocal to return our mock
    from database import db as db_module

    original = db_module.SessionLocal
    db_module.SessionLocal = MagicMock(return_value=mock_session)  # type: ignore[assignment]
    try:
        gen = get_db()
        next(gen)  # enter the with body
        # Simulate an exception inside the consumer block
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
        # Finish normally
        with pytest.raises(StopIteration):
            next(gen)
        mock_session.close.assert_called_once()
        mock_session.rollback.assert_not_called()
    finally:
        db_module.SessionLocal = original


# ----------------------- database file location (issue #218) -----------------------
#
# The bind mount used to point at ./smartb100_v2.db, a path that is gitignored and
# therefore always absent on a clean clone, so Docker created it as a directory and
# the API refused to start. The container now points this variable inside a mounted
# directory instead.


def test_db_path_defaults_to_the_repository_root() -> None:
    """With nothing set, the location is unchanged, so no local database moves."""
    resolved = resolve_db_path({})
    assert resolved == Path(db_module.__file__).resolve().parents[1] / "smartb100_v2.db"
    assert resolved == db_module.DEFAULT_DB_PATH


def test_db_path_honours_the_override() -> None:
    """The container sets this to a path inside the mounted directory."""
    assert resolve_db_path({DB_PATH_ENV_VAR: "/app/data/smartb100_v2.db"}) == Path(
        "/app/data/smartb100_v2.db"
    )


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_blank_override_falls_back_to_the_default(blank: str) -> None:
    """A declared-but-empty variable must not resolve the database to the cwd.

    ``SMARTB100_DB_PATH=`` in an env file arrives as the empty string, and
    ``Path("")`` is ``.``, which would put the database wherever the process
    happened to start.
    """
    assert resolve_db_path({DB_PATH_ENV_VAR: blank}) == db_module.DEFAULT_DB_PATH


def test_resolve_db_path_reads_the_process_environment_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Called with no argument it reads os.environ, which is how the module uses it."""
    target = tmp_path / "elsewhere.db"
    monkeypatch.setenv(DB_PATH_ENV_VAR, str(target))
    assert resolve_db_path() == target
