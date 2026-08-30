import argparse
import logging
import re
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

from core.config import settings
from retrieval.ollama_embeddings import embed_text

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Global settings
# ─────────────────────────────────────────────

# The CLI override, and nothing else. None means "follow settings.embed_model",
# which is the same source retrieval/embedder.py reads: the corpus and the query
# have to be embedded by the same model or they land in different vector spaces,
# and a hardcoded name here meant EMBED_MODEL moved only the query (#105).
OLLAMA_MODEL: str | None = None
EMBED_DIM = 768  # collection vector size; retrieval/vector_store refuses any other
QDRANT_URL = "http://localhost:6333"
QDRANT_API_KEY: str | None = None  # for authenticated Qdrant servers
COLLECTION_NAME = "archives_v2"
# Payload key stamping each point with the model that embedded it.
EMBED_MODEL_PAYLOAD_KEY = "embed_model"

# Semantic chunking thresholds
SIMILARITY_THRESHOLD = 0.75  # below this → new chunk
MIN_CHUNK_SENTENCES = 3  # minimum sentences per chunk
MAX_CHUNK_SENTENCES = 20  # maximum sentences per chunk


# ─────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────


@dataclass
class Sentence:
    text: str
    embedding: np.ndarray = field(default=None, repr=False)


@dataclass
class Chunk:
    text: str
    sentences: list[str]
    embedding: np.ndarray = field(default=None, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────
# PDF text extraction
# ─────────────────────────────────────────────


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from all pages of the PDF."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)
    doc.close()
    return "\n".join(pages_text)


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences using a simple regex (no NLTK).
    Works well for Portuguese and English texts.
    """
    # Normalize spaces and line breaks
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Split on end-of-sentence punctuation
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÀÂÊÔÃÕ])", text)

    # Drop very short sentences (PDF noise)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    return sentences


# ─────────────────────────────────────────────
# Embeddings via Ollama (Llama)
# ─────────────────────────────────────────────


class EmbeddingDimensionError(RuntimeError):
    """Raised when the configured model does not produce the collection's vector shape."""


class EmbeddingModelMismatchError(RuntimeError):
    """Raised when the collection already holds vectors from a different embedding model."""


def resolve_embed_model() -> str:
    """The model to embed with: the ``--model`` override when given, else the setting.

    Resolved per call rather than at import, so a test or a caller that changes
    ``settings.embed_model`` is obeyed without reloading this module.
    """
    return OLLAMA_MODEL or settings.embed_model


def verify_embedding_dimension() -> None:
    """Fail before indexing if the configured model is not the shape the collection holds.

    ``EMBED_MODEL`` now reaches the indexer, which is the point of the fix, and that
    makes a model of another dimension reachable for the first time. Without this
    probe such a run embeds every sentence of every PDF, then fails at the Qdrant
    upsert with a vector-shape error that names neither the model nor the setting
    that chose it. One short call costs about a second and says both.

    Raises:
        EmbeddingDimensionError: If the model returns a vector of another length.
    """
    model = resolve_embed_model()
    actual_dim = len(embed_text(model, "dimension probe"))
    if actual_dim != EMBED_DIM:
        raise EmbeddingDimensionError(
            f"model {model!r} returns {actual_dim}-dimension vectors; this indexer "
            f"writes {EMBED_DIM}-dimension collections and retrieval/vector_store "
            f"refuses anything else. Set EMBED_MODEL to a {EMBED_DIM}-dimension "
            f"model, or change EMBED_DIM and re-index from scratch."
        )


def verify_collection_model(client: QdrantClient) -> None:
    """Refuse to add vectors from one model to a collection another model built.

    ``verify_embedding_dimension`` only proves the shape matches, and two different
    768-dimension models produce two incompatible spaces of the same shape.
    ``init_qdrant`` keeps an existing collection and ``upsert_chunks`` writes fresh
    UUIDs, so nothing else stops a second model's vectors being appended to the
    first model's corpus, after which every search compares across both.

    The check samples one point. That is enough for the case worth catching, a
    collection built entirely by one model and now being indexed with another, and
    it is not a proof for a collection that is already mixed. A collection written
    before the stamp existed carries no model name; an absent stamp cannot
    demonstrate a mismatch, so it is logged and allowed rather than breaking every
    install that predates this.

    Raises:
        EmbeddingModelMismatchError: If the sampled point names another model.
    """
    model = resolve_embed_model()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        return

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME, limit=1, with_payload=True, with_vectors=False
    )
    if not points:
        return

    recorded = (points[0].payload or {}).get(EMBED_MODEL_PAYLOAD_KEY)
    if recorded is None:
        logger.warning(
            "semantic_chunker.collection_model_unknown",
            extra={"collection": COLLECTION_NAME, "model": model},
        )
        return

    if recorded != model:
        raise EmbeddingModelMismatchError(
            f"collection {COLLECTION_NAME!r} holds vectors from {recorded!r} and "
            f"EMBED_MODEL is {model!r}. Two models of the same dimension still "
            f"produce different spaces, so indexing would mix them. Re-create the "
            f"collection to switch models, or set EMBED_MODEL back to {recorded!r}."
        )


