"""Gate de verificação de alucinações com retry e fallback.

TASK-T64: se o cálculo de entropia falhar, a verificação degrada para um score
neutro (0.5) preservando a resposta gerada — sem mascarar a falha do gerador,
que deve propagar normalmente para o caller.
"""

import logging

from core.config import settings
from core.schemas import ChatResponse, UserProfile
from generation.llm import generate
from verification.entropy import compute_entropy_score

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
FALLBACK_MESSAGE = "Não sei informar com segurança sobre este tópico."
NEUTRAL_SCORE = 0.5


def evaluate(
    question: str,
    context: str,
    history: list[dict[str, str]],
    profile: UserProfile,
) -> ChatResponse:
    """Avalia e regenera resposta se score de entropia exceder threshold.

    Lógica:
        1. Gera resposta — se falhar, propaga (erro do gerador é caso real de 503).
        2. Calcula score de entropia — se falhar, retorna a resposta com score
           neutro 0.5 (a verificação é opcional; falha não derruba o pipeline).
        3. Se score <= threshold, devolve a resposta.
        4. Se exceder, regenera até ``MAX_RETRIES``.
        5. Após esgotar tentativas, retorna ``FALLBACK_MESSAGE`` com último score.
    """
    last_score = 0.0

    for attempt in range(MAX_RETRIES):
        answer = generate(
            question=question,
            context=context,
            history=history,
            profile=profile,
        )

        try:
            last_score = compute_entropy_score(
                question=question,
                context=context,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "verification.gate.entropy_failure",
                extra={"attempt": attempt, "error": str(exc)},
            )
            return ChatResponse(answer=answer, hallucination_score=NEUTRAL_SCORE)

        if last_score <= settings.hallucination_threshold:
            return ChatResponse(answer=answer, hallucination_score=last_score)

    return ChatResponse(answer=FALLBACK_MESSAGE, hallucination_score=last_score)
