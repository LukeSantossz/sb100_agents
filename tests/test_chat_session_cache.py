"""Eviction and recency behaviour of the per-session conversation cache (issue #97).

`tests/test_chat_concurrency.py` covers concurrent get-or-create. The eviction
path was uncovered, and it was wrong: the size limit was enforced *before* the
lookup, so at capacity a request for an existing session evicted an entry for no
reason, and a request for the least recently used session evicted that session
and handed the caller back an empty buffer. The user lost the conversation they
were in the middle of.

`_SESSION_MAX_SIZE` is monkeypatched small here so capacity is reachable without
building a thousand sessions.
"""

from __future__ import annotations

import pytest

from api.routes import chat as chat_module
from memory.conversation import ConversationBuffer


class _User:
    """Minimal stand-in for the authenticated user; only ``id`` is read."""

    def __init__(self, user_id: int) -> None:
        self.id = user_id


@pytest.fixture(autouse=True)
def _clear_sessions():
    """Each test starts from an empty cache and leaves one behind."""
    chat_module._sessions.clear()
    yield
    chat_module._sessions.clear()


def _fill(user: _User, session_ids: list[str]) -> None:
    for session_id in session_ids:
        chat_module._get_or_create_buffer(user, session_id)


def test_a_hit_at_capacity_evicts_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cache hit must not cost another session its place.

    Nothing is being inserted, so there is nothing to make room for.
    """
    monkeypatch.setattr(chat_module, "_SESSION_MAX_SIZE", 3)
    user = _User(1)
    _fill(user, ["a", "b", "c"])
    assert len(chat_module._sessions) == 3

    chat_module._get_or_create_buffer(user, "c")

    assert len(chat_module._sessions) == 3
    assert set(chat_module._sessions) == {"1:a", "1:b", "1:c"}


def test_the_caller_is_never_evicted_by_its_own_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """The defect this file exists for: asking for your own session lost it.

    With the cache full and ``a`` the least recently used, the old order evicted
    ``a`` and then created it again, empty, so the caller's own history vanished
    on a request that should have returned it.
    """
    monkeypatch.setattr(chat_module, "_SESSION_MAX_SIZE", 2)
    user = _User(1)
    first = chat_module._get_or_create_buffer(user, "a")
    first.add("user", "qual a epoca de plantio da soja?")
    first.add("assistant", "depende do regime de chuvas")
    chat_module._get_or_create_buffer(user, "b")  # "a" is now the LRU entry

    again = chat_module._get_or_create_buffer(user, "a")

    assert again is first, "the caller got a different buffer than the one it had"
    assert [message["content"] for message in again.to_messages()] == [
        "qual a epoca de plantio da soja?",
        "depende do regime de chuvas",
    ]


def test_a_miss_at_capacity_stays_within_the_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inserting at capacity must still evict, and evict the oldest."""
    monkeypatch.setattr(chat_module, "_SESSION_MAX_SIZE", 3)
    user = _User(1)
    _fill(user, ["a", "b", "c"])

    chat_module._get_or_create_buffer(user, "d")

    assert len(chat_module._sessions) == 3
    assert "1:a" not in chat_module._sessions, "the oldest entry survived"
    assert set(chat_module._sessions) == {"1:b", "1:c", "1:d"}


def test_a_hit_refreshes_recency(monkeypatch: pytest.MonkeyPatch) -> None:
    """A used session must stop being the eviction candidate.

    Without this the cache would be first-in-first-out wearing an LRU's name.
    """
    monkeypatch.setattr(chat_module, "_SESSION_MAX_SIZE", 3)
    user = _User(1)
    _fill(user, ["a", "b", "c"])

    chat_module._get_or_create_buffer(user, "a")  # "a" becomes the most recent
    chat_module._get_or_create_buffer(user, "d")  # forces one eviction

    assert "1:a" in chat_module._sessions, "the just-used session was evicted"
    assert "1:b" not in chat_module._sessions, "the actual LRU entry survived"


def test_sessions_stay_namespaced_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two users sharing a session_id must not share a buffer (#108).

    Asserted here because this file is where the cache key is exercised, and the
    reordering must not weaken it.
    """
    monkeypatch.setattr(chat_module, "_SESSION_MAX_SIZE", 10)
    first = chat_module._get_or_create_buffer(_User(1), "shared")
    second = chat_module._get_or_create_buffer(_User(2), "shared")

    assert first is not second
    assert set(chat_module._sessions) == {"1:shared", "2:shared"}


def test_the_returned_object_is_a_conversation_buffer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guards the constructor call the reordering moves past."""
    monkeypatch.setattr(chat_module, "_SESSION_MAX_SIZE", 3)
    assert isinstance(chat_module._get_or_create_buffer(_User(1), "a"), ConversationBuffer)
