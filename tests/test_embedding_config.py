"""The embedding configuration must be one source of truth, and inside the model's limits.

Two defects, one theme: a number or a name that describes the embedding model
lives in a second place, and the second place is wrong.

- #105: the indexer embedded with a hardcoded ``nomic-embed-text`` while every
  query path embedded with ``settings.embed_model``. Setting ``EMBED_MODEL`` moved
  the query and not the corpus, so the two ended up in different vector spaces and
  retrieval degraded with nothing in the logs to say why.
- #225: the truncation guard was set above the context the model actually accepts,
  so the call it exists to protect still failed with
  ``the input length exceeds the context length``.

Nothing here reaches Ollama or Qdrant: the model name is resolved before any call,
and the truncation is measured on the argument ``embed_text`` passes down.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import database.semantic_chunker as chunker
from core.config import settings
from retrieval.embedder import generate_embedding
from retrieval.ollama_embeddings import _MAX_EMBED_CHARS, embed_text

# The smallest ceiling found by a binary search over the longest chunks in the
# shipped collection: nomic-embed-text refused that sample past 6203 characters. The
# model's context is 2048 tokens, and how many characters fit depends on the
# tokenizer and the text, so this is a measured number rather than a documented one.
_MEASURED_WORST_CASE_CEILING = 6203


@pytest.fixture(autouse=True)
def _restore_model_override() -> Iterator[None]:
    """The CLI override is module state; a test that sets it must not leak it."""
    original = chunker.OLLAMA_MODEL
    yield
    chunker.OLLAMA_MODEL = original


# ─────────────────────────────────────────────
# #105: one model name for indexing and querying
# ─────────────────────────────────────────────


def test_the_indexer_embeds_with_the_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMBED_MODEL has to move the corpus, not only the query.

    This is the defect itself: the indexer used a name it held privately, so the
    setting that the README documents changed one side of the comparison.
    """
    monkeypatch.setattr(settings, "embed_model", "mxbai-embed-large")

    with patch.object(chunker, "embed_text", return_value=[0.0] * 768) as embed:
        chunker.get_embedding("some sentence")

    assert embed.call_args.args[0] == "mxbai-embed-large"


def test_the_indexer_and_the_query_path_agree(monkeypatch: pytest.MonkeyPatch) -> None:
    """The two sides must ask for the same model, which is what makes retrieval work."""
    monkeypatch.setattr(settings, "embed_model", "some-other-model")

    with patch.object(chunker, "embed_text", return_value=[0.0] * 768) as index_side:
        chunker.get_embedding("text")
    with patch("retrieval.embedder.embed_text", return_value=[0.0] * 768) as query_side:
        generate_embedding("text")

    assert index_side.call_args.args[0] == query_side.call_args.args[0]


def test_the_cli_override_still_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--model`` is documented and stays authoritative over the setting."""
    monkeypatch.setattr(settings, "embed_model", "from-settings")
    chunker.OLLAMA_MODEL = "from-the-command-line"

    with patch.object(chunker, "embed_text", return_value=[0.0] * 768) as embed:
        chunker.get_embedding("text")

    assert embed.call_args.args[0] == "from-the-command-line"


def test_a_model_of_the_wrong_shape_fails_before_indexing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Making EMBED_MODEL effective makes a wrong-dimension model reachable.

    Without the probe the run embeds every sentence of every PDF first and fails
    at the Qdrant upsert, naming neither the model nor the setting that chose it.
    """
    monkeypatch.setattr(settings, "embed_model", "wrong-shape-model")

    with (
        patch.object(chunker, "embed_text", return_value=[0.0] * 1024),
        pytest.raises(chunker.EmbeddingDimensionError) as excinfo,
    ):
        chunker.verify_embedding_dimension()

    message = str(excinfo.value)
    assert "wrong-shape-model" in message, "the error must name the model that was used"
    assert "1024" in message and str(chunker.EMBED_DIM) in message


def test_the_expected_shape_passes_the_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embed_model", "nomic-embed-text")

    with patch.object(chunker, "embed_text", return_value=[0.0] * chunker.EMBED_DIM):
        chunker.verify_embedding_dimension()


