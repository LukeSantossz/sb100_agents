"""Tests for the public-contract Pydantic schemas."""

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
        question="How to grow soybeans in the Cerrado?",
        profile=_profile(),
    )
    assert req.question == "How to grow soybeans in the Cerrado?"


# ----------------------------- additional bounds ---------------------------


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


# ---------------- a blank question is rejected up front (issue #95) ----------------


@pytest.mark.parametrize("question", ["   ", "\t", "\n", " \n \t "])
def test_a_whitespace_only_question_is_rejected(question: str) -> None:
    """It used to pass min_length=1, spend the whole pipeline, and 500 at the buffer."""
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="s1",
            question=question,
            profile=UserProfile(name="U", expertise="beginner"),
        )


def test_a_question_is_stripped_before_use() -> None:
    """The pipeline should embed the question, not the whitespace around it."""
    request = ChatRequest(
        session_id="s1",
        question="  como corrigir a acidez do solo?  ",
        profile=UserProfile(name="U", expertise="beginner"),
    )
    assert request.question == "como corrigir a acidez do solo?"
