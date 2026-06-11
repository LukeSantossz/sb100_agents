"""SmartB100 API routers.

Groups the FastAPI routers by functional domain:

- **auth**: User registration and authentication (JWT).
- **chat**: Main conversation endpoint with RAG.
- **health**: Health check for monitoring and load balancers.
"""

from api.routes import auth, chat, health

__all__ = ["auth", "chat", "health"]
