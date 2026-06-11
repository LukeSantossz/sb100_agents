"""Retrieval module — vector search and embeddings.

Implements the retrieval layer of the RAG pipeline:

1. **Embeddings**: Converts text into dense vectors via Ollama (nomic-embed-text).
2. **Vector Search**: Retrieves relevant chunks from Qdrant by similarity.

Exports:
    generate_embedding: Generates an embedding vector for a text.
    search_context: Searches for similar chunks in Qdrant.
"""

from .embedder import generate_embedding
from .vector_store import search_context

__all__ = ["generate_embedding", "search_context"]
