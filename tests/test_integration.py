"""End-to-end integration tests for the RAG pipeline."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import verify_token
from api.main import app
from api.routes.chat import _sessions
from core.schemas import ChatResponse, ExpertiseLevel
from database.models import User


def _override_verify_token() -> User:
    """JWT gate stub for integration — returns a fixed user without hitting the DB."""
    return User(
        id=1,
        username="testuser",
        hashed_password="x",
        created_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def _clear_sessions_cache() -> Generator[None, None, None]:
    """Ensure ``_sessions`` starts empty in each test to avoid leaks."""
    _sessions.clear()
    yield
    _sessions.clear()


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
def mock_verification_disabled():
    """Mock that disables hallucination verification."""
    with patch("api.routes.chat.settings") as mock_settings:
        mock_settings.verification_enabled = False
        mock_settings.buffer_maxlen = 10
        yield mock_settings


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
    payload = {
        "session_id": f"test-expertise-{expertise.value}",
        "question": "How to correct soil acidity?",
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
    session_id = "test-multiturn-session"
    questions = [
        "What is the ideal soil pH?",
        "And how do I correct it?",
        "How long before planting?",
    ]

    for question in questions:
        payload = {
            "session_id": session_id,
            "question": question,
            "profile": {"name": "TestUser", "expertise": "beginner"},
        }

        response = client.post("/chat", json=payload)

        assert response.status_code == 200

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
def mock_verification_enabled():
    """Mock that enables verification with a fixed score."""
    with patch("api.routes.chat.settings") as mock_settings:
        mock_settings.verification_enabled = True
        mock_settings.buffer_maxlen = 10

        with patch("api.routes.chat.verify_and_generate") as mock_verify:
            mock_verify.return_value = ChatResponse(
                answer="Verified answer",
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
        "session_id": "test-score",
        "question": "How to correct soil acidity?",
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
    """hallucination_score is 0.0 when verification is disabled."""
    payload = {
        "session_id": "test-score-disabled",
        "question": "How to correct soil acidity?",
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
    """The full nominal flow does not produce HTTP 500."""
    payloads = [
        {
            "session_id": "nominal-1",
            "question": "What is the ideal pH?",
            "profile": {"name": "User1", "expertise": "beginner"},
        },
        {
            "session_id": "nominal-1",
            "question": "How to apply lime?",
            "profile": {"name": "User1", "expertise": "beginner"},
        },
        {
            "session_id": "nominal-2",
            "question": "Lime dosage?",
            "profile": {"name": "User2", "expertise": "expert"},
        },
    ]

    for payload in payloads:
        response = client.post("/chat", json=payload)
        assert response.status_code != 500, f"HTTP 500 for payload: {payload}"
        assert response.status_code == 200


def test_chat_access_log_emits_username_and_session_id(
    client,
    mock_embedding,
    mock_context,
    mock_verification_disabled,
    mock_generate_by_expertise,
    caplog: pytest.LogCaptureFixture,
):
    """The /chat handler emits a structured log with username + session_id."""
    payload = {
        "session_id": "log-session-42",
        "question": "ping",
        "profile": {"name": "TestUser", "expertise": "beginner"},
    }

    with caplog.at_level("INFO", logger="api.routes.chat"):
        response = client.post("/chat", json=payload)

    assert response.status_code == 200
    access_records = [r for r in caplog.records if "chat.access" in r.message]
    assert len(access_records) >= 1
    # Check structured fields (from the logger.info `extra=` kwarg)
    record = access_records[0]
    assert getattr(record, "username", None) == "testuser"
    assert getattr(record, "session_id", None) == "log-session-42"


def test_cross_user_session_id_does_not_leak_history_via_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Endpoint-level (#108): a second user reusing a session_id gets no history.

    Two users hit POST /chat with the SAME session_id; the second must never see
    the first user's turns in the history handed to ``generate`` (IDOR closed).
    """
    from api.dependencies import limiter
    from api.routes import chat as chat_module

    captured_histories: list[list[dict[str, str]]] = []

    def _capture_generate(question, context, history, profile):  # type: ignore[no-untyped-def]
        captured_histories.append(list(history))
        return f"answer to {question}"

    monkeypatch.setattr(chat_module.settings, "verification_enabled", False)
    monkeypatch.setattr(chat_module, "generate_embedding", lambda _q: [0.1] * 768)
    monkeypatch.setattr(chat_module, "search_context", lambda _emb: ["chunk"])
    monkeypatch.setattr(chat_module, "generate", _capture_generate)

    user_a = User(id=1, username="alice", hashed_password="x", created_at=datetime.now(UTC))
    user_b = User(id=2, username="bob", hashed_password="x", created_at=datetime.now(UTC))
    current = {"user": user_a}
    limiter.reset()
    app.dependency_overrides[verify_token] = lambda: current["user"]
    try:
        client = TestClient(app)

        def _post(question: str) -> int:
            return client.post(
                "/chat",
                json={
                    "session_id": "victim-session",
                    "question": question,
                    "profile": {"name": "u", "expertise": "beginner"},
                },
            ).status_code

        assert _post("alice-1") == 200
        assert _post("alice-2") == 200
        current["user"] = user_b
        assert _post("bob-1") == 200
    finally:
        app.dependency_overrides.clear()
        limiter.reset()

    # Bob's request (last) saw an empty history — Alice's turns never leaked.
    assert captured_histories[-1] == []
    # Sanity: Alice's second turn did see her own first turn.
    assert len(captured_histories[1]) > 0
