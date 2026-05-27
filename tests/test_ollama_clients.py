"""Testes do core.ollama_clients (TASK-T76).

Cobre singletons thread-safe, propagação de timeout das Settings e reset.
"""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from core import ollama_clients
from core.config import settings


@pytest.fixture(autouse=True)
def _reset_singletons() -> Generator[None, None, None]:
    """Garante estado limpo antes e depois de cada teste."""
    ollama_clients.reset_clients()
    yield
    ollama_clients.reset_clients()


def test_get_chat_client_returns_singleton() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        sentinel = object()
        mock_cls.return_value = sentinel

        first = ollama_clients.get_chat_client()
        second = ollama_clients.get_chat_client()

        assert first is sentinel
        assert first is second
        mock_cls.assert_called_once_with(timeout=settings.ollama_timeout)


def test_get_embed_client_returns_singleton() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        sentinel = object()
        mock_cls.return_value = sentinel

        first = ollama_clients.get_embed_client()
        second = ollama_clients.get_embed_client()

        assert first is sentinel
        assert first is second
        mock_cls.assert_called_once_with(timeout=settings.ollama_embed_timeout)


def test_chat_client_uses_settings_ollama_timeout() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        mock_cls.return_value = object()
        ollama_clients.get_chat_client()

        _, kwargs = mock_cls.call_args
        assert kwargs["timeout"] == settings.ollama_timeout


def test_embed_client_uses_settings_ollama_embed_timeout() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        mock_cls.return_value = object()
        ollama_clients.get_embed_client()

        _, kwargs = mock_cls.call_args
        assert kwargs["timeout"] == settings.ollama_embed_timeout


def test_reset_clients_forces_reinstantiation() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        mock_cls.return_value = object()

        ollama_clients.get_chat_client()
        ollama_clients.get_embed_client()
        # 2 chamadas (chat + embed) já feitas
        assert mock_cls.call_count == 2

        ollama_clients.reset_clients()

        ollama_clients.get_chat_client()
        # Após reset, chat foi instanciado novamente → +1
        assert mock_cls.call_count == 3


def test_chat_and_embed_clients_are_independent() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        # Cada chamada à classe retorna um objeto diferente
        instances = [object(), object()]
        mock_cls.side_effect = instances

        chat_inst = ollama_clients.get_chat_client()
        embed_inst = ollama_clients.get_embed_client()

        assert chat_inst is not embed_inst
        # Chamadas distintas para chat e embed, cada uma com seu timeout
        assert mock_cls.call_count == 2
        chat_call_kwargs = mock_cls.call_args_list[0].kwargs
        embed_call_kwargs = mock_cls.call_args_list[1].kwargs
        assert chat_call_kwargs["timeout"] == settings.ollama_timeout
        assert embed_call_kwargs["timeout"] == settings.ollama_embed_timeout
