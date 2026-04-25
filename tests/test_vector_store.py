import unittest
from unittest.mock import MagicMock, patch

from core.config import settings
from retrieval.vector_store import search_context


class TestSearchContext(unittest.TestCase):
    @patch("retrieval.vector_store.QdrantClient")
    def test_returns_list_str_with_top_k_elements(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        points = []
        for i in range(settings.top_k):
            p = MagicMock()
            p.payload = {"text": f"chunk-{i}"}
            points.append(p)
        mock_client.query_points.return_value = MagicMock(points=points)

        embedding = [0.1] * 768
        out = search_context(embedding)

        self.assertIsInstance(out, list)
        self.assertEqual(len(out), settings.top_k)
        self.assertEqual(out, [f"chunk-{i}" for i in range(settings.top_k)])
        mock_client.query_points.assert_called_once_with(
            collection_name=settings.collection_name,
            query=embedding,
            limit=settings.top_k,
            with_payload=True,
        )
        mock_client_cls.assert_called_once_with(url=settings.qdrant_url)

    @patch("retrieval.vector_store.QdrantClient")
    def test_missing_text_payload_returns_empty_string(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        p = MagicMock()
        p.payload = {}
        mock_client.query_points.return_value = MagicMock(points=[p])

        out = search_context([0.0])

        self.assertEqual(out, [""])


if __name__ == "__main__":
    unittest.main()
