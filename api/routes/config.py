"""Page configuration endpoint.

The web app runs in the browser, so it cannot import ``Settings`` the way the
old Gradio page did in its own Python process. This endpoint hands it exactly the two values
it needs, read at request time so they always match what the API itself uses.
Neither is a secret, so no token is required.
"""

from fastapi import APIRouter

from core.config import settings

router = APIRouter(tags=["config"])


@router.get("/config")
async def config() -> dict[str, float]:
    """Return the values the web app needs from ``Settings``.

    Returns:
        ``hallucination_threshold``, which sets the score bands the page shows, and
        ``chat_timeout``, how many seconds the page waits for ``POST /chat``.
    """
    return {
        "hallucination_threshold": settings.hallucination_threshold,
        "chat_timeout": settings.chat_timeout,
    }
