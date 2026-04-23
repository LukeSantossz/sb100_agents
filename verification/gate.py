"""Gate de verificação de alucinações com retry e fallback."""

from core.config import settings
from core.schemas import ChatResponse, UserProfile
from generation.llm import generate
from verification.entropy import compute_entropy_score

MAX_RETRIES = 2
FALLBACK_MESSAGE = "Não sei informar com segurança sobre este tópico."


def evaluate(
    question: str,
    context: str,
    history: list[dict],
    profile: UserProfile,
) -> ChatResponse:
    """Avalia e regenera resposta se score de entropia exceder threshold.

    Lógica:
    1. Gera resposta
    2. Calcula score de entropia
    3. Se score > threshold, regenera (máx 2 tentativas)
    4. Se todas tentativas falharem, retorna fallback com score da última

    Args:
        question: Pergunta do usuário.
        context: Contexto RAG concatenado.
        history: Histórico de conversação.
        profile: Perfil do usuário.

    Returns:
        ChatResponse com answer e hallucination_score.
    """
    last_answer = ""
    last_score = 0.0

    for attempt in range(MAX_RETRIES):
        answer = generate(
            question=question,
            context=context,
            history=history,
            profile=profile,
        )

        score = compute_entropy_score(
            response=answer,
            context=context,
            question=question,
        )

        last_answer = answer
        last_score = score

        if score <= settings.hallucination_threshold:
            return ChatResponse(
                answer=answer,
                hallucination_score=score,
            )

    return ChatResponse(
        answer=FALLBACK_MESSAGE,
        hallucination_score=last_score,
    )
