"""Unit tests for memory/conversation.py."""

import unittest

import pytest

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


# ---------------- atomic turns (issue #95) ----------------
#
# The handler appended the question and the answer with two separate `add` calls.
# When the buffer refused the answer, the question was already stored, so the
# history held half a conversation and the request became a 500 after the answer
# had already been generated.


def test_add_turn_appends_both_on_success() -> None:
    buffer = ConversationBuffer(maxlen=10)

    buffer.add_turn("qual a epoca de plantio?", "depende do regime de chuvas")

    assert buffer.to_messages() == [
        {"role": "user", "content": "qual a epoca de plantio?"},
        {"role": "assistant", "content": "depende do regime de chuvas"},
    ]


@pytest.mark.parametrize("answer", ["", "   ", "\n\t"])
def test_add_turn_appends_neither_when_the_answer_is_blank(answer: str) -> None:
    """The defect: the question was stored and the answer was not."""
    buffer = ConversationBuffer(maxlen=10)

    with pytest.raises(ValueError):
        buffer.add_turn("uma pergunta", answer)

    assert buffer.to_messages() == [], "the question was stored without its answer"


@pytest.mark.parametrize("question", ["", "   "])
def test_add_turn_appends_neither_when_the_question_is_blank(question: str) -> None:
    buffer = ConversationBuffer(maxlen=10)

    with pytest.raises(ValueError):
        buffer.add_turn(question, "uma resposta")

    assert buffer.to_messages() == []


def test_add_turn_leaves_earlier_history_untouched_when_it_refuses() -> None:
    """A refused turn must not disturb what was already there."""
    buffer = ConversationBuffer(maxlen=10)
    buffer.add_turn("primeira", "resposta um")

    with pytest.raises(ValueError):
        buffer.add_turn("segunda", "")

    assert [m["content"] for m in buffer.to_messages()] == ["primeira", "resposta um"]
