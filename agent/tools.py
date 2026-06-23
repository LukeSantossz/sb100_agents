"""Agent tools that expose the RAG retrieval layer to the deep agent."""

import logging

from langchain_core.tools import tool

from generation.llm import _sanitize_context
from retrieval import generate_embedding, search_context

logger = logging.getLogger(__name__)

_NO_CONTEXT = "No relevant context was found in the corpus for this query."
_RETRIEVAL_ERROR = "The corpus could not be searched right now due to a retrieval error."

SEARCH_CORPUS_SENTINELS: frozenset[str] = frozenset({_NO_CONTEXT, _RETRIEVAL_ERROR})


@tool
def search_corpus(query: str) -> str:
    """Search the indexed agricultural corpus and return relevant context text.

    Embeds the query and runs vector search over the configured collection, returning the
    concatenated text of the most similar chunks.
    """
    try:
        embedding = generate_embedding(query)
        chunks = search_context(embedding)
    except Exception:
        # Surface, do not silence: the full traceback is logged and an informative
        # message is returned so the agent loop can respond instead of crashing.
        logger.exception("agent.search_corpus.failure", extra={"chars": len(query)})
        return _RETRIEVAL_ERROR
    texts = [chunk for chunk in chunks if chunk]
    if not texts:
        return _NO_CONTEXT
    return _sanitize_context("\n\n".join(texts))
