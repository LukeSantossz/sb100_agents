"""Health check endpoint for monitoring.

Exposes a simple endpoint to check API availability.
Used by load balancers, Kubernetes probes and monitoring.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the API health status.

    Lightweight endpoint for availability checks.
    Does not check dependencies (Ollama, Qdrant) to avoid overhead.

    Returns:
        Dict with status "ok" indicating the API is responding.
    """
    return {"status": "ok"}
