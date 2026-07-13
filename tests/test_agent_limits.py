"""Tests for the agent loop bounds (ADR-0012): the token-budget callback handler."""

import pytest
from langchain_core.outputs import Generation, LLMResult


def _llm_result(total_tokens: int | None) -> LLMResult:
    """Build an LLMResult carrying OpenAI/Groq-style token usage in llm_output."""
    llm_output = None if total_tokens is None else {"token_usage": {"total_tokens": total_tokens}}
    return LLMResult(generations=[[Generation(text="x")]], llm_output=llm_output)


def test_token_budget_handler_stays_silent_under_budget() -> None:
    from agent.limits import TokenBudgetHandler

    handler = TokenBudgetHandler(budget=100)
    handler.on_llm_end(_llm_result(40))
    handler.on_llm_end(_llm_result(50))  # cumulative 90, under 100

    assert handler.total == 90


def test_token_budget_handler_raises_when_cumulative_usage_exceeds_budget() -> None:
    from agent.limits import TokenBudgetExceededError, TokenBudgetHandler

    handler = TokenBudgetHandler(budget=100)
    handler.on_llm_end(_llm_result(60))
    with pytest.raises(TokenBudgetExceededError):
        handler.on_llm_end(_llm_result(60))  # cumulative 120 > 100


def test_token_budget_handler_fails_open_when_usage_absent() -> None:
    from agent.limits import TokenBudgetHandler

    handler = TokenBudgetHandler(budget=100)
    handler.on_llm_end(_llm_result(None))  # no usage reported; must not raise

    assert handler.total == 0
