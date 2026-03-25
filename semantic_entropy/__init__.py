"""
Semantic Entropy - Módulo para detecção de alucinações em LLMs.

Este módulo na TEORIA implementa o cálculo de entropia semântica para avaliar
a consistência das respostas de um modelo de linguagem, ajudando a
identificar potenciais alucinações.

Pipeline:
1. Gerar múltiplas respostas para a mesma pergunta
2. Converter respostas em embeddings vetoriais
3. Agrupar embeddings por similaridade de cosseno (Palavras Parecidas em termos simples)
4. Calcular entropia de Shannon sobre a distribuição dos clusters
5. Retornar decisão baseada no índice de risco
"""

from semantic_entropy.compute_entropy import compute_semantic_entropy
from semantic_entropy.shannon_entropy import shannon_entropy
from semantic_entropy.similarity_clustering import similarity_clustering
from semantic_entropy.response_generator import generate_responses

__all__ = [
    "compute_semantic_entropy",
    "shannon_entropy",
    "similarity_clustering",
    "generate_responses",
]
