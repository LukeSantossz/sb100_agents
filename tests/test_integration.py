"""End-to-end integration tests for the database-backed RAG pipeline."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import verify_token
from api.main import app
from core.config import settings
from core.schemas import ChatResponse, ExpertiseLevel
from database.db import Base, get_db
from database.models import Conversation, Message, User


def _override_verify_token() -> User:
    """JWT gate stub for integration — returns a fixed user without hitting the DB."""
    return User(
        id=1,
        username="testuser",
        hashed_password="x",
        created_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def db_setup() -> Generator[None, None, None]:
    """In-memory SQLite database setup, populated with test users."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed users into the in-memory database
    db = TestingSessionLocal()
    try:
        # Default test user
        user = User(
            id=1,
            username="testuser",
            hashed_password="x",
            created_at=datetime.now(UTC),
        )
        # Users for isolation tests
        alice = User(
            id=10,
            username="alice",
            hashed_password="x",
            created_at=datetime.now(UTC),
        )
        bob = User(
            id=20,
            username="bob",
            hashed_password="x",
            created_at=datetime.now(UTC),
        )
        db.add(user)
        db.add(alice)
        db.add(bob)
        db.commit()
    finally:
        db.close()

    def _get_testing_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_testing_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client():
    """FastAPI TestClient with the JWT gate mocked via dependency override."""
    app.dependency_overrides[verify_token] = _override_verify_token
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mock_embedding():
    """Mock of generate_embedding returning a synthetic vector."""
    with patch("api.routes.chat.generate_embedding") as mock:
        mock.return_value = [0.1] * 768
        yield mock


@pytest.fixture
def mock_context():
    """Mock of search_context returning fixed chunks."""
    with patch("api.routes.chat.search_context") as mock:
        mock.return_value = [
            "Chunk 1: Information about liming and soil acidity correction.",
            "Chunk 2: Lime must be applied 60-90 days before planting.",
        ]
        yield mock


@pytest.fixture
def mock_verification_disabled(monkeypatch):
    """Mock that disables hallucination verification."""
    monkeypatch.setattr(settings, "verification_enabled", False)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)
    monkeypatch.setattr(settings, "agent_enabled", False)
    yield settings


@pytest.fixture
def mock_generate_by_expertise():
    """Mock of generate that returns distinct answers per expertise."""

    def _generate(question, context, history, profile):
        responses = {
            ExpertiseLevel.beginner: "Simple answer for a beginner about liming.",
            ExpertiseLevel.intermediate: "Technical intermediate answer: dolomitic lime, PRNT 85%.",
            ExpertiseLevel.expert: "Advanced answer: CEC, V%, base saturation, 2t/ha dosage.",
        }
        return responses.get(profile.expertise, "Default answer")

    with patch("api.routes.chat.generate") as mock:
        mock.side_effect = _generate
        yield mock


@pytest.mark.parametrize(
    "expertise,expected_keyword",
    [
        (ExpertiseLevel.beginner, "simple"),
        (ExpertiseLevel.intermediate, "technical"),
        (ExpertiseLevel.expert, "advanced"),
    ],
)
def test_expertise_levels_produce_distinct_responses(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_by_expertise,
    expertise,
    expected_keyword,
):
    """3 expertise profiles produce visibly distinct answers."""
    with patch("api.routes.chat.classify_expertise_llm", return_value=expertise):
        payload = {
            "conversation_id": None,
            "question": "How to correct soil acidity?",
        }
        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert expected_keyword in data["answer"].lower()
    assert "hallucination_score" in data


@pytest.fixture
def mock_generate_captures_history():
    """Mock of generate that captures and validates the history."""
    captured_histories = []

    def _generate(question, context, history, profile):
        captured_histories.append(list(history))
        return f"Answer to: {question}"

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
    """A session with 3 consecutive turns keeps context across turns."""
    questions = [
        "What is the ideal soil pH?",
        "And how do I correct it?",
        "How long before planting?",
    ]

    conversation_id = None
    for question in questions:
        payload = {
            "conversation_id": conversation_id,
            "question": question,
        }

        response = client.post("/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        conversation_id = data["conversation_id"]

    # Check the growing history
    histories = mock_generate_captures_history.captured_histories

    # Turn 1: empty history
    assert len(histories[0]) == 0

    # Turn 2: history with 2 messages (user + assistant from turn 1)
    assert len(histories[1]) == 2
    assert histories[1][0]["role"] == "user"
    assert histories[1][1]["role"] == "assistant"

    # Turn 3: history with 4 messages (turns 1 and 2)
    assert len(histories[2]) == 4


@pytest.fixture
def mock_verification_enabled(monkeypatch):
    """Mock that enables verification with a fixed score."""
    monkeypatch.setattr(settings, "verification_enabled", True)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)
    monkeypatch.setattr(settings, "agent_enabled", False)

    with patch("api.routes.chat.verify_and_generate") as mock_verify:
        mock_verify.return_value = ChatResponse(
            answer="Verified answer",
            conversation_id=1,
            hallucination_score=0.25,
        )
        yield mock_verify


