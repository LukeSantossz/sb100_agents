"""Routers da API SmartB100.

Agrupa os routers FastAPI para cada domínio funcional:

- **auth**: Registro e autenticação de usuários (JWT).
- **chat**: Endpoint principal de conversação com RAG.
- **health**: Health check para monitoramento e load balancers.
"""

from api.routes import auth, chat, health

__all__ = ["auth", "chat", "health"]
