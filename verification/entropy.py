"""Cálculo de entropia semântica para detecção de alucinações.

Referência: Semantic Uncertainty (Farquhar et al., 2023)
https://arxiv.org/abs/2302.09664
"""

import math

from openai import OpenAI

from core.config import settings

NUM_SAMPLES = 5
TEMPERATURE = 0.7


def _generate_samples(question: str, context: str, n: int = NUM_SAMPLES) -> list[str]:
    """Gera N respostas para a mesma pergunta com temperatura > 0.

    Custo: N chamadas sequenciais à API (gpt-4o-mini ~$0.15/1M tokens).
    Otimização futura: usar `n` parameter da API para gerar múltiplas em uma chamada.
    """
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = f"Contexto:\n{context}\n\nPergunta: {question}" if context else question

    responses = []
    for _ in range(n):
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em agronomia. Responda de forma concisa.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=256,
        )
        responses.append(completion.choices[0].message.content or "")

    return responses


def _compute_similarity(text1: str, text2: str) -> float:
    """Calcula similaridade semântica entre dois textos usando embeddings."""
    client = OpenAI(api_key=settings.openai_api_key)

    embeddings = client.embeddings.create(
        model="text-embedding-3-small",
        input=[text1, text2],
    )

    vec1 = embeddings.data[0].embedding
    vec2 = embeddings.data[1].embedding

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0


def _cluster_responses(responses: list[str], threshold: float = 0.85) -> list[list[str]]:
    """Agrupa respostas por similaridade semântica.

    Complexidade: O(n*k) onde n=respostas e k=clusters. No pior caso O(n²).
    Para NUM_SAMPLES=5, são no máximo 10 chamadas de embedding.

    Otimização futura: batch embeddings e usar matriz de similaridade.
    """
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

    Args:
        question: Pergunta original do usuário.
        context: Contexto RAG usado na geração.

    Returns:
        Score entre 0.0 (baixa incerteza) e 1.0 (alta incerteza/possível alucinação).
    """
    if not settings.openai_api_key:
        return 0.0

    samples = _generate_samples(question, context, NUM_SAMPLES)
    clusters = _cluster_responses(samples)
    score = _shannon_entropy(clusters, len(samples))

    return min(max(score, 0.0), 1.0)
