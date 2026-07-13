"""Tests for the agent loop bounds (ADR-0012): the token-budget callback handler."""

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, Generation, LLMResult


def _llm_result(total_tokens: int | None) -> LLMResult:
    """Build an LLMResult carrying OpenAI/Groq-style token usage in llm_output."""
    llm_output = None if total_tokens is None else {"token_usage": {"total_tokens": total_tokens}}
    return LLMResult(generations=[[Generation(text="x")]], llm_output=llm_output)


def _ollama_llm_result(total_tokens: int) -> LLMResult:
    """Build an LLMResult in the ChatOllama shape: no llm_output, usage on the message.

    Captured from a live qwen2.5:7b call (issue #193): ``llm_output`` is None and usage lives
    in the message's standardized ``usage_metadata``.
    """
    message = AIMessage(
        content="ok",
        usage_metadata={"input_tokens": 35, "output_tokens": 2, "total_tokens": total_tokens},
    )
    return LLMResult(generations=[[ChatGeneration(message=message)]], llm_output=None)


def test_extract_total_tokens_reads_ollama_usage_metadata_shape() -> None:
    from agent.limits import TokenBudgetHandler

    handler = TokenBudgetHandler(budget=10**12)
    handler.on_llm_end(_ollama_llm_result(37))

    assert handler.total == 37


def test_extract_total_tokens_still_reads_groq_llm_output_shape() -> None:
    from agent.limits import TokenBudgetHandler

    handler = TokenBudgetHandler(budget=10**12)
    handler.on_llm_end(_llm_result(117))

    assert handler.total == 117


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


def test_token_budget_aborts_through_callback_manager_dispatch() -> None:
    """Regression (R2): the budget must abort via the real callback dispatch, not only a direct
    call. BaseCallbackHandler swallows handler exceptions unless raise_error is True, so a direct
    on_llm_end call would pass while a real model run silently ignores the budget."""
    from langchain_core.callbacks.manager import CallbackManager

    from agent.limits import TokenBudgetExceededError, TokenBudgetHandler

    handler = TokenBudgetHandler(budget=100)
    manager = CallbackManager(handlers=[handler])
    run_manager = manager.on_llm_start({"name": "x"}, ["prompt"])[0]
    run_manager.on_llm_end(_llm_result(60))  # cumulative 60, under budget
    with pytest.raises(TokenBudgetExceededError):
        run_manager.on_llm_end(_llm_result(60))  # cumulative 120 > 100 must propagate
