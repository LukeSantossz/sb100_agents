"""Agricultural domain gate for the agent path (ADR-0010).

A cheap pre-flight check: embed the question and measure the single best cosine
similarity against the indexed corpus. Below ``settings.intent_threshold`` the
question is out of domain and the agent loop is skipped. The corpus is the domain
reference, so this is a coverage proxy, not a topic classifier. Fails open.
"""

import logging
from dataclasses import dataclass

from core.config import settings
from retrieval import generate_embedding, top_similarity

logger = logging.getLogger(__name__)

OUT_OF_DOMAIN_MESSAGE = (
    "Só respondo sobre temas agrícolas cobertos pela base de documentos. "
    "Reformule sua pergunta nesse domínio."
)


@dataclass(frozen=True)
class DomainDecision:
    """Outcome of the domain gate: whether the question is in domain and the score seen."""

    in_domain: bool
    score: float | None


def classify_domain(question: str) -> DomainDecision:
    """Decide whether ``question`` is in the agricultural domain via corpus retrieval score.

    Embeds the question and compares the top corpus similarity to ``settings.intent_threshold``.
    Fails open: on any embedding/search error, or when the collection yields no score, the
    question is treated as in domain (the agent path shares this retrieval and would surface the
    failure itself) and the failure is logged.
    """
    try:
        embedding = generate_embedding(question)
        score = top_similarity(embedding)
    except Exception:
        logger.exception("agent.intent.failure", extra={"chars": len(question)})
        return DomainDecision(in_domain=True, score=None)

    if score is None:
        logger.warning("agent.intent.no_score", extra={"chars": len(question)})
        return DomainDecision(in_domain=True, score=None)

    return DomainDecision(in_domain=score >= settings.intent_threshold, score=score)
