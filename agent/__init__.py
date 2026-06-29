"""Agentic layer: deepagents + Groq, isolated behind this package (ADR-0008)."""

from agent.factory import create_agent, default_model
from agent.intent import OUT_OF_DOMAIN_MESSAGE, DomainDecision, classify_domain
from agent.runner import AgentOutcome, invoke_agent
from agent.tools import search_corpus

__all__ = [
    "OUT_OF_DOMAIN_MESSAGE",
    "AgentOutcome",
    "DomainDecision",
    "classify_domain",
    "create_agent",
    "default_model",
    "invoke_agent",
    "search_corpus",
]
