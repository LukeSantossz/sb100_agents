"""Conversation buffer with a FIFO rolling window."""

import logging
from collections import deque

logger = logging.getLogger(__name__)

_VALID_ROLES: frozenset[str] = frozenset({"user", "assistant"})


class ConversationBuffer:
    """Conversation history buffer with FIFO behavior.

    Uses a deque with maxlen to automatically discard the oldest
    turns when the limit is reached.
    """

    def __init__(self, maxlen: int = 10):
        """Initialize the buffer with a maximum size.

        Args:
            maxlen: Maximum number of turns in the buffer.
        """
        self._buffer: deque[dict[str, str]] = deque(maxlen=maxlen)

    def add(self, role: str, content: str) -> None:
        """Add a turn to the buffer.

        Args:
            role: Turn role (``"user"`` or ``"assistant"``).
            content: Message content (must not be empty or whitespace-only).

        Raises:
            ValueError: If ``role`` is not in ``{"user", "assistant"}`` or
                if ``content`` is empty.
        """
        if role not in _VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(_VALID_ROLES)}; got {role!r}")
        if not content or not content.strip():
            raise ValueError("content must be a non-empty string")
        self._buffer.append({"role": role, "content": content})
        logger.debug("memory.conversation.add", extra={"role": role, "size": len(self._buffer)})

    def add_turn(self, question: str, answer: str) -> None:
        """Append a user question and its answer, or neither.

        The two halves used to be appended by separate ``add`` calls, so an answer
        the buffer rejected left the question stored on its own and the history
        held half a conversation (#95). Both are validated before either is
        appended, which is an invariant of the buffer rather than of whoever
        happens to be writing to it.

        Args:
            question: The user's message.
            answer: The assistant's reply.

        Raises:
            ValueError: If either is empty or whitespace-only. Nothing is appended.
        """
        for role, content in (("user", question), ("assistant", answer)):
            if not content or not content.strip():
                raise ValueError(f"{role} content must be a non-empty string")
        self.add("user", question)
        self.add("assistant", answer)

    def to_messages(self) -> list[dict[str, str]]:
        """Return the history as a list of messages.

        Returns:
            List of dicts in the ``[{"role": ..., "content": ...}]`` format.
        """
        return [msg.copy() for msg in self._buffer]
