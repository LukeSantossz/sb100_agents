"""Health check endpoint para monitoramento.

Expõe endpoint simples para verificação de disponibilidade da API.
Usado por load balancers, Kubernetes probes e monitoramento.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Retorna status de saúde da API.

    Endpoint leve para verificação de disponibilidade.
    Não verifica dependências (Ollama, Qdrant) para evitar overhead.

    Returns:
        Dict com status "ok" indicando que a API está respondendo.
    """
    return {"status": "ok"}
