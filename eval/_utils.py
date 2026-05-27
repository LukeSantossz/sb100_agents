"""Utilitarios compartilhados do pipeline de avaliacao.

Constantes de paths derivadas de `__file__` para permitir execucao
de qualquer CWD; helpers de validacao de schema, qualidade de pergunta
e decisao A/B deterministica.
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
    """Valida que `data` e um dict contendo todas as chaves em `expected_keys`.

    Args:
        data: Objeto carregado de JSON (esperado dict).
        expected_keys: Chaves obrigatorias no nivel raiz.

    Raises:
        ValueError: `data` nao e dict ou alguma chave esta ausente.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Dataset deve ser dict, recebido {type(data).__name__}")
    missing = [key for key in expected_keys if key not in data]
    if missing:
        raise ValueError(f"Dataset sem chaves obrigatorias: {missing}")


def is_valid_question(question: Any) -> bool:
    """Filtro de qualidade: string contendo '?' com 20-500 caracteres."""
    if not isinstance(question, str):
        return False
    stripped = question.strip()
    if "?" not in stripped:
        return False
    return QUESTION_MIN_LEN <= len(stripped) <= QUESTION_MAX_LEN


def deterministic_sb100_position_is_a(question_id: str) -> bool:
    """Decide a posicao do SB100 (A ou B) de forma deterministica.

    Usa hash MD5 do `question_id` para evitar dependencia de
    `random.seed()` ou de `PYTHONHASHSEED`. Mesmo `question_id` sempre
    retorna o mesmo lado, permitindo reproducibilidade entre execucoes.

    Args:
        question_id: Identificador unico da pergunta.

    Returns:
        True se SB100 deve ocupar a posicao A; False para posicao B.
    """
    digest = hashlib.md5(question_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2 == 0
