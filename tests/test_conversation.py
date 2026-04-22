"""Testes unitários para memory/conversation.py."""

import unittest

from memory.conversation import ConversationBuffer


class TestConversationBuffer(unittest.TestCase):
    """Testes para ConversationBuffer."""

    def test_add_single_turn(self):
        """Adicionar um turno deve inserir no buffer."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "Olá")

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], {"role": "user", "content": "Olá"})

    def test_to_messages_empty_buffer(self):
        """Buffer vazio retorna lista vazia."""
        buffer = ConversationBuffer(maxlen=5)

        messages = buffer.to_messages()

        self.assertEqual(messages, [])

    def test_to_messages_preserves_order(self):
        """to_messages retorna turnos na ordem de inserção."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "Pergunta 1")
        buffer.add("assistant", "Resposta 1")
        buffer.add("user", "Pergunta 2")

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[2]["role"], "user")

    def test_fifo_overflow_discards_oldest(self):
        """Ao exceder maxlen, o turno mais antigo é descartado."""
        buffer = ConversationBuffer(maxlen=3)
        buffer.add("user", "Turno 1")
        buffer.add("assistant", "Turno 2")
        buffer.add("user", "Turno 3")
        buffer.add("assistant", "Turno 4")  # Overflow: Turno 1 descartado

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["content"], "Turno 2")
        self.assertEqual(messages[1]["content"], "Turno 3")
        self.assertEqual(messages[2]["content"], "Turno 4")

    def test_fifo_multiple_overflows(self):
        """Múltiplos overflows descartam turnos corretamente."""
        buffer = ConversationBuffer(maxlen=2)
        buffer.add("user", "A")
        buffer.add("assistant", "B")
        buffer.add("user", "C")
        buffer.add("assistant", "D")
        buffer.add("user", "E")

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "D")
        self.assertEqual(messages[1]["content"], "E")

    def test_to_messages_returns_copy(self):
        """to_messages retorna cópia, não referência ao buffer interno."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "Teste")

        messages = buffer.to_messages()
        messages.append({"role": "fake", "content": "Intruso"})

        self.assertEqual(len(buffer.to_messages()), 1)


if __name__ == "__main__":
    unittest.main()
