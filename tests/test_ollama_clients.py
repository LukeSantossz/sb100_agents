"""Tests for core.ollama_clients.

Covers thread-safe singletons, Settings timeout propagation and reset.
"""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from core import ollama_clients
from core.config import settings


@pytest.fixture(autouse=True)
def _reset_singletons() -> Generator[None, None, None]:
    """Ensure a clean state before and after each test."""
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
        mock_cls.assert_called_once_with(host=settings.ollama_host, timeout=settings.ollama_timeout)


def test_get_embed_client_returns_singleton() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        sentinel = object()
        mock_cls.return_value = sentinel

        first = ollama_clients.get_embed_client()
        second = ollama_clients.get_embed_client()

        assert first is sentinel
        assert first is second
        mock_cls.assert_called_once_with(host=settings.ollama_host, timeout=settings.ollama_embed_timeout)


def test_chat_client_uses_settings_ollama_timeout() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        mock_cls.return_value = object()
        ollama_clients.get_chat_client()

        _, kwargs = mock_cls.call_args
        assert kwargs["timeout"] == settings.ollama_timeout
        assert kwargs["host"] == settings.ollama_host


def test_embed_client_uses_settings_ollama_embed_timeout() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        mock_cls.return_value = object()
        ollama_clients.get_embed_client()

        _, kwargs = mock_cls.call_args
        assert kwargs["timeout"] == settings.ollama_embed_timeout
        assert kwargs["host"] == settings.ollama_host


def test_reset_clients_forces_reinstantiation() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        mock_cls.return_value = object()

        ollama_clients.get_chat_client()
        ollama_clients.get_embed_client()
        # 2 calls (chat + embed) already made
        assert mock_cls.call_count == 2

        ollama_clients.reset_clients()

        ollama_clients.get_chat_client()
        # After reset, chat was instantiated again → +1
        assert mock_cls.call_count == 3


def test_chat_and_embed_clients_are_independent() -> None:
    with patch("core.ollama_clients.OllamaClient") as mock_cls:
        # Each call to the class returns a different object
        instances = [object(), object()]
        mock_cls.side_effect = instances

        chat_inst = ollama_clients.get_chat_client()
        embed_inst = ollama_clients.get_embed_client()

        assert chat_inst is not embed_inst
        # Distinct calls for chat and embed, each with its own timeout and host
        assert mock_cls.call_count == 2
        chat_call_kwargs = mock_cls.call_args_list[0].kwargs
        embed_call_kwargs = mock_cls.call_args_list[1].kwargs
        assert chat_call_kwargs["timeout"] == settings.ollama_timeout
        assert chat_call_kwargs["host"] == settings.ollama_host
        assert embed_call_kwargs["timeout"] == settings.ollama_embed_timeout
        assert embed_call_kwargs["host"] == settings.ollama_host
