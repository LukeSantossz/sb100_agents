"""
Módulo para agrupamento de embeddings por similaridade de cosseno (Palavras Parecidas em termos simples).

Agrupa vetores de embedding em clusters baseando-se na similaridade
de cosseno. Vetores similares (acima do threshold) são agrupados juntos.
"""

import numpy as np
from numpy.linalg import norm


def cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    """
    Calcula a similaridade de cosseno entre dois vetores.

    A similaridade de cosseno mede o ângulo entre dois vetores,
    retornando um valor entre -1 e 1, onde 1 significa vetores idênticos.

    Args:
        vector_a: Primeiro vetor numpy.
        vector_b: Segundo vetor numpy.

    Returns:
        Valor de similaridade entre -1.0 e 1.0.
    """
    norm_a = norm(vector_a)
    norm_b = norm(vector_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return np.dot(vector_a, vector_b) / (norm_a * norm_b)


def similarity_clustering(
    embeddings: list[list[float]], threshold: float = 0.7
) -> list[int]:
    """
    Agrupa embeddings em clusters baseado na similaridade de cosseno.

    Utiliza um algoritmo guloso de clustering: cada embedding é comparado
    com o primeiro elemento de cada cluster existente. Se a similaridade
    excede o threshold, o embedding é adicionado ao cluster; caso contrário,
    um novo cluster é criado.

    Args:
        embeddings: Lista de vetores de embedding (cada embedding é uma lista de floats).
        threshold: Limiar mínimo de similaridade para agrupar (default: 0.7).

    Returns:
        Lista com a frequência (quantidade de elementos) de cada cluster.
        Ex: [5, 2, 1] indica 3 clusters com 5, 2 e 1 embeddings respectivamente.
    """
    if not embeddings:
        return []

    clusters: list[list[np.ndarray]] = []

    for embedding in embeddings:
        vector = np.array(embedding)
        assigned_to_cluster = False

        for cluster in clusters:
            cluster_representative = cluster[0]
            similarity = cosine_similarity(vector, cluster_representative)

            if similarity >= threshold:
                cluster.append(vector)
                assigned_to_cluster = True
                break

        if not assigned_to_cluster:
            clusters.append([vector])

    cluster_frequencies = [len(cluster) for cluster in clusters]
    return cluster_frequencies
