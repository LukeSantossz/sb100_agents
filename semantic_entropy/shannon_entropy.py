"""
Módulo para cálculo da entropia de Shannon.

A entropia de Shannon mede a incerteza ou aleatoriedade de uma distribuição.
No contexto de detecção de alucinações, alta entropia indica respostas
inconsistentes (maior probabilidade de alucinação).
"""

import math


def shannon_entropy(cluster_frequencies: list[int]) -> float:
    """
    Calcula a entropia de Shannon normalizada para uma distribuição de frequências.

    A entropia é normalizada pelo log2 do número de clusters para retornar
    um valor entre 0 e 1, onde:
    - 0 = todas as respostas no mesmo cluster (alta consistência)
    - 1 = respostas uniformemente distribuídas (alta incerteza/alucinação)

    Args:
        cluster_frequencies: Lista com a contagem de elementos em cada cluster.
                            Ex: [5, 2, 1] significa 3 clusters com 5, 2 e 1 elementos.

    Returns:
        Entropia normalizada entre 0.0 e 1.0.
    """
    total = sum(cluster_frequencies)
    num_clusters = len(cluster_frequencies)

    if total == 0 or num_clusters <= 1:
        return 0.0

    entropy = 0.0
    for frequency in cluster_frequencies:
        if frequency > 0:
            probability = frequency / total
            entropy -= probability * math.log2(probability)

    max_entropy = math.log2(num_clusters)
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    return normalized_entropy
