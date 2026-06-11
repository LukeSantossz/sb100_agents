"""Hallucination verification module."""

from verification.entropy import compute_entropy_score
from verification.gate import evaluate

__all__ = ["compute_entropy_score", "evaluate"]
