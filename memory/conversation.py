"""Buffer de conversação com janela rolante FIFO."""

from collections import deque


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
        self._buffer: deque[dict] = deque(maxlen=maxlen)

    def add(self, role: str, content: str) -> None:
        """Adiciona um turno ao buffer.

        Args:
            role: Papel do turno ("user" ou "assistant").
            content: Conteúdo da mensagem.
        """
        self._buffer.append({"role": role, "content": content})

    def to_messages(self) -> list[dict]:
        """Retorna o histórico como lista de mensagens.

        Returns:
            Lista de dicts no formato [{"role": ..., "content": ...}].
        """
        return [msg.copy() for msg in self._buffer]
