"""Endpoint de chat com pipeline RAG completo.

Este módulo implementa o endpoint principal de conversação:

1. Recebe pergunta do usuário com session_id e perfil.
2. Gera embedding da pergunta via Ollama.
3. Busca chunks relevantes no Qdrant.
4. Gera resposta adaptada ao perfil do usuário.
5. (Opcional) Verifica alucinações via entropia semântica.
6. Mantém histórico de conversação por sessão em memória.

Cache de sessões:
    - TTL: 1 hora de inatividade.
    - Máximo: 1000 sessões simultâneas (LRU eviction).
"""

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

router = APIRouter(prefix="/chat", tags=["chat"])

_SESSION_TTL_SECONDS = 3600  # 1 hora
_SESSION_MAX_SIZE = 1000

_sessions: OrderedDict[str, tuple[ConversationBuffer, float]] = OrderedDict()
_sessions_lock = threading.Lock()


def _get_or_create_buffer(session_id: str) -> ConversationBuffer:
    """Recupera ou cria buffer de conversação para a sessão.

    Implementa cache LRU com TTL para gerenciar memória de sessões.
    Cleanup lazy de sessões expiradas (até 10 por chamada).

    Thread-safe: todas as operações sobre ``_sessions`` ocorrem sob
    ``_sessions_lock`` para evitar race conditions no thread pool do FastAPI.

    Args:
        session_id: Identificador único da sessão.

    Returns:
        Buffer de conversação associado à sessão.
    """
    now = time.time()

    with _sessions_lock:
        # Cleanup de sessões expiradas (lazy, até 10 por chamada)
        expired = []
        for sid, (_, ts) in list(_sessions.items())[:10]:
            if now - ts > _SESSION_TTL_SECONDS:
                expired.append(sid)
            else:
                break  # OrderedDict mantém ordem de inserção
        for sid in expired:
            _sessions.pop(sid, None)

        # Enforce max size (remove mais antigas)
        while len(_sessions) >= _SESSION_MAX_SIZE:
            _sessions.popitem(last=False)

        # Recupera ou cria
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
    """Processa pergunta do usuário autenticado e retorna resposta do assistente.

    Pipeline RAG completo:
    1. Recupera/cria buffer de conversação para a sessão.
    2. Gera embedding da pergunta.
    3. Busca contexto relevante no Qdrant.
    4. Gera resposta via LLM (com verificação opcional de alucinações).
    5. Atualiza histórico de conversação.

    Args:
        req: Requisição contendo session_id, question e profile.
        current_user: Usuário autenticado (injetado por ``verify_token``).

    Returns:
        Resposta do assistente com score de alucinação.

    Raises:
        HTTPException(401): Se o token JWT estiver ausente, inválido ou expirado.
        HTTPException(503): Se Ollama ou Qdrant estiverem indisponíveis.
    """
    _ = current_user  # auth gate aplicado por Depends(verify_token); identidade não consumida aqui
    buffer = _get_or_create_buffer(req.session_id)

    try:
        embedding = generate_embedding(req.question)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao gerar embedding: {str(e)}. Verifique se o Ollama está rodando.",
        ) from e

    try:
        context_chunks = search_context(embedding)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao buscar contexto: {str(e)}. Verifique se o Qdrant está rodando.",
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
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao gerar resposta: {str(e)}. Verifique se o Ollama está rodando.",
        ) from e

    # Atualiza buffer somente após sucesso
    buffer.add("user", req.question)
    buffer.add("assistant", response.answer)

    return response
