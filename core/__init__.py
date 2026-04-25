"""Módulo core — configurações e schemas compartilhados.

Este módulo centraliza as definições fundamentais do sistema SmartB100:

- **Configurações**: Parâmetros de ambiente e defaults do sistema (via Pydantic Settings).
- **Schemas**: Modelos Pydantic que definem o contrato público da API (requests/responses).

Exports:
    settings: Instância singleton das configurações do sistema.
    ExpertiseLevel: Enum com níveis de expertise do usuário.
    UserProfile: Schema do perfil do usuário.
    ChatRequest: Schema de requisição de chat.
    ChatResponse: Schema de resposta de chat.
"""

from core.config import settings
from core.schemas import ChatRequest, ChatResponse, ExpertiseLevel, UserProfile

__all__ = [
    "settings",
    "ExpertiseLevel",
    "UserProfile",
    "ChatRequest",
    "ChatResponse",
]
