"""Profiling module for user adaptation and intent filtering."""

from .intent_filter import is_agricultural_intent
from .profile import adapt_response_for_profile

__all__ = ["is_agricultural_intent", "adapt_response_for_profile"]
