import time
from collections import OrderedDict

from fastapi import APIRouter, HTTPException

from core.config import settings
from core.schemas import ChatRequest, ChatResponse
from generation.llm import generate
from memory.conversation import ConversationBuffer
from retrieval.embedder import generate_embedding
from retrieval.vector_store import search_context
from verification.gate import evaluate as verify_and_generate

router = APIRouter(prefix="/chat", tags=["chat"])

# Configuração do cache de sessões
_SESSION_TTL_SECONDS = 3600  # 1 hora
_SESSION_MAX_SIZE = 1000

# Armazena buffers por sessão com timestamps
_sessions: OrderedDict[str, tuple[ConversationBuffer, float]] = OrderedDict()


def _get_or_create_buffer(session_id: str) -> ConversationBuffer:
    """Recupera ou cria buffer para a sessão com cleanup de entradas expiradas."""
    now = time.time()

    # Cleanup de sessões expiradas (lazy, até 10 por chamada)
    expired = []
    for sid, (_, ts) in list(_sessions.items())[:10]:
        if now - ts > _SESSION_TTL_SECONDS:
            expired.append(sid)
        else:
            break  # OrderedDict mantém ordem de inserção
    for sid in expired:
        del _sessions[sid]

    # Enforce max size (remove mais antigas)
    while len(_sessions) >= _SESSION_MAX_SIZE:
        _sessions.popitem(last=False)

    # Recupera ou cria
    if session_id in _sessions:
        buffer, _ = _sessions.pop(session_id)  # Remove para reinserir no final
        _sessions[session_id] = (buffer, now)
        return buffer

    buffer = ConversationBuffer(maxlen=settings.buffer_maxlen)
    _sessions[session_id] = (buffer, now)
    return buffer


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    buffer = _get_or_create_buffer(req.session_id)

    try:
        embedding = generate_embedding(req.question)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao gerar embedding: {str(e)}. Verifique se o Ollama está rodando.",
        )

    try:
        context_chunks = search_context(embedding)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao buscar contexto: {str(e)}. Verifique se o Qdrant está rodando.",
        )

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
        )

    # Atualiza buffer somente após sucesso
    buffer.add("user", req.question)
    buffer.add("assistant", response.answer)

    return response
