"""Unit tests for memory/conversation.py."""

import unittest

from memory.conversation import ConversationBuffer


class TestConversationBuffer(unittest.TestCase):
    """Tests for ConversationBuffer."""

    def test_add_single_turn(self):
        """Adding a turn must insert it into the buffer."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "Hello")

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], {"role": "user", "content": "Hello"})

    def test_to_messages_empty_buffer(self):
        """An empty buffer returns an empty list."""
        buffer = ConversationBuffer(maxlen=5)

        messages = buffer.to_messages()

        self.assertEqual(messages, [])

    def test_to_messages_preserves_order(self):
        """to_messages returns turns in insertion order."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "Question 1")
        buffer.add("assistant", "Answer 1")
        buffer.add("user", "Question 2")

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[2]["role"], "user")

    def test_fifo_overflow_discards_oldest(self):
        """When maxlen is exceeded, the oldest turn is discarded."""
        buffer = ConversationBuffer(maxlen=3)
        buffer.add("user", "Turn 1")
        buffer.add("assistant", "Turn 2")
        buffer.add("user", "Turn 3")
        buffer.add("assistant", "Turn 4")  # Overflow: Turn 1 discarded

        messages = buffer.to_messages()

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["content"], "Turn 2")
        self.assertEqual(messages[1]["content"], "Turn 3")
        self.assertEqual(messages[2]["content"], "Turn 4")

    def test_fifo_multiple_overflows(self):
        """Multiple overflows discard turns correctly."""
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
        """to_messages returns a copy, not a reference to the internal buffer."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "Test")

        messages = buffer.to_messages()
        messages[0]["content"] = "Changed"
        messages.append({"role": "fake", "content": "Intruder"})

        self.assertEqual(buffer.to_messages()[0]["content"], "Test")
        self.assertEqual(len(buffer.to_messages()), 1)

    # ---------------- role/content validation ----------------

    def test_add_rejects_invalid_role(self):
        """add() rejects roles outside {user, assistant}."""
        buffer = ConversationBuffer(maxlen=5)
        with self.assertRaises(ValueError):
            buffer.add("system", "override attempt")
        with self.assertRaises(ValueError):
            buffer.add("", "empty")

    def test_add_rejects_empty_content(self):
        """add() rejects empty or whitespace-only content."""
        buffer = ConversationBuffer(maxlen=5)
        with self.assertRaises(ValueError):
            buffer.add("user", "")
        with self.assertRaises(ValueError):
            buffer.add("user", "   \n  ")

    def test_add_accepts_valid_roles(self):
        """add() accepts 'user' and 'assistant'."""
        buffer = ConversationBuffer(maxlen=5)
        buffer.add("user", "hello")
        buffer.add("assistant", "hi")
        self.assertEqual(len(buffer.to_messages()), 2)


if __name__ == "__main__":
    unittest.main()