def test_hallucination_score_present_and_valid(
    client,
    mock_embedding,
    mock_context,
    mock_verification_enabled,
):
    """hallucination_score is present and between 0.0 and 1.0 in every answer."""
    payload = {
        "conversation_id": None,
        "question": "How to correct soil acidity?",
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
    """hallucination_score is 0.0 when verification is disabled."""
    payload = {
        "conversation_id": None,
        "question": "How to correct soil acidity?",
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
    """The full nominal flow does not produce HTTP 500."""
    response1 = client.post("/chat", json={"conversation_id": None, "question": "What is the ideal pH?"})
    assert response1.status_code == 200
    conv_id = response1.json()["conversation_id"]

    response2 = client.post("/chat", json={"conversation_id": conv_id, "question": "How to apply lime?"})
    assert response2.status_code == 200

    response3 = client.post("/chat", json={"conversation_id": None, "question": "Lime dosage?"})
    assert response3.status_code == 200


def test_chat_access_log_emits_username_and_conversation_id(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_by_expertise,
    caplog: pytest.LogCaptureFixture,
):
    """The /chat handler emits a structured log with username + conversation_id."""
    payload = {
        "conversation_id": None,
        "question": "ping",
    }

    with caplog.at_level("INFO", logger="api.routes.chat"):
        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    access_records = [r for r in caplog.records if "chat.access" in r.message]
    assert len(access_records) >= 1
    record = access_records[0]
    assert getattr(record, "username", None) == "testuser"
    assert hasattr(record, "conversation_id")


def test_cross_user_conversation_id_does_not_leak_history_via_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Endpoint-level (#108): a second user reusing another user's conversation_id gets HTTP 404."""
    from api.dependencies import limiter
    from api.routes import chat as chat_module

    monkeypatch.setattr(chat_module.settings, "verification_enabled", False)
    monkeypatch.setattr(chat_module, "generate_embedding", lambda _q: [0.1] * 768)
    monkeypatch.setattr(chat_module, "search_context", lambda _emb: ["chunk"])
    monkeypatch.setattr(chat_module, "generate", lambda question, context, history, profile: "response")
    monkeypatch.setattr(chat_module, "classify_domain_llm", lambda q: True)
    monkeypatch.setattr(chat_module, "classify_expertise_llm", lambda q: ExpertiseLevel.intermediate)

    user_a = User(id=10, username="alice", hashed_password="x", created_at=datetime.now(UTC))
    user_b = User(id=20, username="bob", hashed_password="x", created_at=datetime.now(UTC))

    current = {"user": user_a}
    limiter.reset()
    app.dependency_overrides[verify_token] = lambda: current["user"]
    try:
        client = TestClient(app)

        response_alice = client.post(
            "/chat",
            json={"conversation_id": None, "question": "alice-1"},
        )
        assert response_alice.status_code == 200
        alice_conv_id = response_alice.json()["conversation_id"]

        current["user"] = user_b
        response_bob = client.post(
            "/chat",
            json={"conversation_id": alice_conv_id, "question": "bob-1"},
        )
        assert response_bob.status_code == 404
    finally:
        app.dependency_overrides.clear()
        limiter.reset()


@pytest.fixture
def _agent_payload() -> dict[str, object]:
    return {
        "conversation_id": None,
        "question": "When should I plant soybeans in the Midwest?",
    }


def test_chat_agent_path_returns_agent_answer_and_gate_score(client, _agent_payload, monkeypatch):
    from agent.runner import AgentOutcome

    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", False)
    monkeypatch.setattr(settings, "verification_enabled", True)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)

    with (
        patch("api.routes.chat.invoke_agent") as mock_invoke,
        patch("api.routes.chat.score_context", return_value=0.22) as mock_score,
    ):
        mock_invoke.return_value = AgentOutcome(answer="agent answer", context="ctx")
        response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "agent answer"
    assert data["hallucination_score"] == 0.22
    mock_score.assert_called_once()


def test_chat_agent_path_zero_score_when_verification_disabled(client, _agent_payload, monkeypatch):
    from agent.runner import AgentOutcome

    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", False)
    monkeypatch.setattr(settings, "verification_enabled", False)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)

    with (
        patch("api.routes.chat.invoke_agent") as mock_invoke,
        patch("api.routes.chat.score_context") as mock_score,
    ):
        mock_invoke.return_value = AgentOutcome(answer="agent answer", context="ctx")
        response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 200
    assert response.json()["hallucination_score"] == 0.0
    mock_score.assert_not_called()


def test_chat_agent_path_failure_returns_503(client, _agent_payload, monkeypatch):
    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", False)
    monkeypatch.setattr(settings, "verification_enabled", True)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)

    with patch("api.routes.chat.invoke_agent", side_effect=RuntimeError("secret boom")):
        response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 503
    assert "secret boom" in response.json()["detail"]


