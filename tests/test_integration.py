"""Testes de integração end-to-end do pipeline RAG."""

import pytest
from unittest.mock import patch
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
        "session_id": f"test-expertise-{expertise.value}",
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


@pytest.fixture
def mock_generate_captures_history():
    """Mock de generate que captura e valida histórico."""
    captured_histories = []

    def _generate(question, context, history, profile):
        captured_histories.append(list(history))
        return f"Resposta para: {question}"

    with patch("api.routes.chat.generate") as mock:
        mock.side_effect = _generate
        mock.captured_histories = captured_histories
        yield mock


def test_multiturn_session_maintains_context(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_captures_history,
):
    """Sessão com 3 turnos consecutivos mantém contexto ao longo dos turnos."""
    session_id = "test-multiturn-session"
    questions = [
        "Qual o pH ideal do solo?",
        "E como faço a correção?",
        "Quanto tempo antes do plantio?",
    ]

    for question in questions:
        payload = {
            "session_id": session_id,
            "question": question,
            "profile": {"name": "TestUser", "expertise": "beginner"},
        }

        response = client.post("/chat", json=payload)

        assert response.status_code == 200

    # Verificar histórico crescente
    histories = mock_generate_captures_history.captured_histories

    # Turno 1: histórico vazio
    assert len(histories[0]) == 0

    # Turno 2: histórico com 2 mensagens (user + assistant do turno 1)
    assert len(histories[1]) == 2
    assert histories[1][0]["role"] == "user"
    assert histories[1][1]["role"] == "assistant"

    # Turno 3: histórico com 4 mensagens (turnos 1 e 2)
    assert len(histories[2]) == 4


@pytest.fixture
def mock_verification_enabled():
    """Mock que habilita verificação com score fixo."""
    with patch("api.routes.chat.settings") as mock_settings:
        mock_settings.verification_enabled = True
        mock_settings.buffer_maxlen = 10

        with patch("api.routes.chat.verify_and_generate") as mock_verify:
            mock_verify.return_value = ChatResponse(
                answer="Resposta verificada",
                hallucination_score=0.25,
            )
            yield mock_verify


def test_hallucination_score_present_and_valid(
    client,
    mock_embedding,
    mock_context,
    mock_verification_enabled,
):
    """hallucination_score presente e entre 0.0 e 1.0 em todas as respostas."""
    payload = {
        "session_id": "test-score",
        "question": "Como corrigir acidez do solo?",
        "profile": {"name": "TestUser", "expertise": "beginner"},
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "hallucination_score" in data
    assert 0.0 <= data["hallucination_score"] <= 1.0


def test_hallucination_score_zero_when_verification_disabled(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_by_expertise,
):
    """hallucination_score é 0.0 quando verificação está desabilitada."""
    payload = {
        "session_id": "test-score-disabled",
        "question": "Como corrigir acidez do solo?",
        "profile": {"name": "TestUser", "expertise": "beginner"},
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["hallucination_score"] == 0.0


def test_nominal_flow_no_500_errors(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_by_expertise,
):
    """Fluxo nominal completo não produz HTTP 500."""
    payloads = [
        {
            "session_id": "nominal-1",
            "question": "Qual o pH ideal?",
            "profile": {"name": "User1", "expertise": "beginner"},
        },
        {
            "session_id": "nominal-1",
            "question": "Como aplicar calcário?",
            "profile": {"name": "User1", "expertise": "beginner"},
        },
        {
            "session_id": "nominal-2",
            "question": "Dosagem de calcário?",
            "profile": {"name": "User2", "expertise": "expert"},
        },
    ]

    for payload in payloads:
        response = client.post("/chat", json=payload)
        assert response.status_code != 500, f"HTTP 500 em payload: {payload}"
        assert response.status_code == 200
