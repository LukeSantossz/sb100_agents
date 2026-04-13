import unittest
from unittest.mock import patch

from core.config import settings
from retrieval.embedder import generate_embedding


class TestGenerateEmbedding(unittest.TestCase):
    @patch("retrieval.embedder.ollama.embeddings")
    def test_returns_list_float_and_calls_ollama_with_settings_model(self, mock_embeddings):
        vec = [0.25] * 768
        mock_embeddings.return_value = {"embedding": vec}

        out = generate_embedding("hello")

        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 768)
        self.assertEqual(out, vec)
        mock_embeddings.assert_called_once_with(
            model=settings.embed_model,
            prompt="hello",
        )

    @patch("retrieval.embedder.ollama.embeddings")
    def test_same_input_same_output(self, mock_embeddings):
        fixed = [1.0, 2.0, 3.0]
        mock_embeddings.return_value = {"embedding": fixed}
        self.assertEqual(generate_embedding("x"), generate_embedding("x"))


if __name__ == "__main__":
    unittest.main()
