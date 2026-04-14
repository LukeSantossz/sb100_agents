import ollama
from fastapi import APIRouter, HTTPException

from core.config import settings
from core.schemas import ChatRequest, ChatResponse
from retrieval.embedder import generate_embedding
from retrieval.vector_store import search_context

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = """Você é um assistente especializado em agronomia e agricultura.
Responda às perguntas do usuário de forma clara e objetiva, baseando-se no contexto fornecido.
Se o contexto não contiver informação suficiente, indique isso ao usuário.
Adapte a complexidade da resposta ao nível de expertise do usuário."""


def build_prompt(question: str, context: list[str], expertise: str) -> str:
    """Monta o prompt com contexto recuperado e nível de expertise."""
    context_text = "\n\n".join(context) if context else "Nenhum contexto disponível."

    expertise_instruction = {
        "beginner": "Use linguagem simples e evite termos técnicos.",
        "intermediate": "Use termos técnicos com explicações breves quando necessário.",
        "expert": "Use terminologia técnica avançada.",
    }.get(expertise, "")

    return f"""Contexto recuperado:
{context_text}

Nível do usuário: {expertise}
{expertise_instruction}

Pergunta: {question}

Resposta:"""


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        embedding = generate_embedding(req.question)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao gerar embedding: {str(e)}. Verifique se o Ollama está rodando.",
        )

    try:
        context = search_context(embedding)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao buscar contexto: {str(e)}. Verifique se o Qdrant está rodando.",
        )

    prompt = build_prompt(req.question, context, req.profile.expertise.value)

    try:
        response = ollama.chat(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        answer = response["message"]["content"]
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao gerar resposta: {str(e)}. Verifique se o Ollama está rodando.",
        )

    return ChatResponse(
        answer=answer,
        hallucination_score=0.0,
    )
