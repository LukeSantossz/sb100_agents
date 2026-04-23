from fastapi import APIRouter, HTTPException

from core.config import settings
from core.schemas import ChatRequest, ChatResponse
from generation.llm import generate
from memory.conversation import ConversationBuffer
from retrieval.embedder import generate_embedding
from retrieval.vector_store import search_context
from verification.gate import evaluate as verify_and_generate

router = APIRouter(prefix="/chat", tags=["chat"])

# Armazena buffers por sessão
_sessions: dict[str, ConversationBuffer] = {}


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Recupera ou cria buffer para a sessão
    buffer = _sessions.setdefault(
        req.session_id,
        ConversationBuffer(maxlen=settings.buffer_maxlen),
    )

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
