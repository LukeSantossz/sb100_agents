"""Bounds for the agent loop (ADR-0012): a per-run token-budget callback handler.

The recursion/step bound is native to LangGraph (``recursion_limit`` in the invoke config).
This module supplies the second bound: a callback handler that accumulates per-call token usage
and aborts the run once the cumulative total crosses the configured budget. It is a *soft* cap —
it fires after a model call returns, so it stops the next step rather than preempting an in-flight
call. It fails open: a provider that does not report usage counts zero and never blocks a run.
"""

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class TokenBudgetExceededError(Exception):
    """Raised when cumulative agent-run token usage crosses the configured budget."""

    def __init__(self, used: int, budget: int) -> None:
        super().__init__(f"agent token budget exceeded: {used} > {budget}")
        self.used = used
        self.budget = budget


class TokenBudgetHandler(BaseCallbackHandler):
    """Accumulate per-call token usage and abort the run once it exceeds ``budget``.

    On each ``on_llm_end`` the response's total token usage is added to a running total; when the
    total exceeds ``budget`` the handler raises :class:`TokenBudgetExceededError`, which propagates out
    of ``graph.invoke`` and is caught by the runner. When a response carries no usage, zero is
    counted and a warning is logged (fail-open), so a provider that omits usage never blocks a run.

    ``raise_error = True`` is required: LangChain's callback manager swallows and logs handler
    exceptions by default (``BaseCallbackHandler.raise_error`` is ``False``), which would silently
    discard the budget abort during a real model run.
    """

    raise_error = True

    def __init__(self, budget: int) -> None:
        self.budget = budget
        self.total = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        used = self._extract_total_tokens(response)
        if used == 0:
            logger.warning("agent.token_budget.no_usage")
        self.total += used
        if self.total > self.budget:
            raise TokenBudgetExceededError(used=self.total, budget=self.budget)

    @staticmethod
    def _extract_total_tokens(response: LLMResult) -> int:
        """Read the total token count from an ``on_llm_end`` result across providers.

        Groq/OpenAI report usage in ``llm_output``; Ollama leaves ``llm_output`` empty and reports
        usage on the message's standardized ``usage_metadata``. Try the ``llm_output`` block first,
        then fall back to summing ``usage_metadata`` across the generation messages. Returns 0 when
        no usage is present at either location, so accounting fails open.
        """
        llm_output = response.llm_output or {}
        usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total

        from_messages = 0
        found = False
        for generation_list in response.generations:
            for generation in generation_list:
                usage_metadata = getattr(getattr(generation, "message", None), "usage_metadata", None)
                value = usage_metadata.get("total_tokens") if usage_metadata else None
                if isinstance(value, int):
                    from_messages += value
                    found = True
        return from_messages if found else 0
