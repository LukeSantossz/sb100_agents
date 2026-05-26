"""Testes de concorrência para o cache `_sessions` da rota /chat (TASK-T65)."""

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor

import pytest

from api.routes.chat import _get_or_create_buffer, _sessions
from memory.conversation import ConversationBuffer


@pytest.fixture(autouse=True)
def _clear_sessions() -> Generator[None, None, None]:
    """Garante cache vazio antes e depois de cada teste."""
    _sessions.clear()
    yield
    _sessions.clear()


def test_concurrent_get_or_create_returns_single_buffer_for_same_session_id() -> None:
    """50 threads chamando o mesmo session_id resultam em 1 único buffer compartilhado."""
    session_id = "shared-session"

    with ThreadPoolExecutor(max_workers=50) as executor:
        buffers: list[ConversationBuffer] = list(
            executor.map(lambda _: _get_or_create_buffer(session_id), range(50))
        )

    # Apenas uma entrada em _sessions para esse session_id
    assert session_id in _sessions
    assert len(_sessions) == 1

    # Todos os 50 retornos devem ser exatamente o mesmo objeto
    first = buffers[0]
    assert all(b is first for b in buffers)


def test_concurrent_distinct_session_ids_create_distinct_buffers() -> None:
    """50 session_ids distintos resultam em 50 entradas separadas."""
    session_ids = [f"sess-{i}" for i in range(50)]

    with ThreadPoolExecutor(max_workers=50) as executor:
        buffers = list(executor.map(_get_or_create_buffer, session_ids))

    assert len(_sessions) == 50
    # Buffers únicos
    assert len({id(b) for b in buffers}) == 50


def test_repeated_call_returns_same_buffer_instance() -> None:
    """Chamadas sequenciais com o mesmo session_id retornam o mesmo objeto."""
    session_id = "repeat-session"
    a = _get_or_create_buffer(session_id)
    b = _get_or_create_buffer(session_id)
    assert a is b
