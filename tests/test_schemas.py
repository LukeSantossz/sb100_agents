"""Tests for the public-contract Pydantic schemas."""

import pytest
from pydantic import ValidationError

from core.schemas import ChatRequest, ChatResponse, ExpertiseLevel, UserProfile


def _profile() -> UserProfile:
    return UserProfile(name="tester", expertise=ExpertiseLevel.beginner)


def test_chat_request_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id=1, question="")


def test_chat_request_rejects_oversized_question() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id=1, question="x" * 2001)


def test_chat_request_accepts_question_at_upper_boundary() -> None:
    req = ChatRequest(conversation_id=1, question="x" * 2000)
    assert len(req.question) == 2000


def test_chat_request_accepts_typical_question() -> None:
    req = ChatRequest(
        conversation_id=1,
        question="How to grow soybeans in the Cerrado?",
    )
    assert req.question == "How to grow soybeans in the Cerrado?"
    assert req.conversation_id == 1


def test_chat_request_accepts_none_conversation_id() -> None:
    req = ChatRequest(
        conversation_id=None,
        question="How to grow soybeans?",
    )
    assert req.conversation_id is None


# ----------------------------- additional bounds ---------------------------


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
