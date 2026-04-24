"""Testes de integração end-to-end do pipeline RAG."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from core.schemas import ChatResponse, ExpertiseLevel


@pytest.fixture
def client():
    """TestClient do FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_embedding():
    """Mock de generate_embedding retornando vetor sintético."""
    with patch("api.routes.chat.generate_embedding") as mock:
        mock.return_value = [0.1] * 768
        yield mock


@pytest.fixture
def mock_context():
    """Mock de search_context retornando chunks fixos."""
    with patch("api.routes.chat.search_context") as mock:
        mock.return_value = [
            "Chunk 1: Informação sobre calagem e correção de acidez do solo.",
            "Chunk 2: A aplicação de calcário deve ser feita 60-90 dias antes do plantio.",
        ]
        yield mock


@pytest.fixture
def mock_verification_disabled():
    """Mock que desabilita verificação de alucinação."""
    with patch("api.routes.chat.settings") as mock_settings:
        mock_settings.verification_enabled = False
        mock_settings.buffer_maxlen = 10
        yield mock_settings
