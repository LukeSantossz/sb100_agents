"""Módulo de retrieval — busca vetorial e embeddings.

Este módulo implementa a camada de recuperação do pipeline RAG:

1. **Embeddings**: Converte texto em vetores densos via Ollama (nomic-embed-text).
2. **Busca Vetorial**: Recupera chunks relevantes do Qdrant por similaridade.

Exports:
    generate_embedding: Gera vetor de embedding para um texto.
    search_context: Busca chunks similares no Qdrant.
"""

from .embedder import generate_embedding
from .vector_store import search_context

__all__ = ["generate_embedding", "search_context"]
