"""Synchronous runner for the SmartB100 deep agent, isolated behind agent/ (ADR-0008)."""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from agent.factory import create_agent
from core.schemas import UserProfile


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
        f"User profile — name: {profile.name}, expertise: {profile.expertise.value}. "
        "Adapt the depth and tone of your answer accordingly."
    )
    messages: list[dict[str, str]] = list(history)
    messages.append({"role": "user", "content": f"{preamble}\n\n{question}"})
    return {"messages": messages}


def invoke_agent(
    question: str,
    history: list[dict[str, str]],
    profile: UserProfile,
    graph: Any | None = None,
) -> AgentOutcome:
    """Run the deep agent once and return its final answer plus retrieved context.

    ``graph`` defaults to a freshly built agent; inject a stub in tests to run without network.
    """
    if graph is None:
        graph = create_agent()
    result = graph.invoke(_build_input(question, history, profile))
    messages = result["messages"]

    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    answer = _as_text(ai_messages[-1].content) if ai_messages else ""

    tool_texts = [
        _as_text(m.content)
        for m in messages
        if isinstance(m, ToolMessage) and m.name == "search_corpus"
    ]
    context = "\n\n".join(t for t in tool_texts if t)

    return AgentOutcome(answer=answer, context=context)
