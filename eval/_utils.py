"""Shared utilities for the evaluation pipeline.

Path constants derived from `__file__` so scripts run from any CWD;
helpers for schema validation, question quality filtering and
deterministic A/B assignment.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

EVAL_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = EVAL_DIR.parent
DATASET_DIR: Path = EVAL_DIR / "dataset"
RESULTS_DIR: Path = EVAL_DIR / "results"

DEFAULT_QUESTIONS_PATH: Path = DATASET_DIR / "questions.json"
DEFAULT_REFERENCES_PATH: Path = DATASET_DIR / "reference_answers.json"
DEFAULT_EVAL_RESULTS_PATH: Path = RESULTS_DIR / "evaluation_results.json"
DEFAULT_JUDGED_RESULTS_PATH: Path = RESULTS_DIR / "judged_results.json"
DEFAULT_REPORT_PATH: Path = RESULTS_DIR / "report.md"
DEFAULT_HUMAN_SAMPLE_PATH: Path = RESULTS_DIR / "human_sample.csv"
DEFAULT_CHECKPOINT_PATH: Path = RESULTS_DIR / "evaluation_checkpoint.json"

QUESTION_MIN_LEN: int = 20
QUESTION_MAX_LEN: int = 500


def validate_dataset_schema(data: Any, expected_keys: list[str]) -> None:
    """Validate that `data` is a dict containing every key in `expected_keys`.

    Args:
        data: Object loaded from JSON (expected to be a dict).
        expected_keys: Required top-level keys.

    Raises:
        ValueError: `data` is not a dict or a required key is missing.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Dataset must be a dict, got {type(data).__name__}")
    missing = [key for key in expected_keys if key not in data]
    if missing:
        raise ValueError(f"Dataset missing required keys: {missing}")


def is_valid_question(question: Any) -> bool:
    """Quality filter: string containing '?' with 20-500 characters."""
    if not isinstance(question, str):
        return False
    stripped = question.strip()
    if "?" not in stripped:
        return False
    return QUESTION_MIN_LEN <= len(stripped) <= QUESTION_MAX_LEN


def deterministic_sb100_position_is_a(question_id: str) -> bool:
    """Decide the SB100 position (A or B) deterministically.

    Uses the MD5 hash of `question_id` to avoid depending on
    `random.seed()` or `PYTHONHASHSEED`. The same `question_id` always
    yields the same side, keeping runs reproducible.

    Args:
        question_id: Unique question identifier.

    Returns:
        True if SB100 should take position A; False for position B.
    """
    digest = hashlib.md5(question_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2 == 0
