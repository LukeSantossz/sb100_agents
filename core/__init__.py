"""Core module — shared settings and schemas.

This module centralizes the fundamental definitions of the SmartB100 system:

- **Settings**: Environment parameters and system defaults (via Pydantic Settings).
- **Schemas**: Pydantic models defining the public API contract (requests/responses).

Exports:
    settings: Singleton instance of the system settings.
    ExpertiseLevel: Enum of user expertise levels.
    UserProfile: User profile schema.
    ChatRequest: Chat request schema.
    ChatResponse: Chat response schema.
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
