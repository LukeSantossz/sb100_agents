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


@pytest.fixture
def mock_generate_by_expertise():
    """Mock de generate que retorna respostas distintas por expertise."""
    def _generate(question, context, history, profile):
        responses = {
            ExpertiseLevel.beginner: "Resposta simples para iniciante sobre calagem.",
            ExpertiseLevel.intermediate: "Resposta técnica intermediária: calcário dolomítico, PRNT 85%.",
            ExpertiseLevel.expert: "Resposta avançada: CTC, V%, saturação de bases, dosagem 2t/ha.",
        }
        return responses.get(profile.expertise, "Resposta padrão")

    with patch("api.routes.chat.generate") as mock:
        mock.side_effect = _generate
        yield mock


@pytest.mark.parametrize("expertise,expected_keyword", [
    (ExpertiseLevel.beginner, "simples"),
    (ExpertiseLevel.intermediate, "técnica"),
    (ExpertiseLevel.expert, "avançada"),
])
def test_expertise_levels_produce_distinct_responses(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_by_expertise,
    expertise,
    expected_keyword,
):
    """3 perfis de expertise produzem respostas visivelmente distintas."""
    payload = {
        "session_id": "test-expertise",
        "question": "Como corrigir acidez do solo?",
        "profile": {
            "name": "TestUser",
            "expertise": expertise.value,
        },
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert expected_keyword in data["answer"].lower()
    assert "hallucination_score" in data
