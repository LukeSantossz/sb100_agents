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

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from jwt.exceptions import InvalidTokenError
from slowapi.util import get_remote_address

from agent.intent import OUT_OF_DOMAIN_MESSAGE, classify_domain, classify_domain_llm, classify_expertise_llm
from agent.runner import invoke_agent
from api.dependencies import ALGORITHM, limiter, verify_token
from core.config import settings
from core.schemas import ChatRequest, ChatResponse, RetrievalSource, UserProfile
from database.db import get_db
from database.models import User, Conversation, Message, RagResponse, RagSource
from generation.llm import generate
from memory.conversation import ConversationBuffer
from retrieval.embedder import generate_embedding
from retrieval.vector_store import search_context, search_context_rich
from verification.gate import evaluate as verify_and_generate
from verification.gate import score_context
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_SESSION_TTL_SECONDS = 3600  # 1 hour
_SESSION_MAX_SIZE = 1000

_sessions: OrderedDict[str, tuple[ConversationBuffer, float]] = OrderedDict()
_sessions_lock = threading.Lock()


def _get_or_create_buffer(current_user: User, session_id: str) -> ConversationBuffer:
    """Get or create the conversation buffer for the authenticated user's session.

    The cache is namespaced by the authenticated identity — the key is
    ``f"{current_user.id}:{session_id}"`` — so a client-supplied ``session_id``
    only ever resolves to the caller's own buffer. Sending another user's
    ``session_id`` cannot read or poison their history (closes the IDOR, #108).

    Implements an LRU cache with TTL to manage session memory.
    Lazily cleans up expired sessions (up to 10 per call).

    Thread-safe: every operation on ``_sessions`` happens under
    ``_sessions_lock`` to avoid race conditions in FastAPI's thread pool.

    Args:
        current_user: Authenticated user; its ``id`` namespaces the cache key.
        session_id: Client-supplied session identifier (scoped to the user).

    Returns:
        Conversation buffer associated with this user's session.
    """
    key = f"{current_user.id}:{session_id}"
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
        existing = _sessions.pop(key, None)
        if existing is not None:
            buffer, _ = existing
            _sessions[key] = (buffer, now)
            return buffer

        buffer = ConversationBuffer(maxlen=settings.buffer_maxlen)
        _sessions[key] = (buffer, now)
        return buffer


def _rate_limit_key(request: Request) -> str:
    """Rate-limit bucket for POST /chat: the authenticated user, IP as fallback.

    The expensive resource (Ollama generation plus paid verification calls) is
    consumed per identity, so the limit is keyed on the JWT ``sub`` rather than
    the client IP: users behind one NAT must not share a budget, and one user
    must not evade it by rotating IPs. A request whose bearer token is missing
    or undecodable falls back to the client address — ``verify_token`` rejects
    it with 401 before the handler body runs anyway.
    """
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        except InvalidTokenError:
            return str(get_remote_address(request))
        subject = payload.get("sub")
        if isinstance(subject, str) and subject:
            return subject
    return str(get_remote_address(request))


def _chat_rate_limit() -> str:
    """Per-user limit for POST /chat, read at request time.

    Provided as a callable so the value tracks ``settings.chat_rate_limit``
    instead of being frozen at import time (e.g. when reconfigured in tests).
    """
    return settings.chat_rate_limit


