"""Semantic entropy computation for hallucination detection.

Reference: Semantic Uncertainty (Farquhar et al., 2023)
https://arxiv.org/abs/2302.09664

Numerical-stability and error-handling notes:

- Epsilon ``1e-10`` replaces the ``> 0`` test in cosine similarity.
- ``logger.warning`` when the selected provider has no API key.
- Sample generation tolerates partial failures (continues) and propagates
  only if all fail.
- Safe access to ``resp["message"]["content"]`` via ``.get(...)``.
- Provider validated against the sample-function keys before dispatch.
- Temperature comes from ``settings.entropy_temperature``.
"""

import logging
import math
from typing import Any, cast

from core.config import settings
from core.ollama_clients import get_chat_client
from retrieval.ollama_embeddings import embed_text

logger = logging.getLogger(__name__)

_EPSILON = 1e-10

DEFAULT_VERIFICATION_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "ollama": "llama3.2:3b",
    "openrouter": "google/gemma-4-31b-it",
}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _build_messages(question: str, context: str) -> list[dict[str, str]]:
    """Builds the message list for sampling."""
    prompt = f"Contexto:\n{context}\n\nPergunta: {question}" if context else question
    return [
        {
            "role": "system",
            "content": "Você é um assistente especializado em agronomia. Responda de forma concisa.",
        },
        {"role": "user", "content": prompt},
    ]


def _generate_one_groq(question: str, context: str, model: str) -> str:
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=_build_messages(question, context),  # type: ignore[arg-type]
        temperature=settings.entropy_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    return resp.choices[0].message.content or ""


def _generate_one_ollama(question: str, context: str, model: str) -> str:
    # ollama-py returns ChatResponse; casting to dict[str, Any] keeps the safe
    # ``.get`` access (still valid at runtime for ChatResponse).
    # Shared client (singleton with timeout — see core/ollama_clients).
    resp = cast(
        dict[str, Any],
        get_chat_client().chat(
            model=model,
            messages=_build_messages(question, context),
            options={
                "temperature": settings.entropy_temperature,
                "num_predict": settings.llm_max_tokens,
            },
        ),
    )
    return str(resp.get("message", {}).get("content", ""))


def _generate_one_openrouter(question: str, context: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=_build_messages(question, context),  # type: ignore[arg-type]
        temperature=settings.entropy_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    return resp.choices[0].message.content or ""


def _generate_samples(provider: str, question: str, context: str, model: str, n: int) -> list[str]:
    """Generates ``n`` samples, tolerating partial failures.

    If an individual call raises, it logs the error and moves on to the next.
    If none of the ``n`` attempts succeed, the last exception is propagated to
    the caller (usually the gate, which decides the fallback).
    """
    sample_fns = {
        "groq": _generate_one_groq,
        "ollama": _generate_one_ollama,
        "openrouter": _generate_one_openrouter,
    }
    fn = sample_fns[provider]

    samples: list[str] = []
    last_exc: Exception | None = None
    for index in range(n):
        try:
            samples.append(fn(question, context, model))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "verification.entropy.sample_failure",
                extra={"provider": provider, "index": index, "error": str(exc)},
            )

    if not samples and last_exc is not None:
        raise last_exc
    return samples


def _compute_similarity(
    text1: str,
    text2: str,
    cache: dict[str, list[float]] | None = None,
) -> float:
    """Computes cosine similarity between two texts via Ollama embeddings.

    Uses epsilon ``1e-10`` to avoid division by zero on degenerate vectors.
    Accepts an optional ``cache`` dict to reuse embeddings across calls
    (clustering N responses makes N embed calls instead of up to
    ``N*(N-1)`` without the cache).
    """

    def _embed(text: str) -> list[float]:
        if cache is None:
            return embed_text(settings.embed_model, text)
        cached = cache.get(text)
        if cached is None:
            cached = embed_text(settings.embed_model, text)
            cache[text] = cached
        return cached

    vec1 = _embed(text1)
    vec2 = _embed(text2)

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 < _EPSILON or norm2 < _EPSILON:
        return 0.0
    return dot_product / (norm1 * norm2)


def _cluster_responses(responses: list[str], threshold: float = 0.85) -> list[list[str]]:
    """Groups responses by semantic similarity using greedy clustering.

    A local embedding cache (``{text: vec}``) ensures each unique text is
    embedded only once, even with O(N²) clustering across samples.
    """
    if not responses:
        return []

    embedding_cache: dict[str, list[float]] = {}
    clusters: list[list[str]] = []

    for response in responses:
        placed = False
        for cluster in clusters:
            representative = cluster[0]
            if _compute_similarity(response, representative, cache=embedding_cache) >= threshold:
                cluster.append(response)
                placed = True
                break
        if not placed:
            clusters.append([response])

    return clusters


def _shannon_entropy(clusters: list[list[str]], total: int) -> float:
    """Computes normalized Shannon entropy over the cluster distribution."""
    if total == 0 or len(clusters) == 0:
        return 0.0

    entropy = 0.0
    for cluster in clusters:
        p = len(cluster) / total
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(total) if total > 1 else 1.0
    return entropy / max_entropy if max_entropy > 0 else 0.0


def compute_entropy_score(question: str, context: str) -> float:
    """Computes the semantic entropy score for hallucination detection.

    Generates multiple responses to the same question, groups them by semantic
    similarity, and computes Shannon entropy over the cluster distribution.
    High entropy indicates uncertainty/possible hallucination.

    Returns:
        Score in the range [0.0, 1.0]. Returns 0.0 when the provider has no
        API key (logs a warning) or when all samples fail and the caller
        decides to proceed.

    Raises:
        KeyError: If ``settings.verification_provider`` is not in
            :data:`DEFAULT_VERIFICATION_MODELS` (should not happen with the enum).
    """
    provider = str(settings.verification_provider)

    if provider not in DEFAULT_VERIFICATION_MODELS:
        logger.error(
            "verification.entropy.unknown_provider",
            extra={"provider": provider},
        )
        raise ValueError(f"Unknown verification provider: {provider!r}")

    if provider == "groq" and not settings.groq_api_key:
        logger.warning("verification.entropy.missing_api_key", extra={"provider": provider})
        return 0.0
    if provider == "openrouter" and not settings.openrouter_api_key:
        logger.warning("verification.entropy.missing_api_key", extra={"provider": provider})
        return 0.0

    model = settings.verification_chat_model or DEFAULT_VERIFICATION_MODELS[provider]
    samples = _generate_samples(provider, question, context, model, settings.entropy_num_samples)
    clusters = _cluster_responses(samples)
    score = _shannon_entropy(clusters, len(samples))

    return min(max(score, 0.0), 1.0)
