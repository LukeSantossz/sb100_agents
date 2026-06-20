"""Factory for the SmartB100 deep agent (deepagents + Groq), isolated behind agent/."""

from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langgraph.graph.state import CompiledStateGraph

from agent.prompt import AGENT_INSTRUCTIONS
from agent.tools import search_corpus
from core.config import settings


def default_model() -> ChatGroq:
    """Build the default agent chat model from settings (hosted Groq, ADR-0009)."""
    return ChatGroq(model=settings.agent_model, api_key=settings.groq_api_key)


def create_agent(model: BaseChatModel | None = None) -> CompiledStateGraph:
    """Build the compiled deep-agent graph.

    `model` defaults to the Groq model from settings; inject a model in tests to compile
    the graph without network access.
    """
    if model is None:
        model = default_model()
    return create_deep_agent(
        model=model,
        tools=[search_corpus],
        system_prompt=AGENT_INSTRUCTIONS,
    )