def test_chat_agent_path_short_circuits_out_of_domain(client, _agent_payload, monkeypatch):
    from agent.intent import OUT_OF_DOMAIN_MESSAGE, DomainDecision

    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", True)
    monkeypatch.setattr(settings, "verification_enabled", False)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)
    monkeypatch.setattr(settings, "intent_threshold", 0.3)

    with (
        patch(
            "api.routes.chat.classify_domain",
            return_value=DomainDecision(in_domain=False, score=0.05),
        ),
        patch("api.routes.chat.invoke_agent") as mock_invoke,
    ):
        response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == OUT_OF_DOMAIN_MESSAGE
    assert data["hallucination_score"] == 0.0
    mock_invoke.assert_not_called()


def test_chat_agent_path_proceeds_when_in_domain(client, _agent_payload, monkeypatch):
    from agent.intent import DomainDecision
    from agent.runner import AgentOutcome

    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", True)
    monkeypatch.setattr(settings, "verification_enabled", False)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)
    monkeypatch.setattr(settings, "intent_threshold", 0.3)

    with (
        patch(
            "api.routes.chat.classify_domain",
            return_value=DomainDecision(in_domain=True, score=0.7),
        ),
        patch("api.routes.chat.invoke_agent") as mock_invoke,
        patch("api.routes.chat.score_context"),
    ):
        mock_invoke.return_value = AgentOutcome(answer="agent answer", context="ctx")
        response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 200
    assert response.json()["answer"] == "agent answer"
    mock_invoke.assert_called_once()


def test_chat_agent_path_intent_filter_disabled_bypasses_gate(client, _agent_payload, monkeypatch):
    from agent.runner import AgentOutcome

    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", False)
    monkeypatch.setattr(settings, "verification_enabled", False)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)

    with (
        patch("api.routes.chat.classify_domain") as mock_classify,
        patch("api.routes.chat.invoke_agent") as mock_invoke,
        patch("api.routes.chat.score_context"),
    ):
        mock_invoke.return_value = AgentOutcome(answer="agent answer", context="ctx")
        response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 200
    mock_classify.assert_not_called()
    mock_invoke.assert_called_once()


def test_chat_intent_decision_emitted_as_structured_log(client, _agent_payload, caplog, monkeypatch):
    from agent.intent import DomainDecision

    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "intent_filter_enabled", True)
    monkeypatch.setattr(settings, "verification_enabled", False)
    monkeypatch.setattr(settings, "buffer_maxlen", 10)
    monkeypatch.setattr(settings, "intent_threshold", 0.3)

    with (
        patch(
            "api.routes.chat.classify_domain",
            return_value=DomainDecision(in_domain=False, score=0.05),
        ),
        patch("api.routes.chat.invoke_agent"),
    ):
        with caplog.at_level("INFO", logger="api.routes.chat"):
            response = client.post("/chat", json=_agent_payload)

    assert response.status_code == 200
    intent_records = [r for r in caplog.records if "chat.intent" in r.message]
    assert len(intent_records) >= 1
    assert getattr(intent_records[0], "in_domain", None) is False
    assert getattr(intent_records[0], "score", None) == 0.05
    assert getattr(intent_records[0], "username", None) == "testuser"
    assert getattr(intent_records[0], "threshold", None) == 0.3