def get_embedding(text: str) -> np.ndarray:
    """Generate an embedding for a text using the configured model via Ollama."""
    vec = embed_text(resolve_embed_model(), text)
    return np.array(vec, dtype=np.float32)


def get_embeddings_batch(texts: list[str], batch_size: int = 16) -> list[np.ndarray]:
    """Embed every text, one request at a time, reporting progress per group of ``batch_size``.

    The grouping is for the progress bar only: the embedding calls are sequential, and
    deliberately so. Ollama serialises inference on a CPU-only host, so the cost is the model,
    not the request overhead, and the faster-looking shapes are not faster. Measured over 96
    corpus sentences: this loop 23.58s, a 4-worker thread pool 21.47s, an 8-worker pool 23.28s,
    ``client.embed`` with 16 per call 20.47s, with 64 per call 25.25s. ``client.embed`` also
    returns L2-normalised vectors where ``client.embeddings`` returns raw ones, which changes
    the chunk vectors this function feeds into ``build_chunks``. See docs/specs/0008.
    """
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="  Generating embeddings", leave=False):
        batch = texts[i : i + batch_size]
        for text in batch:
            emb = get_embedding(text)
            embeddings.append(emb)
    return embeddings


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ─────────────────────────────────────────────
# Semantic chunking
# ─────────────────────────────────────────────


def semantic_chunking(sentences: list[Sentence]) -> list[list[Sentence]]:
    """
    Group sentences into chunks based on semantic similarity.

    Algorithm:
      1. Start a chunk with the first sentence.
      2. For each next sentence, compare against the current chunk's mean embedding.
      3. If similarity < threshold (or the chunk got too large) → new chunk.
      4. Respect minimum and maximum sizes.
    """
    if not sentences:
        return []

    chunks: list[list[Sentence]] = []
    current_chunk: list[Sentence] = [sentences[0]]

    for i in range(1, len(sentences)):
        sentence = sentences[i]

        # Mean embedding of the current chunk
        chunk_embeddings = np.stack([s.embedding for s in current_chunk])
        chunk_mean = chunk_embeddings.mean(axis=0)

        similarity = cosine_similarity(chunk_mean, sentence.embedding)
        too_large = len(current_chunk) >= MAX_CHUNK_SENTENCES
        too_small = len(current_chunk) < MIN_CHUNK_SENTENCES

        if (similarity < SIMILARITY_THRESHOLD and not too_small) or too_large:
            # Close the current chunk and start a new one
            chunks.append(current_chunk)
            current_chunk = [sentence]
        else:
            current_chunk.append(sentence)

    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def build_chunks(sentence_groups: list[list[Sentence]], metadata: dict) -> list[Chunk]:
    """Convert sentence groups into Chunk objects with a representative embedding."""
    chunks = []
    for group in sentence_groups:
        text = " ".join(s.text for s in group)

        # Chunk embedding = mean of the sentence embeddings
        embeddings = np.stack([s.embedding for s in group])
        chunk_embedding = embeddings.mean(axis=0)

        chunk = Chunk(
            text=text,
            sentences=[s.text for s in group],
            embedding=chunk_embedding,
            metadata={**metadata, "num_sentences": len(group)},
        )
        chunks.append(chunk)
    return chunks


# ─────────────────────────────────────────────
# Qdrant
# ─────────────────────────────────────────────


