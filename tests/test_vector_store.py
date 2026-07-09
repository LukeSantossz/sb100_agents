"""Tests for retrieval/vector_store (singleton + dim validation + warnings).

Mocks use a real ``ScoredPoint`` from ``qdrant_client.models`` instead of a
generic ``MagicMock`` — so contract changes in the SDK are caught by the tests.
"""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.models import ScoredPoint

from core.config import settings
from retrieval import vector_store as vs_module
from retrieval.vector_store import search_context, search_context_rich, top_similarity


@pytest.fixture(autouse=True)
def _reset_singleton() -> Generator[None, None, None]:
    """Resets the singleton between tests to isolate ``QdrantClient`` mocks."""
    vs_module._qdrant_client = None
    yield
    vs_module._qdrant_client = None


def _make_point(text: str | None = "chunk", *, id_: int = 1, score: float = 0.9) -> ScoredPoint:
    """Builds a real ``ScoredPoint`` for use in mocks."""
    payload: dict[str, str] = {} if text is None else {"text": text}
    return ScoredPoint(id=id_, version=0, score=score, payload=payload)


def test_search_returns_text_list_with_top_k_chunks() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        points = [_make_point(f"chunk-{i}", id_=i) for i in range(settings.top_k)]
        mock_client.query_points.return_value = MagicMock(points=points)

        out = search_context([0.1] * settings.embed_dim)

        assert out == [f"chunk-{i}" for i in range(settings.top_k)]
        mock_client.query_points.assert_called_once_with(
            collection_name=settings.collection_name,
            query=[0.1] * settings.embed_dim,
            using=settings.qdrant_vector_name,
            limit=settings.top_k,
            with_payload=True,
        )


def test_search_rejects_wrong_dim() -> None:
    with pytest.raises(ValueError, match=f"must have {settings.embed_dim} dimensions"):
        search_context([0.1] * 10)


def test_search_rejects_empty_embedding() -> None:
    with pytest.raises(ValueError, match=f"must have {settings.embed_dim} dimensions"):
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

        out = search_context([0.1] * settings.embed_dim)

    assert out == [""]
    assert any("empty_or_missing_text" in record.message for record in caplog.records)


def test_top_similarity_returns_top_point_score() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.query_points.return_value = MagicMock(points=[_make_point("chunk", score=0.83)])

        out = top_similarity([0.1] * settings.embed_dim)

        assert out == 0.83
        mock_client.query_points.assert_called_once_with(
            collection_name=settings.collection_name,
            query=[0.1] * settings.embed_dim,
            using=settings.qdrant_vector_name,
            limit=1,
        )


def test_top_similarity_returns_none_when_no_points() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.query_points.return_value = MagicMock(points=[])

        assert top_similarity([0.1] * settings.embed_dim) is None
        mock_client.query_points.assert_called_once_with(
            collection_name=settings.collection_name,
            query=[0.1] * settings.embed_dim,
            using=settings.qdrant_vector_name,
            limit=1,
        )


def test_top_similarity_rejects_wrong_dim() -> None:
    with pytest.raises(ValueError, match=f"must have {settings.embed_dim} dimensions"):
        top_similarity([0.1] * 10)


def test_singleton_reuses_client_across_calls() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.query_points.return_value = MagicMock(points=[])

        for _ in range(5):
            search_context([0.1] * settings.embed_dim)

        # Only 1 instantiation despite 5 calls
        mock_cls.assert_called_once_with(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def test_search_rich_returns_detailed_metadata() -> None:
    with patch("retrieval.vector_store.QdrantClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        
        point = ScoredPoint(
            id="000d0064-f08d-4197-bca3-698a3df364d9",
            version=0,
            score=0.88,
            payload={
                "content": "teste rico",
                "chunk_index": 12,
                "file": "doc.pdf",
                "pagina_pdf": 3
            }
        )
        mock_client.query_points.return_value = MagicMock(points=[point])

        out = search_context_rich([0.1] * settings.embed_dim)

        assert len(out) == 1
        assert out[0]["id"] == "000d0064-f08d-4197-bca3-698a3df364d9"
        assert out[0]["inicio"] == 12
        assert out[0]["text"] == "teste rico"
        assert out[0]["file"] == "doc.pdf"
        assert out[0]["pagina"] == 3
        assert out[0]["score"] == 0.88


def test_search_rich_rejects_wrong_dim() -> None:
    with pytest.raises(ValueError, match=f"must have {settings.embed_dim} dimensions"):
        search_context_rich([0.1] * 10)
