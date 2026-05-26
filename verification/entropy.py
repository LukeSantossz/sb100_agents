"""Cálculo de entropia semântica para detecção de alucinações.

Referência: Semantic Uncertainty (Farquhar et al., 2023)
https://arxiv.org/abs/2302.09664

TASK-T64 endurece a estabilidade numérica e o error handling:

- Epsilon ``1e-10`` substitui o teste ``> 0`` na similaridade de cosseno.
- ``logger.warning`` quando provedor selecionado está sem API key.
- Geração de samples tolera falhas parciais (continua) e propaga apenas se todas falharem.
- Acesso seguro a ``resp["message"]["content"]`` via ``.get(...)``.
- Validação do provider contra ``_sample_fns.keys()`` antes do dispatch.
- Temperatura via ``settings.entropy_temperature`` (era constante hardcoded).
"""

import logging
import math
from typing import Any, cast

import ollama

from core.config import settings
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
    """Constrói lista de mensagens para amostragem."""
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
    # ollama-py retorna ChatResponse; cast para dict[str, Any] mantém o acesso
    # seguro via ``.get`` (que continua válido em runtime para ChatResponse).
    # Client com timeout explícito evita hang indefinido se o servidor Ollama estiver indisponível.
    client = ollama.Client(timeout=settings.ollama_timeout)
    resp = cast(
        dict[str, Any],
        client.chat(
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
    """Gera ``n`` samples tolerando falhas parciais.

    Se uma chamada individual levantar exceção, segue para a próxima e registra
    o erro. Se nenhuma das ``n`` tentativas tiver sucesso, propaga a última
    exceção para o caller (em geral o gate, que decide o fallback).
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
    """Calcula similaridade de cosseno entre dois textos via embeddings Ollama.

    Usa epsilon ``1e-10`` para evitar divisão por zero em vetores degenerados.
    Aceita um dicionário ``cache`` opcional para reutilizar embeddings entre
    chamadas (TASK-T68: clustering de N respostas faz N embed calls em vez de
    até ``N*(N-1)`` sem cache).
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
    """Agrupa respostas por similaridade semântica usando clustering guloso.

    Cache local de embeddings (``{text: vec}``) garante que cada texto único
    seja embedded apenas uma vez, mesmo em clustering O(N²) entre samples.
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
    """Calcula entropia de Shannon normalizada sobre a distribuição de clusters."""
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
    """Calcula score de entropia semântica para detecção de alucinações.

    Gera múltiplas respostas para a mesma pergunta, agrupa por similaridade
    semântica e calcula entropia de Shannon sobre a distribuição dos clusters.
    Alta entropia indica incerteza/possível alucinação.

    Returns:
        Score no intervalo [0.0, 1.0]. Retorna 0.0 quando o provider está sem
        API key (loga warning) ou quando todas as amostras falham e o caller
        decidir prosseguir.

    Raises:
        KeyError: Se ``settings.verification_provider`` não estiver em
            :data:`DEFAULT_VERIFICATION_MODELS` (não deve acontecer com o enum).
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