def _client_with(payload: dict | None, collection_exists: bool = True) -> MagicMock:
    """A Qdrant client holding one point with the given payload, or an absent collection."""
    client = MagicMock()
    named = MagicMock()
    named.name = chunker.COLLECTION_NAME if collection_exists else "something-else"
    client.get_collections.return_value.collections = [named]
    point = MagicMock()
    point.payload = payload
    client.scroll.return_value = ([point], None)
    return client


def test_a_collection_built_by_another_model_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same dimension, different model: the vectors do not belong in one space.

    ``init_qdrant`` keeps an existing collection and ``upsert_chunks`` writes fresh
    UUIDs, so without this the run appends vectors from a second model to the first
    model's corpus and every later search compares across both.
    """
    monkeypatch.setattr(settings, "embed_model", "mxbai-embed-large")
    client = _client_with({"embed_model": "nomic-embed-text"})

    with pytest.raises(chunker.EmbeddingModelMismatchError) as excinfo:
        chunker.verify_collection_model(client)

    message = str(excinfo.value)
    assert "nomic-embed-text" in message and "mxbai-embed-large" in message


def test_the_same_model_may_add_to_its_own_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embed_model", "nomic-embed-text")

    chunker.verify_collection_model(_client_with({"embed_model": "nomic-embed-text"}))


def test_a_collection_predating_the_stamp_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shipped collection has no stamp, and an absent stamp proves no mismatch.

    Refusing here would break every existing install to guard against a state that
    cannot be demonstrated. It is logged instead.
    """
    monkeypatch.setattr(settings, "embed_model", "nomic-embed-text")

    chunker.verify_collection_model(_client_with({"source_file": "boletim.pdf"}))


def test_a_collection_that_does_not_exist_yet_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embed_model", "nomic-embed-text")

    chunker.verify_collection_model(_client_with(None, collection_exists=False))


def test_indexed_points_record_the_model_that_embedded_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stamp the check reads has to be written, or it never protects anything."""
    monkeypatch.setattr(settings, "embed_model", "nomic-embed-text")
    chunk = chunker.Chunk(
        text="corpo do texto",
        sentences=["corpo do texto"],
        embedding=np.zeros(chunker.EMBED_DIM, dtype=np.float32),
        metadata={"num_sentences": 1, "source_file": "a.pdf", "source_path": "/a.pdf"},
    )
    client = MagicMock()

    chunker.upsert_chunks(client, [chunk])

    point = client.upsert.call_args.kwargs["points"][0]
    assert point.payload["embed_model"] == "nomic-embed-text"


# ─────────────────────────────────────────────
# #225: truncate below the context, not above it
# ─────────────────────────────────────────────


def test_the_truncation_limit_is_below_the_measured_ceiling() -> None:
    """A guard above the real limit does not guard anything.

    It was 8192 against a measured worst case of 6203, so the truncation ran and
    the call still failed.
    """
    assert _MAX_EMBED_CHARS <= _MEASURED_WORST_CASE_CEILING


def test_a_long_text_is_truncated_to_the_limit() -> None:
    """The truncation itself, on the value that actually reaches Ollama."""
    with patch("retrieval.ollama_embeddings.get_embed_client") as get_client:
        client = get_client.return_value
        client.embeddings.return_value = {"embedding": [0.0] * 768}

        embed_text("nomic-embed-text", "a" * 50_000)

    assert len(client.embeddings.call_args.kwargs["prompt"]) == _MAX_EMBED_CHARS


def test_a_short_text_is_passed_through_whole() -> None:
    """Truncation must not touch the texts the system actually embeds."""
    question = "Qual a dose de nitrogenio para milho safrinha?"

    with patch("retrieval.ollama_embeddings.get_embed_client") as get_client:
        client = get_client.return_value
        client.embeddings.return_value = {"embedding": [0.0] * 768}

        embed_text("nomic-embed-text", question)

    assert client.embeddings.call_args.kwargs["prompt"] == question


def test_the_limit_still_admits_a_chat_question() -> None:
    """Lowering the ceiling must not start truncating a request the schema allows.

    ``ChatRequest.question`` is capped at 2000 characters, so anything the API
    accepts has to survive the guard whole.
    """
    assert _MAX_EMBED_CHARS >= 2000
