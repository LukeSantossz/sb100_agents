"""
Módulo principal para cálculo de entropia semântica.

Orquestra o pipeline completo de detecção de alucinações:
1. Geração de múltiplas respostas
2. Conversão para embeddings
3. Agrupamento por similaridade
4. Cálculo da entropia
5. Decisão baseada no risco
"""

from typing import Callable, Awaitable
from semantic_entropy.similarity_clustering import similarity_clustering
from semantic_entropy.shannon_entropy import shannon_entropy
from semantic_entropy.response_generator import generate_responses


async def compute_semantic_entropy(
    prompt: str,
    model_call: Callable[[str, float], Awaitable[str]],
    embedding_fn: Callable[[str], list[float]],
    risk_threshold: float = 0.5,
    num_responses: int = 5,
    similarity_threshold: float = 0.7,
    temperature: float = 0.7,
) -> dict:
    """
    Calcula a entropia semântica e retorna uma decisão sobre o risco de alucinação.

    Pipeline completo:
    1. Gera múltiplas respostas do modelo para o mesmo prompt
    2. Converte cada resposta em um vetor de embedding
    3. Agrupa embeddings similares em clusters
    4. Calcula a entropia de Shannon sobre a distribuição dos clusters
    5. Retorna decisão "uncertain" ou "proceed" baseada no índice de risco

    Interpretação do risco:
    - Baixa entropia (próximo de 0): Respostas consistentes, baixo risco
    - Alta entropia (próximo de 1): Respostas divergentes, alto risco de alucinação

    Args:
        prompt: Pergunta ou texto de entrada para o modelo.
        model_call: Função assíncrona para chamar o modelo de linguagem.
                   Assinatura: async def(prompt: str, temperature: float) -> str
        embedding_fn: Função síncrona para converter texto em embedding.
                     Assinatura: def(text: str) -> list[float]
        risk_threshold: Limiar de entropia acima do qual a resposta é abortada (default: 0.5).
        num_responses: Número de respostas a gerar para análise (default: 5).
        similarity_threshold: Limiar de similaridade para clustering (default: 0.7).
        temperature: Temperatura do modelo para geração (default: 0.7).

    Returns:
        Dicionário com:
        - decision: "uncertain" se risco alto, "proceed" se risco aceitável
        - entropy: Valor da entropia normalizada (0.0 a 1.0)
        - response: Resposta selecionada (presente apenas se decision="proceed")
        - num_clusters: Quantidade de clusters formados
        - num_responses: Quantidade de respostas geradas
    """
    responses = await generate_responses(
        prompt=prompt,
        model_call=model_call,
        num_responses=num_responses,
        temperature=temperature,
    )

    embeddings = [embedding_fn(response) for response in responses]

    cluster_frequencies = similarity_clustering(
        embeddings=embeddings,
        threshold=similarity_threshold,
    )

    risk_index = shannon_entropy(cluster_frequencies)

    result = {
        "entropy": round(risk_index, 4),
        "num_clusters": len(cluster_frequencies),
        "num_responses": len(responses),
        "cluster_distribution": cluster_frequencies,
    }

    if risk_index > risk_threshold:
        result["decision"] = "uncertain"
        result["reason"] = "Alta entropia semântica indica possível alucinação"
    else:
        result["decision"] = "proceed"
        result["response"] = responses[0]

    return result


def select_best_response(
    responses: list[str],
    embeddings: list[list[float]],
    cluster_frequencies: list[int],
) -> str:
    """
    Seleciona a melhor resposta baseada no cluster mais populoso.

    Identifica o cluster com mais elementos (maior consenso) e retorna
    a primeira resposta desse cluster como a mais confiável.

    Args:
        responses: Lista de respostas geradas.
        embeddings: Lista de embeddings correspondentes às respostas.
        cluster_frequencies: Frequência de cada cluster.

    Returns:
        A resposta do cluster com maior consenso.
    """
    if not cluster_frequencies:
        return responses[0] if responses else ""

    largest_cluster_idx = cluster_frequencies.index(max(cluster_frequencies))

    current_cluster = 0
    cumulative_count = 0

    for i, _ in enumerate(responses):
        if i >= cumulative_count + cluster_frequencies[current_cluster]:
            cumulative_count += cluster_frequencies[current_cluster]
            current_cluster += 1

        if current_cluster == largest_cluster_idx:
            return responses[i]

    return responses[0]