def init_qdrant(client: QdrantClient, embed_dim: int):
    """Create the Qdrant collection if it does not exist."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=embed_dim, distance=Distance.COSINE),
        )
        logger.info(
            "semantic_chunker.collection_created",
            extra={"collection": COLLECTION_NAME, "dim": embed_dim},
        )
    else:
        logger.info("semantic_chunker.collection_exists", extra={"collection": COLLECTION_NAME})


def upsert_chunks(client: QdrantClient, chunks: list[Chunk]):
    """Insert chunks into Qdrant."""
    points = []
    for chunk in chunks:
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk.embedding.tolist(),
            payload={
                "text": chunk.text,
                "num_sentences": chunk.metadata.get("num_sentences", 0),
                "source_file": chunk.metadata.get("source_file", ""),
                "source_path": chunk.metadata.get("source_path", ""),
                # Which model produced this vector. verify_collection_model reads it
                # to refuse mixing two models in one space; points written before the
                # stamp existed simply do not carry it.
                EMBED_MODEL_PAYLOAD_KEY: resolve_embed_model(),
            },
        )
        points.append(point)

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


# ─────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────


def process_pdf(pdf_path: str, client: QdrantClient) -> int:
    """Process a single PDF and index it in Qdrant. Returns the number of chunks."""
    filename = Path(pdf_path).name
    logger.info("semantic_chunker.pdf_start", extra={"file": filename})

    # 1. Text extraction
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        logger.warning("semantic_chunker.empty_pdf", extra={"file": filename})
        return 0

    # 2. Sentence splitting
    raw_sentences = split_into_sentences(raw_text)
    logger.info(
        "semantic_chunker.sentences_extracted",
        extra={"file": filename, "count": len(raw_sentences)},
    )

    if len(raw_sentences) == 0:
        return 0

    # 3. Sentence embeddings
    logger.info("semantic_chunker.embeddings_start", extra={"model": resolve_embed_model()})
    texts = list(raw_sentences)
    embeddings = get_embeddings_batch(texts)

    sentences = [
        Sentence(text=t, embedding=e) for t, e in zip(raw_sentences, embeddings, strict=True)
    ]

    # 4. Semantic chunking
    sentence_groups = semantic_chunking(sentences)
    logger.info(
        "semantic_chunker.chunks_built", extra={"file": filename, "count": len(sentence_groups)}
    )

    # 5. Build chunks with metadata
    metadata = {
        "source_file": filename,
        "source_path": str(Path(pdf_path).resolve()),
    }
    chunks = build_chunks(sentence_groups, metadata)

    # 6. Indexing in Qdrant
    count = upsert_chunks(client, chunks)
    logger.info("semantic_chunker.chunks_indexed", extra={"file": filename, "count": count})
    return count


def discover_pdfs(path: Path) -> list[Path]:
    """Return the PDFs ``path`` denotes: the file itself, or everything beneath a directory.

    Globbing ``**/*.pdf`` beneath the argument is what made a path to a single PDF
    match nothing, so the run indexed nothing and still exited 0 (#100). A file is
    now answered with itself, and anything that is neither a PDF file nor a
    directory answers with nothing, which ``process_folder`` turns into a failure
    rather than a silent success.

    Args:
        path: A PDF file, a directory to search recursively, or a path that is
            neither, including one that does not exist.

    Returns:
        Matching PDF paths, sorted so a run is reproducible. The extension is
        matched case-insensitively, in a directory as well as on a direct path.
    """
    if path.is_file():
        return [path] if path.suffix.lower() == ".pdf" else []
    if path.is_dir():
        # Filtering on the lowercased suffix rather than globbing "**/*.pdf":
        # that pattern is case-sensitive on Linux, so REPORT.PDF was accepted
        # when passed directly and skipped when found in a directory, and the
        # same file was indexed or ignored depending on how it was named on the
        # command line. set() because a case-insensitive filesystem can return
        # one entry more than once.
        return sorted({p for p in path.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"})
    return []


class NoPDFsFoundError(RuntimeError):
    """Raised when a path denotes no PDF, so the run fails instead of reporting success."""


def process_folder(folder_path: str):
    """Index every PDF the given path denotes.

    Raises:
        NoPDFsFoundError: When the path denotes no PDF. Indexing nothing is a
            failure: it leaves an empty collection behind and a ``/chat`` that
            answers from no context, and reporting success hides that.
    """
    pdf_files = discover_pdfs(Path(folder_path))
    if not pdf_files:
        logger.warning("semantic_chunker.no_pdfs_found", extra={"folder": folder_path})
        raise NoPDFsFoundError(
            f"no PDF found at {folder_path}. Pass a .pdf file, or a directory containing one."
        )

    logger.info(
        "semantic_chunker.folder_start",
        extra={"folder": folder_path, "pdf_count": len(pdf_files)},
    )

    # Fail on a wrong-shape model now, not after embedding every PDF.
    verify_embedding_dimension()

    # Initialize Qdrant
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    verify_collection_model(client)
    init_qdrant(client, EMBED_DIM)

    total_chunks = 0
    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        total_chunks += process_pdf(str(pdf_path), client)

    logger.info(
        "semantic_chunker.pipeline_complete",
        extra={
            "pdfs_processed": len(pdf_files),
            "chunks_indexed": total_chunks,
            "collection": COLLECTION_NAME,
            "qdrant_url": QDRANT_URL,
        },
    )


# ─────────────────────────────────────────────
# Search (usage example)
# ─────────────────────────────────────────────


def search(query: str, top_k: int = 5):
    """Semantic search over the collection."""
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    query_embedding = get_embedding(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        limit=top_k,
        with_payload=True,
    ).points

    logger.info("semantic_chunker.search", extra={"query": query, "top_k": top_k})
    for i, r in enumerate(results, 1):
        logger.info(
            "semantic_chunker.search_result",
            extra={
                "rank": i,
                "score": round(r.score, 4),
                "source_file": r.payload.get("source_file") if r.payload else None,
                "snippet": (r.payload.get("text", "")[:300] if r.payload else ""),
            },
        )


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """Entry point for CLI usage. Parses arguments and runs index or search.

    Args:
        argv: Argument list to parse; defaults to ``sys.argv[1:]``. Passing it
            explicitly is what lets the tests drive this without touching argv.

    Returns:
        Process exit code. Non-zero when the path denotes no PDF, so a run that
        indexed nothing cannot be mistaken for one that worked.
    """
    global OLLAMA_MODEL, SIMILARITY_THRESHOLD, QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Semantic Chunking Pipeline with Llama + Qdrant")
    subparsers = parser.add_subparsers(dest="command")

    # Command: index
    index_parser = subparsers.add_parser("index", help="Index PDFs from a folder")
    index_parser.add_argument("folder", help="Path to the folder containing the PDFs")
    index_parser.add_argument(
        "--model",
        default=None,
        help="Ollama model for embeddings (default: EMBED_MODEL, the same setting the API reads)",
    )
    index_parser.add_argument(
        "--threshold",
        type=float,
        default=SIMILARITY_THRESHOLD,
        help="Similarity threshold for a new chunk (default: 0.75)",
    )
    index_parser.add_argument("--qdrant-url", default=QDRANT_URL, help="Qdrant URL")
    index_parser.add_argument("--api-key", default=QDRANT_API_KEY, help="Qdrant API key (optional)")
    index_parser.add_argument("--collection", default=COLLECTION_NAME, help="Collection name")

    # Command: search
    search_parser = subparsers.add_parser("search", help="Semantic search over the collection")
    search_parser.add_argument("query", help="Search text")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    search_parser.add_argument("--qdrant-url", default=QDRANT_URL)
    search_parser.add_argument(
        "--api-key", default=QDRANT_API_KEY, help="Qdrant API key (optional)"
    )
    search_parser.add_argument("--collection", default=COLLECTION_NAME)

    args = parser.parse_args(argv)

    if args.command == "index":
        OLLAMA_MODEL = args.model
        SIMILARITY_THRESHOLD = args.threshold
        QDRANT_URL = args.qdrant_url
        QDRANT_API_KEY = args.api_key
        COLLECTION_NAME = args.collection
        try:
            process_folder(args.folder)
        except NoPDFsFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    elif args.command == "search":
        QDRANT_URL = args.qdrant_url
        QDRANT_API_KEY = args.api_key
        COLLECTION_NAME = args.collection
        search(args.query, top_k=args.top_k)

    else:
        parser.print_help()
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
