"""Testes dos schemas Pydantic do contrato público (TASK-T61 + TASK-T62)."""

import pytest
from pydantic import ValidationError

from core.schemas import ChatRequest, ChatResponse, ExpertiseLevel, UserProfile


def _profile() -> UserProfile:
    return UserProfile(name="tester", expertise=ExpertiseLevel.beginner)


def test_chat_request_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(session_id="s1", question="", profile=_profile())


def test_chat_request_rejects_oversized_question() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(session_id="s1", question="x" * 2001, profile=_profile())


def test_chat_request_accepts_question_at_upper_boundary() -> None:
    req = ChatRequest(session_id="s1", question="x" * 2000, profile=_profile())
    assert len(req.question) == 2000


def test_chat_request_accepts_typical_question() -> None:
    req = ChatRequest(
        session_id="s1",
        question="Como cultivar soja no cerrado?",
        profile=_profile(),
    )
    assert req.question == "Como cultivar soja no cerrado?"


# ----------------------------- T62: bounds adicionais ---------------------------


def test_chat_request_rejects_empty_session_id() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(session_id="", question="q", profile=_profile())


def test_chat_request_rejects_oversized_session_id() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(session_id="x" * 256, question="q", profile=_profile())


def test_user_profile_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        UserProfile(name="", expertise=ExpertiseLevel.beginner)


def test_user_profile_rejects_oversized_name() -> None:
    with pytest.raises(ValidationError):
        UserProfile(name="x" * 256, expertise=ExpertiseLevel.beginner)


def test_chat_response_rejects_score_below_zero() -> None:
    with pytest.raises(ValidationError):
        ChatResponse(answer="ok", hallucination_score=-0.01)


def test_chat_response_rejects_score_above_one() -> None:
    with pytest.raises(ValidationError):
        ChatResponse(answer="ok", hallucination_score=1.01)


def test_chat_response_accepts_score_boundaries() -> None:
    low = ChatResponse(answer="ok", hallucination_score=0.0)
    high = ChatResponse(answer="ok", hallucination_score=1.0)
    assert low.hallucination_score == 0.0
    assert high.hallucination_score == 1.0
