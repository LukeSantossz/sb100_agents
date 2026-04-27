"""Cálculo de entropia semântica para detecção de alucinações.

Referência: Semantic Uncertainty (Farquhar et al., 2023)
https://arxiv.org/abs/2302.09664
"""

import math

import ollama

from core.config import settings
from retrieval.ollama_embeddings import embed_text

TEMPERATURE = 0.7

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


def _generate_samples_groq(question: str, context: str, model: str, n: int) -> list[str]:
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    messages = _build_messages(question, context)
    samples = []
    for _ in range(n):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=settings.llm_max_tokens,
        )
        samples.append(resp.choices[0].message.content or "")
    return samples


def _generate_samples_ollama(question: str, context: str, model: str, n: int) -> list[str]:
    messages = _build_messages(question, context)
    samples = []
    for _ in range(n):
        resp = ollama.chat(
            model=model,
            messages=messages,
            options={"temperature": TEMPERATURE, "num_predict": settings.llm_max_tokens},
        )
        samples.append(str(resp["message"]["content"]))
    return samples


def _generate_samples_openrouter(question: str, context: str, model: str, n: int) -> list[str]:
    from openai import OpenAI

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)
    messages = _build_messages(question, context)
    samples = []
    for _ in range(n):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=settings.llm_max_tokens,
        )
        samples.append(resp.choices[0].message.content or "")
    return samples


_sample_fns = {
    "groq": _generate_samples_groq,
    "ollama": _generate_samples_ollama,
    "openrouter": _generate_samples_openrouter,
}


def _compute_similarity(text1: str, text2: str) -> float:
    """Calcula similaridade de cosseno entre dois textos via embeddings Ollama."""
    vec1 = embed_text(settings.embed_model, text1)
    vec2 = embed_text(settings.embed_model, text2)

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0


def _cluster_responses(responses: list[str], threshold: float = 0.85) -> list[list[str]]:
    """Agrupa respostas por similaridade semântica usando clustering guloso."""
    if not responses:
        return []

    clusters: list[list[str]] = []

    for response in responses:
        placed = False
        for cluster in clusters:
            representative = cluster[0]
            if _compute_similarity(response, representative) >= threshold:
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
    """
    provider = settings.verification_provider

    if provider == "groq" and not settings.groq_api_key:
        return 0.0
    if provider == "openrouter" and not settings.openrouter_api_key:
        return 0.0

    model = settings.verification_chat_model or DEFAULT_VERIFICATION_MODELS[provider]
    sample_fn = _sample_fns[provider]
    samples = sample_fn(question, context, model, settings.entropy_num_samples)
    clusters = _cluster_responses(samples)
    score = _shannon_entropy(clusters, len(samples))

    return min(max(score, 0.0), 1.0)
