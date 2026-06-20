"""Agentic layer: deepagents + Groq, isolated behind this package (ADR-0008)."""

from agent.factory import create_agent, default_model
from agent.tools import search_corpus

__all__ = ["create_agent", "default_model", "search_corpus"]
