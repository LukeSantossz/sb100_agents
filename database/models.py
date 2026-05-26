"""Modelos SQLAlchemy do SmartB100.

Reforço de integridade aplicado em TASK-T63:

- ``nullable=False`` em campos obrigatórios.
- ``index=True`` em foreign keys.
- ``ondelete="CASCADE"`` em FKs para limpar dependentes ao remover o pai.
- ``Boolean`` em ``is_hallucinated`` (antes ``Integer`` representando 0/1).
- ``DateTime(timezone=True)`` em ``created_at`` para preservar tz.

CASCADE só funciona em SQLite quando o PRAGMA ``foreign_keys=ON`` está ativo;
isso é garantido em ``database/db.py`` via listener de conexão.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


def _utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title = Column(String(255), default="New Conversation", nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role = Column(String(50), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    is_hallucinated = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
