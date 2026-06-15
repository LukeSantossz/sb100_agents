"""Concurrency and per-user isolation tests for the /chat `_sessions` cache."""

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from api.routes.chat import _get_or_create_buffer, _sessions
from database.models import User
from memory.conversation import ConversationBuffer


def _user(user_id: int) -> User:
    """Build a minimal User with the given primary key for cache-key tests."""
    return User(
        id=user_id,
        username=f"user{user_id}",
        hashed_password="x",
        created_at=datetime.now(UTC),
    )


_USER_A = _user(1)
_USER_B = _user(2)


@pytest.fixture(autouse=True)
def _clear_sessions() -> Generator[None, None, None]:
    """Ensure the cache is empty before and after each test."""
    _sessions.clear()
    yield
    _sessions.clear()


def test_concurrent_get_or_create_returns_single_buffer_for_same_session_id() -> None:
    """50 threads with the same user + session_id resolve to a single shared buffer."""
    session_id = "shared-session"

    with ThreadPoolExecutor(max_workers=50) as executor:
        buffers: list[ConversationBuffer] = list(
            executor.map(lambda _: _get_or_create_buffer(_USER_A, session_id), range(50))
        )

    assert len(_sessions) == 1
    first = buffers[0]
    assert all(b is first for b in buffers)


def test_concurrent_distinct_session_ids_create_distinct_buffers() -> None:
    """50 distinct session_ids (same user) result in 50 separate entries."""
    session_ids = [f"sess-{i}" for i in range(50)]

    with ThreadPoolExecutor(max_workers=50) as executor:
        buffers = list(executor.map(lambda sid: _get_or_create_buffer(_USER_A, sid), session_ids))

    assert len(_sessions) == 50
    assert len({id(b) for b in buffers}) == 50


def test_same_user_same_session_id_reuses_buffer() -> None:
    """Sequential calls with the same user + session_id return the same object."""
    a = _get_or_create_buffer(_USER_A, "repeat-session")
    b = _get_or_create_buffer(_USER_A, "repeat-session")
    assert a is b


def test_same_session_id_different_users_get_independent_buffers() -> None:
    """Two users with the same session_id resolve to different buffers (#108)."""
    buf_a = _get_or_create_buffer(_USER_A, "shared")
    buf_b = _get_or_create_buffer(_USER_B, "shared")

    assert buf_a is not buf_b
    assert len(_sessions) == 2


def test_cache_key_includes_authenticated_identity() -> None:
    """The _sessions key carries current_user.id, never the bare session_id (#108)."""
    _get_or_create_buffer(_USER_A, "sess")

    assert f"{_USER_A.id}:sess" in _sessions
    assert "sess" not in _sessions


def test_cross_user_access_does_not_leak_history() -> None:
    """A user reusing another's session_id sees no history and cannot poison it (#108)."""
    victim = _get_or_create_buffer(_USER_A, "shared")
    victim.add("user", "victim secret")
    victim.add("assistant", "victim answer")

    attacker = _get_or_create_buffer(_USER_B, "shared")

    assert attacker is not victim
    assert attacker.to_messages() == []  # victim history must not leak

    attacker.add("user", "injected")
    assert all("injected" not in message["content"] for message in victim.to_messages())
