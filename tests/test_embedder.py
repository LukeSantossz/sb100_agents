import unittest
from unittest.mock import patch

from core.config import settings
from retrieval.embedder import generate_embedding


class TestGenerateEmbedding(unittest.TestCase):
    @patch("retrieval.embedder.embed_text")
    def test_returns_list_float_and_calls_ollama_with_settings_model(self, mock_embed):
        vec = [0.25] * 768
        mock_embed.return_value = vec

        out = generate_embedding("hello")

        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 768)
        self.assertEqual(out, vec)
        mock_embed.assert_called_once_with(settings.embed_model, "hello")

    @patch("retrieval.embedder.embed_text")
    def test_same_input_same_output(self, mock_embed):
        fixed = [1.0, 2.0, 3.0]
        mock_embed.return_value = fixed
        self.assertEqual(generate_embedding("x"), generate_embedding("x"))

    @patch("retrieval.embedder.embed_text")
    def test_empty_string_is_forwarded(self, mock_embed):
        """Empty string is forwarded to embed_text (truncation handles it)."""
        mock_embed.return_value = [0.0] * 768
        out = generate_embedding("")
        self.assertEqual(len(out), 768)
        mock_embed.assert_called_once_with(settings.embed_model, "")

    @patch("retrieval.embedder.embed_text")
    def test_long_string_is_forwarded(self, mock_embed):
        """Long string (10k chars) is forwarded; embed_text truncates at 8192."""
        mock_embed.return_value = [0.5] * 768
        long_text = "a" * 10_000
        out = generate_embedding(long_text)
        self.assertEqual(len(out), 768)
        # embed_text receives the raw text; truncation happens there.
        mock_embed.assert_called_once_with(settings.embed_model, long_text)

    @patch("retrieval.embedder.embed_text")
    def test_unicode_string_is_forwarded(self, mock_embed):
        """Strings with accents/CJK/emojis pass through unchanged to embed_text."""
        mock_embed.return_value = [0.1] * 768
        unicode_text = "Crème brûlée with açaí après la récolte? 🌱 农业"
        out = generate_embedding(unicode_text)
        self.assertEqual(len(out), 768)
        mock_embed.assert_called_once_with(settings.embed_model, unicode_text)


if __name__ == "__main__":
    unittest.main()
