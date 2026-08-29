import argparse
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

from retrieval.ollama_embeddings import embed_text

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Global settings
# ─────────────────────────────────────────────

OLLAMA_MODEL = "nomic-embed-text"  # embeddings model via Ollama
EMBED_DIM = 768  # nomic-embed-text dimension
QDRANT_URL = "http://localhost:6333"
QDRANT_API_KEY: str | None = None  # for authenticated Qdrant servers
COLLECTION_NAME = "archives_v2"

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


def get_embedding(text: str) -> np.ndarray:
    """Generate an embedding for a text using the Llama model via Ollama."""
    vec = embed_text(OLLAMA_MODEL, text)
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
    logger.info("semantic_chunker.embeddings_start", extra={"model": OLLAMA_MODEL})
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


def process_folder(folder_path: str):
    """Process all PDFs in a folder."""
    pdf_files = list(Path(folder_path).glob("**/*.pdf"))
    if not pdf_files:
        logger.warning("semantic_chunker.no_pdfs_found", extra={"folder": folder_path})
        return

    logger.info(
        "semantic_chunker.folder_start",
        extra={"folder": folder_path, "pdf_count": len(pdf_files)},
    )

    # Initialize Qdrant
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
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


def main() -> None:
    """Entry point for CLI usage. Parses arguments and runs index or search."""
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
    index_parser.add_argument("--model", default=OLLAMA_MODEL, help="Ollama model for embeddings")
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

    args = parser.parse_args()

    if args.command == "index":
        OLLAMA_MODEL = args.model
        SIMILARITY_THRESHOLD = args.threshold
        QDRANT_URL = args.qdrant_url
        QDRANT_API_KEY = args.api_key
        COLLECTION_NAME = args.collection
        process_folder(args.folder)

    elif args.command == "search":
        QDRANT_URL = args.qdrant_url
        QDRANT_API_KEY = args.api_key
        COLLECTION_NAME = args.collection
        search(args.query, top_k=args.top_k)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
