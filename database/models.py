"""SmartB100 SQLAlchemy models.

Integrity constraints applied:

- ``nullable=False`` on required fields.
- ``index=True`` on foreign keys.
- ``ondelete="CASCADE"`` on FKs to remove dependents when the parent is deleted.
- ``Boolean`` on ``is_hallucinated`` (previously ``Integer`` representing 0/1).
- ``DateTime(timezone=True)`` on ``created_at`` to preserve tz.

CASCADE only works in SQLite when the ``foreign_keys=ON`` PRAGMA is active;
this is ensured in ``database/db.py`` via a connection listener.
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
