"""Testes dos schemas Pydantic do contrato público (TASK-T61)."""

import pytest
from pydantic import ValidationError

from core.schemas import ChatRequest, ExpertiseLevel, UserProfile


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
