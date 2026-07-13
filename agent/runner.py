"""Synchronous runner for the SmartB100 deep agent, isolated behind agent/ (ADR-0008)."""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

from agent.factory import get_agent
from agent.limits import TokenBudgetExceededError, TokenBudgetHandler
from agent.tools import SEARCH_CORPUS_SENTINELS
from core.config import settings
from core.schemas import UserProfile

# Reuse the generation-layer sanitizer so the agent path has the same
# prompt-injection hardening as the legacy /chat path (parity, no duplication).
from generation.llm import _sanitize_question

logger = logging.getLogger(__name__)

# Graceful answer returned when a run hits a configured bound (ADR-0012). A bounded run
# is a normal ChatResponse carrying this text, not a 503.
AGENT_BOUND_FALLBACK = (
    "Não consegui concluir a resposta dentro dos limites de processamento definidos. "
    "Tente reformular ou detalhar melhor a pergunta."
)


@dataclass(frozen=True)
class AgentOutcome:
    """Result of one agent run: the final answer and the context it retrieved."""

    answer: str
    context: str


def _as_text(content: Any) -> str:
    """Normalize LangChain message content (str or content blocks) to plain text."""
    if isinstance(content, str):
        return content
    return str(content)


def _build_input(
    question: str, history: list[dict[str, str]], profile: UserProfile
) -> dict[str, Any]:
    """Build the graph input: prior turns plus the user question with a short profile preamble."""
    preamble = (
        f"The user's expertise level is {profile.expertise.value}. "
        "Adapt the depth and tone of your answer accordingly."
    )
    # Sanitize the user question to strip model control tokens; the preamble is
    # system-authored and keys only on a constrained StrEnum value, so it carries
    # no injection risk.
    sanitized_question = _sanitize_question(question)
    messages: list[dict[str, str]] = list(history)
    messages.append({"role": "user", "content": f"{preamble}\n\n{sanitized_question}"})
    return {"messages": messages}


def invoke_agent(
    question: str,
    history: list[dict[str, str]],
    profile: UserProfile,
    graph: Any | None = None,
) -> AgentOutcome:
    """Run the deep agent once and return its final answer plus retrieved context.

    ``graph`` defaults to the process-wide cached agent; inject a stub in tests to run without network.
    """
    if graph is None:
        graph = get_agent()
    # Bound the run (ADR-0012): a native recursion/step limit plus a per-run token budget
    # enforced by an accumulating callback. Either bound terminates gracefully with a fallback.
    handler = TokenBudgetHandler(settings.agent_token_budget)
    callbacks: list[BaseCallbackHandler] = [handler]
    config: RunnableConfig = {
        "recursion_limit": settings.agent_recursion_limit,
        "callbacks": callbacks,
    }
    try:
        result = graph.invoke(_build_input(question, history, profile), config)
    except (GraphRecursionError, TokenBudgetExceededError) as exc:
        logger.warning("agent.bound_exceeded", extra={"bound": type(exc).__name__})
        return AgentOutcome(answer=AGENT_BOUND_FALLBACK, context="")
    messages = result["messages"]

    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    answer = _as_text(ai_messages[-1].content) if ai_messages else ""

    tool_texts = [
        _as_text(m.content)
        for m in messages
        if isinstance(m, ToolMessage)
        and m.name == "search_corpus"
        and _as_text(m.content) not in SEARCH_CORPUS_SENTINELS
    ]
    context = "\n\n".join(t for t in tool_texts if t)

    return AgentOutcome(answer=answer, context=context)
