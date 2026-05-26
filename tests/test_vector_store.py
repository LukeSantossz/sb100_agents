"""Testes do retrieval/vector_store (TASK-T66 — singleton + dim validation + warnings)."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from core.config import settings
from retrieval import vector_store as vs_module
from retrieval.vector_store import search_context


@pytest.fixture(autouse=True)
def _reset_singleton() -> Generator[None, None, None]:
    """Reseta o singleton entre testes para isolar mocks de ``QdrantClient``."""
    vs_module._qdrant_client = None
    yield
    vs_module._qdrant_client = None


def _make_point(text: str | None = "chunk") -> MagicMock:
    point = MagicMock()
    point.payload = {"text": text} if text is not None else {}
    return point


def test_search_returns_text_list_with_top_k_chunks() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        points = [_make_point(f"chunk-{i}") for i in range(settings.top_k)]
        mock_client.query_points.return_value = MagicMock(points=points)

        out = search_context([0.1] * 768)

        assert out == [f"chunk-{i}" for i in range(settings.top_k)]
        mock_client.query_points.assert_called_once_with(
            collection_name=settings.collection_name,
            query=[0.1] * 768,
            limit=settings.top_k,
            with_payload=True,
        )


def test_search_rejects_wrong_dim() -> None:
    with pytest.raises(ValueError, match="must have 768 dimensions"):
        search_context([0.1] * 10)


def test_search_rejects_empty_embedding() -> None:
    with pytest.raises(ValueError, match="must have 768 dimensions"):
        search_context([])


def test_missing_text_logs_warning_and_returns_empty_string(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        patch("retrieval.vector_store.QdrantClient") as mock_cls,
        caplog.at_level("WARNING", logger="retrieval.vector_store"),
    ):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.query_points.return_value = MagicMock(points=[_make_point(None)])

        out = search_context([0.1] * 768)

    assert out == [""]
    assert any("empty_or_missing_text" in record.message for record in caplog.records)


def test_singleton_reuses_client_across_calls() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.query_points.return_value = MagicMock(points=[])

        for _ in range(5):
            search_context([0.1] * 768)

        # Apenas 1 instanciação apesar de 5 chamadas
        mock_cls.assert_called_once_with(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
