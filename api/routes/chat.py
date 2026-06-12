"""Chat endpoint with the full RAG pipeline.

This module implements the main conversation endpoint:

1. Receives the user's question with session_id and profile.
2. Generates the question embedding via Ollama.
3. Searches relevant chunks in Qdrant.
4. Generates an answer adapted to the user's profile.
5. (Optional) Checks for hallucinations via semantic entropy.
6. Keeps per-session conversation history in memory.

Session cache:
    - TTL: 1 hour of inactivity.
    - Maximum: 1000 concurrent sessions (LRU eviction).
"""

import logging
import threading
import time
from collections import OrderedDict

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import verify_token
from core.config import settings
from core.schemas import ChatRequest, ChatResponse
from database.models import User
from generation.llm import generate
from memory.conversation import ConversationBuffer
from retrieval.embedder import generate_embedding
from retrieval.vector_store import search_context
from verification.gate import evaluate as verify_and_generate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_SESSION_TTL_SECONDS = 3600  # 1 hour
_SESSION_MAX_SIZE = 1000

_sessions: OrderedDict[str, tuple[ConversationBuffer, float]] = OrderedDict()
_sessions_lock = threading.Lock()


def _get_or_create_buffer(session_id: str) -> ConversationBuffer:
    """Get or create the conversation buffer for the session.

    Implements an LRU cache with TTL to manage session memory.
    Lazily cleans up expired sessions (up to 10 per call).

    Thread-safe: every operation on ``_sessions`` happens under
    ``_sessions_lock`` to avoid race conditions in FastAPI's thread pool.

    Args:
        session_id: Unique session identifier.

    Returns:
        Conversation buffer associated with the session.
    """
    now = time.time()

    with _sessions_lock:
        # Clean up expired sessions (lazy, up to 10 per call)
        expired = []
        for sid, (_, ts) in list(_sessions.items())[:10]:
            if now - ts > _SESSION_TTL_SECONDS:
                expired.append(sid)
            else:
                break  # OrderedDict keeps insertion order
        for sid in expired:
            _sessions.pop(sid, None)

        # Enforce max size (drop oldest entries)
        while len(_sessions) >= _SESSION_MAX_SIZE:
            _sessions.popitem(last=False)

        # Get or create
        existing = _sessions.pop(session_id, None)
        if existing is not None:
            buffer, _ = existing
            _sessions[session_id] = (buffer, now)
            return buffer

        buffer = ConversationBuffer(maxlen=settings.buffer_maxlen)
        _sessions[session_id] = (buffer, now)
        return buffer


@router.post("", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    current_user: User = Depends(verify_token),
) -> ChatResponse:
    """Process the authenticated user's question and return the assistant answer.

    Full RAG pipeline:
    1. Get/create the conversation buffer for the session.
    2. Generate the question embedding.
    3. Search relevant context in Qdrant.
    4. Generate the answer via LLM (with optional hallucination check).
    5. Update the conversation history.

    Args:
        req: Request containing session_id, question and profile.
        current_user: Authenticated user (injected by ``verify_token``).

    Returns:
        Assistant answer with hallucination score.

    Raises:
        HTTPException(401): If the JWT is missing, invalid or expired.
        HTTPException(503): If Ollama or Qdrant are unavailable.
    """
    logger.info(
        "chat.access",
        extra={"username": current_user.username, "session_id": req.session_id},
    )
    buffer = _get_or_create_buffer(req.session_id)

    try:
        embedding = generate_embedding(req.question)
    except Exception as e:
        logger.warning(
            "chat.embedding_failure",
            extra={"username": current_user.username, "error": str(e)},
        )
        raise HTTPException(
            status_code=503,
            detail=f"Embedding generation failed: {str(e)}. Check that Ollama is running.",
        ) from e

    try:
        context_chunks = search_context(embedding)
    except Exception as e:
        logger.warning(
            "chat.context_failure",
            extra={"username": current_user.username, "error": str(e)},
        )
        raise HTTPException(
            status_code=503,
            detail=f"Context search failed: {str(e)}. Check that Qdrant is running.",
        ) from e

    context_text = "\n\n".join(context_chunks) if context_chunks else ""
    history = buffer.to_messages()

    try:
        if settings.verification_enabled:
            response = verify_and_generate(
                question=req.question,
                context=context_text,
                history=history,
                profile=req.profile,
            )
        else:
            answer = generate(
                question=req.question,
                context=context_text,
                history=history,
                profile=req.profile,
            )
            response = ChatResponse(answer=answer, hallucination_score=0.0)
    except Exception as e:
        logger.warning(
            "chat.generation_failure",
            extra={"username": current_user.username, "error": str(e)},
        )
        raise HTTPException(
            status_code=503,
            detail=f"Answer generation failed: {str(e)}. Check that Ollama is running.",
        ) from e

    # Update the buffer only after success
    buffer.add("user", req.question)
    buffer.add("assistant", response.answer)

    return response