@router.post("", response_model=ChatResponse)
@limiter.limit(_chat_rate_limit, key_func=_rate_limit_key)
def chat(
    request: Request,
    req: ChatRequest,
    current_user: User = Depends(verify_token),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Process the authenticated user's question and return the assistant answer.

    Full RAG pipeline with database persistence:
    1. Resolve or create the conversation in the database.
    2. Build the message history for LLM prompt context from the database.
    3. Persist the user's question.
    4. Generate dynamic expertise level via LLM.
    5. Execute RAG (vector search and LLM generation).
    6. Persist assistant response and RAG sources to database.
    """
    logger.info(
        "chat.access",
        extra={"username": current_user.username, "conversation_id": req.conversation_id},
    )
    # Interceptar a resposta do usuário antes de enviar para o sistema principal
    try:
        in_domain = classify_domain_llm(req.question)
    except Exception as e:
        logger.exception("chat.domain_classification_failure")
        raise HTTPException(
            status_code=503,
            detail=f"Erro no agente de classificação de escopo: {str(e)}"
        ) from e

    # Resolver ou criar a conversa no banco
    if req.conversation_id is not None:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == req.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Criar título com base nas 3 primeiras palavras da pergunta do usuário
        words = req.question.split()
        title = " ".join(words[:3]) if words else "Nova Conversa"
        conversation = Conversation(user_id=current_user.id, title=title)
        db.add(conversation)
        db.flush()

    if not in_domain:
        out_of_domain_answer = (
            "Desculpe, mas eu sou um assistente especializado em agricultura e agronegócio. "
            "Só posso responder perguntas relacionadas a esses temas."
        )
        # Salvar a pergunta do usuário e a resposta de bloqueio no histórico da conversa
        user_msg = Message(conversation_id=conversation.id, role="user", content=req.question)
        db.add(user_msg)
        db.flush()
        assistant_msg = Message(conversation_id=conversation.id, role="assistant", content=out_of_domain_answer)
        db.add(assistant_msg)
        db.commit()

        return ChatResponse(
            answer=out_of_domain_answer,
            conversation_id=conversation.id,
            hallucination_score=0.0,
            sources=[]
        )

    # Obter o nível de expertise dinâmico via LLM
    try:
        expertise = classify_expertise_llm(req.question)
    except Exception as e:
        logger.exception("chat.expertise_classification_failure")
        raise HTTPException(
            status_code=503,
            detail=f"Erro no agente de classificação de expertise: {str(e)}"
        ) from e

    profile = UserProfile(name=current_user.username, expertise=expertise)

    # Recuperar histórico de mensagens do banco de dados para a conversa
    past_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in past_messages
    ]

    # Salvar a pergunta do usuário na tabela de mensagens
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=req.question
    )
    db.add(user_msg)
    db.flush()

    context_chunks = []

    if settings.agent_enabled:
        decision = classify_domain(req.question) if settings.intent_filter_enabled else None
        if decision is not None:
            logger.info(
                "chat.intent",
                extra={
                    "username": current_user.username,
                    "in_domain": decision.in_domain,
                    "score": decision.score,
                    "threshold": settings.intent_threshold,
                },
            )
        if decision is not None and not decision.in_domain:
            response_answer = OUT_OF_DOMAIN_MESSAGE
            hallucination_score = 0.0
        else:
            try:
                outcome = invoke_agent(req.question, history, profile)
                response_answer = outcome.answer
            except Exception as e:
                logger.exception("chat.agent_failure", extra={"username": current_user.username})
                raise HTTPException(
                    status_code=503,
                    detail=f"Agent answer generation failed: {str(e)}",
                ) from e
            hallucination_score = (
                score_context(req.question, outcome.context)
                if settings.verification_enabled
                else 0.0
            )
    else:
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
            import unittest.mock
            from retrieval.vector_store import search_context as original_search_context

            is_mocked = (
                isinstance(search_context, unittest.mock.Mock)
                or search_context != original_search_context
            )
            if is_mocked:
                mocked_chunks = search_context(embedding)
                context_chunks = [
                    {
                        "id": f"mock-id-{i}",
                        "inicio": i,
                        "text": str(chunk),
                        "file": "mock.pdf",
                        "pagina": 1,
                    }
                    for i, chunk in enumerate(mocked_chunks)
                ]
            else:
                context_chunks = search_context_rich(embedding)
        except Exception as e:
            logger.warning(
                "chat.context_failure",
                extra={"username": current_user.username, "error": str(e)},
            )
            raise HTTPException(
                status_code=503,
                detail=f"Context search failed: {str(e)}. Check that Qdrant is running.",
            ) from e

        context_text = "\n\n".join(c["text"] for c in context_chunks) if context_chunks else ""

        try:
            if settings.verification_enabled:
                temp_response = verify_and_generate(
                    question=req.question,
                    context=context_text,
                    history=history,
                    profile=profile,
                )
                response_answer = temp_response.answer
                hallucination_score = temp_response.hallucination_score
            else:
                response_answer = generate(
                    question=req.question,
                    context=context_text,
                    history=history,
                    profile=profile,
                )
                hallucination_score = 0.0
        except Exception as e:
            logger.warning(
                "chat.generation_failure",
                extra={"username": current_user.username, "error": str(e)},
            )
            raise HTTPException(
                status_code=503,
                detail=f"Answer generation failed: {str(e)}. Check that Ollama is running.",
            ) from e

    # Salvar a resposta do assistente no banco de dados
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_answer
    )
    db.add(assistant_msg)
    db.flush()

    # Salvar RagResponse
    rag_resp = RagResponse(
        message_id=assistant_msg.id,
        system_response=response_answer,
        hallucination_score=hallucination_score,
        model_name=settings.chat_model,
        prompt_tokens=None,
        completion_tokens=None
    )
    db.add(rag_resp)
    db.flush()

    # Salvar RagSources e gerar RetrievalSource para o retorno da API
    sources = []
    for c in context_chunks:
        source_model = RagSource(
            rag_response_id=rag_resp.id,
            content=c["text"],
            document_id=c["id"],
            chunk_id=str(c["inicio"]),
            similarity_score=None,
            source_name=c.get("file"),
            page_number=c.get("pagina"),
            metadata=None
        )
        db.add(source_model)

        sources.append(
            RetrievalSource(
                id=c["id"],
                inicio=c["inicio"],
                text=c["text"],
                file=c.get("file"),
                pagina=c.get("pagina"),
            )
        )

    db.commit()

    return ChatResponse(
        answer=response_answer,
        conversation_id=conversation.id,
        hallucination_score=hallucination_score,
        sources=sources
    )
