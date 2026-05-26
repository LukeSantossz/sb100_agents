"""Buffer de conversação com janela rolante FIFO."""

from collections import deque

_VALID_ROLES: frozenset[str] = frozenset({"user", "assistant"})


class ConversationBuffer:
    """Buffer de histórico de conversa com comportamento FIFO.

    Usa deque com maxlen para descartar automaticamente os turnos
    mais antigos quando o limite é atingido.
    """

    def __init__(self, maxlen: int = 10):
        """Inicializa o buffer com tamanho máximo.

        Args:
            maxlen: Número máximo de turnos no buffer.
        """
        self._buffer: deque[dict[str, str]] = deque(maxlen=maxlen)

    def add(self, role: str, content: str) -> None:
        """Adiciona um turno ao buffer.

        Args:
            role: Papel do turno (``"user"`` ou ``"assistant"``).
            content: Conteúdo da mensagem (não pode ser vazio ou só whitespace).

        Raises:
            ValueError: Se ``role`` não estiver em ``{"user", "assistant"}`` ou
                se ``content`` for vazio.
        """
        if role not in _VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(_VALID_ROLES)}; got {role!r}")
        if not content or not content.strip():
            raise ValueError("content must be a non-empty string")
        self._buffer.append({"role": role, "content": content})

    def to_messages(self) -> list[dict[str, str]]:
        """Retorna o histórico como lista de mensagens.

        Returns:
            Lista de dicts no formato ``[{"role": ..., "content": ...}]``.
        """
        return [msg.copy() for msg in self._buffer]
