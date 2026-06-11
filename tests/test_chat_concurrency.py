"""Concurrency tests for the /chat route `_sessions` cache."""

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor

import pytest

from api.routes.chat import _get_or_create_buffer, _sessions
from memory.conversation import ConversationBuffer


@pytest.fixture(autouse=True)
def _clear_sessions() -> Generator[None, None, None]:
    """Ensure the cache is empty before and after each test."""
    _sessions.clear()
    yield
    _sessions.clear()


def test_concurrent_get_or_create_returns_single_buffer_for_same_session_id() -> None:
    """50 threads calling the same session_id result in a single shared buffer."""
    session_id = "shared-session"

    with ThreadPoolExecutor(max_workers=50) as executor:
        buffers: list[ConversationBuffer] = list(
            executor.map(lambda _: _get_or_create_buffer(session_id), range(50))
        )

    # Only one entry in _sessions for this session_id
    assert session_id in _sessions
    assert len(_sessions) == 1

    # All 50 returns must be exactly the same object
    first = buffers[0]
    assert all(b is first for b in buffers)


def test_concurrent_distinct_session_ids_create_distinct_buffers() -> None:
    """50 distinct session_ids result in 50 separate entries."""
    session_ids = [f"sess-{i}" for i in range(50)]

    with ThreadPoolExecutor(max_workers=50) as executor:
        buffers = list(executor.map(_get_or_create_buffer, session_ids))

    assert len(_sessions) == 50
    # Unique buffers
    assert len({id(b) for b in buffers}) == 50


def test_repeated_call_returns_same_buffer_instance() -> None:
    """Sequential calls with the same session_id return the same object."""
    session_id = "repeat-session"
    a = _get_or_create_buffer(session_id)
    b = _get_or_create_buffer(session_id)
    assert a is b
