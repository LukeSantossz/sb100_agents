"""Hallucination verification gate with retry and fallback.

If the entropy computation fails, verification degrades to a neutral score
(0.5) while keeping the generated answer — without masking generator
failures, which must propagate to the caller as usual.
"""

import logging

from core.config import settings
from core.schemas import ChatResponse, UserProfile
from generation.llm import generate
from verification.entropy import MissingVerifierKeyError, compute_entropy_score

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
FALLBACK_MESSAGE = "I cannot answer this topic with confidence."
NEUTRAL_SCORE = 0.5


def evaluate(
    question: str,
    context: str,
    history: list[dict[str, str]],
    profile: UserProfile,
) -> ChatResponse:
    """Evaluates and regenerates the answer if the entropy score exceeds the threshold.

    Logic:
        1. Generate the answer — if it fails, propagate (generator errors are
           a real 503 case).
        2. Compute the entropy score — if it fails, return the answer with a
           neutral 0.5 score (verification is optional; its failure must not
           take down the pipeline).
        3. If score <= threshold, return the answer.
        4. If it exceeds, regenerate up to ``MAX_RETRIES``.
        5. After exhausting attempts, return ``FALLBACK_MESSAGE`` with the last score.
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
        except MissingVerifierKeyError:
            # A config state, not a crash: degrade to neutral without a traceback.
            logger.warning(
                "verification.gate.verifier_key_missing",
                extra={"attempt": attempt},
            )
            return ChatResponse(answer=answer, hallucination_score=NEUTRAL_SCORE)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "verification.gate.entropy_failure",
                extra={"attempt": attempt, "error": str(exc)},
            )
            return ChatResponse(answer=answer, hallucination_score=NEUTRAL_SCORE)

        if last_score <= settings.hallucination_threshold:
            return ChatResponse(answer=answer, hallucination_score=last_score)

    return ChatResponse(answer=FALLBACK_MESSAGE, hallucination_score=last_score)


def score_context(question: str, context: str) -> float:
    """Score the trustworthiness of an answer grounded in ``context`` for the agent path.

    Returns the neutral score when there is no context to verify; otherwise runs the
    semantic-entropy score with the same neutral fallback as ``evaluate`` on verifier failure.
    """
    if not context.strip():
        return NEUTRAL_SCORE
    try:
        return compute_entropy_score(question=question, context=context)
    except MissingVerifierKeyError:
        logger.warning("verification.score_context.verifier_key_missing")
        return NEUTRAL_SCORE
    except Exception as exc:  # noqa: BLE001
        logger.exception("verification.score_context.failure", extra={"error": str(exc)})
        return NEUTRAL_SCORE
