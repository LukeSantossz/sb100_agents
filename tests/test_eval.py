"""Smoke tests para o pipeline de avaliacao (eval/).

Cobre: helpers em `eval/_utils`, filtro de qualidade em
`generate_questions`, formato de erro estruturado em `collect_references`,
checkpoint atomico em `run_evaluation`, A/B deterministico e filtro de
erros em `judge`, e exit-code/markdown em `report`.

Sem chamadas reais a APIs (Groq/Ollama/OpenRouter); todos os providers
sao substituidos via `monkeypatch`.
"""

from __future__ import annotations

import json
import random

import pytest

from eval._utils import (
    deterministic_sb100_position_is_a,
    is_valid_question,
    validate_dataset_schema,
)
from eval.generate_questions import parse_questions_json
from eval.judge import normalize_verdict, parse_judge_response
from eval.report import (
    extract_all_judgments,
    generate_report,
    generate_score_distribution,
    generate_verdict_stats,
)
from eval.run_evaluation import load_checkpoint, save_checkpoint

# ============================================================================
# _utils
# ============================================================================


class TestValidateDatasetSchema:
    def test_valid(self) -> None:
        validate_dataset_schema({"a": 1, "b": 2}, ["a", "b"])

    def test_missing_key(self) -> None:
        with pytest.raises(ValueError, match="obrigatorias"):
            validate_dataset_schema({"a": 1}, ["a", "b"])

    def test_not_dict(self) -> None:
        with pytest.raises(ValueError, match="deve ser dict"):
            validate_dataset_schema([1, 2, 3], ["a"])

    def test_empty_expected_keys(self) -> None:
        validate_dataset_schema({"qualquer": "coisa"}, [])


class TestIsValidQuestion:
    @pytest.mark.parametrize(
        "question",
        [
            "Qual e a melhor pratica de irrigacao no cerrado?",
            "Como funciona a rotacao de culturas em pequenas propriedades?",
        ],
    )
    def test_valid(self, question: str) -> None:
        assert is_valid_question(question) is True

    def test_too_short(self) -> None:
        assert is_valid_question("Curto?") is False

    def test_too_long(self) -> None:
        assert is_valid_question("A" * 600 + "?") is False

    def test_no_question_mark(self) -> None:
        assert is_valid_question("Um enunciado declarativo de tamanho razoavel.") is False

    def test_non_string(self) -> None:
        assert is_valid_question(None) is False
        assert is_valid_question(123) is False

    def test_empty(self) -> None:
        assert is_valid_question("") is False

    def test_only_whitespace(self) -> None:
        assert is_valid_question("   \n\t   ") is False


class TestDeterministicABPosition:
    def test_consistent_across_calls(self) -> None:
        qid = "abc-123-def-456"
        assert deterministic_sb100_position_is_a(qid) == deterministic_sb100_position_is_a(qid)

    def test_different_ids_balanced_distribution(self) -> None:
        # 1000 ids → distribuicao ~50/50 (tolerancia ampla para MD5)
        ids = [f"q-{i:04d}" for i in range(1000)]
        a_count = sum(1 for qid in ids if deterministic_sb100_position_is_a(qid))
        assert 400 < a_count < 600

    def test_independent_of_random_seed(self) -> None:
        qid = "fixed-question-id"
        first = deterministic_sb100_position_is_a(qid)
        random.seed(42)
        second = deterministic_sb100_position_is_a(qid)
        random.seed(0)
        third = deterministic_sb100_position_is_a(qid)
        assert first == second == third


# ============================================================================
# generate_questions
# ============================================================================


class TestParseQuestionsJson:
    def test_valid_json_array(self) -> None:
        content = (
            "[\n"
            '  "Qual e a melhor pratica de irrigacao no cerrado?",\n'
            '  "Como funciona a rotacao de culturas em propriedades?"\n'
            "]"
        )
        result = parse_questions_json(content)
        assert len(result) == 2

    def test_filters_short_questions(self) -> None:
        content = '["Q?", "Pergunta valida com tamanho suficiente?"]'
        result = parse_questions_json(content)
        # "Q?" tem 2 chars → filtrada; segunda tem 38 chars → ok
        assert len(result) == 1
        assert result[0] == "Pergunta valida com tamanho suficiente?"

    def test_filters_no_question_mark(self) -> None:
        content = (
            '["Frase declarativa sem ponto de interrogacao", '
            '"Frase interrogativa com ponto adequado aqui?"]'
        )
        result = parse_questions_json(content)
        assert len(result) == 1
        assert "?" in result[0]

    def test_fallback_lines_parsing(self) -> None:
        content = (
            "1. Qual e a melhor estacao de plantio para milho safrinha?\n"
            "2. Como fertilizar o solo de forma sustentavel no cerrado?"
        )
        result = parse_questions_json(content)
        assert len(result) == 2

    def test_empty_returns_empty(self) -> None:
        assert parse_questions_json("") == []

    def test_non_string_items_filtered(self) -> None:
        content = '["Pergunta valida com tamanho suficiente aqui?", 42, null]'
        result = parse_questions_json(content)
        assert len(result) == 1


# ============================================================================
# judge
# ============================================================================


class TestParseJudgeResponse:
    def test_valid_json(self) -> None:
        content = (
            '{"score_a": 8, "score_b": 5, "justification": "A e melhor", "verdict": "A_better"}'
        )
        result = parse_judge_response(content)
        assert result["score_a"] == 8.0
        assert result["score_b"] == 5.0
        assert result["verdict"] == "A_better"

    def test_invalid_json_fallback_neutral(self) -> None:
        result = parse_judge_response("texto sem json valido aqui")
        assert result["score_a"] == 5.0
        assert result["score_b"] == 5.0
        assert "[PARSE ERROR]" in result["justification"]


class TestNormalizeVerdict:
    def test_a_better_when_sb100_was_a(self) -> None:
        assert normalize_verdict("A_better", True) == "better"

    def test_a_better_when_sb100_was_b(self) -> None:
        assert normalize_verdict("A_better", False) == "worse"

    def test_b_better_when_sb100_was_a(self) -> None:
        assert normalize_verdict("B_better", True) == "worse"

    def test_b_better_when_sb100_was_b(self) -> None:
        assert normalize_verdict("B_better", False) == "better"

    def test_equivalent(self) -> None:
        assert normalize_verdict("equivalent", True) == "equivalent"
        assert normalize_verdict("equivalent", False) == "equivalent"


# ============================================================================
# run_evaluation: checkpoint
# ============================================================================


class TestCheckpoint:
    def test_roundtrip(self, tmp_path) -> None:
        path = tmp_path / "checkpoint.json"
        results = [
            {"question_id": "q1", "sb100_answer": "r1", "sb100_success": True},
            {"question_id": "q2", "sb100_answer": "r2", "sb100_success": True},
        ]
        save_checkpoint(path, results)
        loaded = load_checkpoint(path)
        assert loaded == results

    def test_missing_returns_empty(self, tmp_path) -> None:
        assert load_checkpoint(tmp_path / "nao_existe.json") == []

    def test_corrupted_returns_empty(self, tmp_path) -> None:
        path = tmp_path / "corrupto.json"
        path.write_text("not valid json {", encoding="utf-8")
        assert load_checkpoint(path) == []

    def test_atomic_replace_keeps_consistent(self, tmp_path) -> None:
        path = tmp_path / "checkpoint.json"
        save_checkpoint(path, [{"question_id": "q1"}])
        save_checkpoint(path, [{"question_id": "q1"}, {"question_id": "q2"}])
        assert len(load_checkpoint(path)) == 2

    def test_load_filters_invalid_entries(self, tmp_path) -> None:
        path = tmp_path / "ck.json"
        path.write_text(
            json.dumps(
                {
                    "results": [
                        {"question_id": "q1"},
                        "string solta sem question_id",
                        {"sem_question_id": True},
                    ]
                }
            ),
            encoding="utf-8",
        )
        loaded = load_checkpoint(path)
        assert loaded == [{"question_id": "q1"}]


# ============================================================================
# collect_references: erro estruturado
# ============================================================================


class TestCollectReferencesErrorStructure:
    def test_error_stored_as_structured_field(self, tmp_path, monkeypatch) -> None:
        from eval import collect_references as cr

        questions_data = {
            "metadata": {"source_documents": ["fake.pdf"]},
            "questions": [
                {
                    "question_id": "q1",
                    "question": "Pergunta valida com tamanho suficiente para teste?",
                    "reference_answers": [],
                }
            ],
        }
        input_path = tmp_path / "questions.json"
        output_path = tmp_path / "references.json"
        input_path.write_text(json.dumps(questions_data), encoding="utf-8")

        def fake_get_ref(question: str, model: str) -> str:
            raise RuntimeError("API down")

        monkeypatch.setattr(cr, "get_reference_groq", fake_get_ref)

        cr.collect_references(
            questions_path=str(input_path),
            output_path=str(output_path),
            provider="groq",
            models=["model-x"],
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))
        ref = data["questions"][0]["reference_answers"][0]
        assert ref["reference_model"] == "model-x"
        assert ref["reference_answer"] is None
        assert ref["error"] == "API down"

    def test_success_stores_answer_with_null_error(self, tmp_path, monkeypatch) -> None:
        from eval import collect_references as cr

        questions_data = {
            "metadata": {},
            "questions": [
                {
                    "question_id": "q1",
                    "question": "Pergunta de teste valida e suficientemente longa?",
                    "reference_answers": [],
                }
            ],
        }
        input_path = tmp_path / "questions.json"
        output_path = tmp_path / "references.json"
        input_path.write_text(json.dumps(questions_data), encoding="utf-8")

        monkeypatch.setattr(cr, "get_reference_groq", lambda q, m: "Resposta OK")

        cr.collect_references(
            questions_path=str(input_path),
            output_path=str(output_path),
            provider="groq",
            models=["model-ok"],
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))
        ref = data["questions"][0]["reference_answers"][0]
        assert ref["reference_answer"] == "Resposta OK"
        assert ref["error"] is None


# ============================================================================
# judge: filtro de erro + smoke
# ============================================================================


class TestJudgeFiltersErrors:
    def _eval_results(self, refs: list[dict]) -> dict:
        return {
            "metadata": {},
            "results": [
                {
                    "question_id": "q1",
                    "question": "Pergunta de teste valida?",
                    "sb100_answer": "resposta SB100",
                    "sb100_hallucination_score": 0.1,
                    "sb100_session_id": "s",
                    "sb100_success": True,
                    "reference_answers": refs,
                }
            ],
        }

    def test_skips_new_format_error(self, tmp_path, monkeypatch) -> None:
        from eval import judge as jd

        data = self._eval_results(
            [
                {
                    "reference_model": "model-broken",
                    "reference_answer": None,
                    "error": "API down",
                },
                {
                    "reference_model": "model-ok",
                    "reference_answer": "Resposta OK",
                    "error": None,
                },
            ]
        )
        input_path = tmp_path / "eval.json"
        output_path = tmp_path / "judged.json"
        input_path.write_text(json.dumps(data), encoding="utf-8")

        monkeypatch.setattr(
            jd,
            "judge_groq",
            lambda q, a, b, m: {
                "score_a": 7.0,
                "score_b": 5.0,
                "justification": "ok",
                "verdict": "A_better",
            },
        )

        jd.run_judge(
            input_path=str(input_path),
            output_path=str(output_path),
            provider="groq",
            model="judge-model",
        )

        result = json.loads(output_path.read_text(encoding="utf-8"))
        judgments = result["results"][0]["judgments"]
        assert len(judgments) == 1
        assert judgments[0]["reference_model"] == "model-ok"

    def test_skips_legacy_format_error(self, tmp_path, monkeypatch) -> None:
        from eval import judge as jd

        data = self._eval_results(
            [
                {
                    "reference_model": "model-legacy",
                    "reference_answer": "[ERRO] formato antigo",
                }
            ]
        )
        input_path = tmp_path / "eval.json"
        output_path = tmp_path / "judged.json"
        input_path.write_text(json.dumps(data), encoding="utf-8")

        def fake_judge(*_args: object, **_kwargs: object) -> dict:
            pytest.fail("Judge nao deveria ser chamado para refs com erro")

        monkeypatch.setattr(jd, "judge_groq", fake_judge)

        jd.run_judge(
            input_path=str(input_path),
            output_path=str(output_path),
            provider="groq",
            model="judge-model",
        )

        result = json.loads(output_path.read_text(encoding="utf-8"))
        assert result["results"][0]["judgments"] == []

    def test_position_is_deterministic_across_runs(self, tmp_path, monkeypatch) -> None:
        from eval import judge as jd

        data = self._eval_results(
            [
                {"reference_model": "m", "reference_answer": "ref", "error": None},
            ]
        )
        input_path = tmp_path / "eval.json"
        input_path.write_text(json.dumps(data), encoding="utf-8")

        captured: list[str] = []

        def fake_judge(question: str, a: str, b: str, model: str) -> dict:
            captured.append(a)
            return {
                "score_a": 7.0,
                "score_b": 5.0,
                "justification": "ok",
                "verdict": "A_better",
            }

        monkeypatch.setattr(jd, "judge_groq", fake_judge)

        for _ in range(2):
            jd.run_judge(
                input_path=str(input_path),
                output_path=str(tmp_path / "out.json"),
                provider="groq",
                model="m",
            )

        # Mesma pergunta → mesma posicao em ambas execucoes
        assert captured[0] == captured[1]


# ============================================================================
# report
# ============================================================================


@pytest.fixture
def sample_judged_dataset() -> dict:
    """Dataset minimo julgado para testar report."""
    return {
        "metadata": {
            "total_questions": 2,
            "judge_model": "test-model",
            "judge_provider": "test",
        },
        "results": [
            {
                "question_id": "q1",
                "question": "Pergunta de teste 1?",
                "sb100_answer": "Resposta SB100 1",
                "reference_answers": [{"reference_model": "modelA", "reference_answer": "Ref A"}],
                "judgments": [
                    {
                        "reference_model": "modelA",
                        "judge_score": 7,
                        "reference_score": 5,
                        "judge_verdict": "better",
                        "judge_justification": "Justificativa 1",
                    }
                ],
            },
            {
                "question_id": "q2",
                "question": "Pergunta de teste 2?",
                "sb100_answer": "Resposta SB100 2",
                "reference_answers": [{"reference_model": "modelB", "reference_answer": "Ref B"}],
                "judgments": [
                    {
                        "reference_model": "modelB",
                        "judge_score": 4,
                        "reference_score": 6,
                        "judge_verdict": "worse",
                        "judge_justification": "Justificativa 2",
                    }
                ],
            },
        ],
    }


class TestReport:
    def test_extract_all_judgments(self, sample_judged_dataset: dict) -> None:
        judgments = extract_all_judgments(sample_judged_dataset["results"])
        assert len(judgments) == 2
        assert judgments[0]["judge_score"] == 7

    def test_extract_skips_none_score(self) -> None:
        results = [
            {
                "question": "Pergunta valida de teste?",
                "sb100_answer": "a",
                "reference_answers": [],
                "judgments": [
                    {
                        "reference_model": "m",
                        "judge_score": None,
                        "judge_verdict": "error",
                    }
                ],
            }
        ]
        assert extract_all_judgments(results) == []

    def test_score_distribution(self, sample_judged_dataset: dict) -> None:
        judgments = extract_all_judgments(sample_judged_dataset["results"])
        dist = generate_score_distribution(judgments)
        assert dist["7-8 (Bom)"] == 1
        assert dist["3-4 (Fraco)"] == 1

    def test_verdict_stats(self, sample_judged_dataset: dict) -> None:
        judgments = extract_all_judgments(sample_judged_dataset["results"])
        stats = generate_verdict_stats(judgments)
        assert stats["modelA"]["better"] == 1
        assert stats["modelB"]["worse"] == 1

    def test_generate_report_creates_files(self, tmp_path, sample_judged_dataset: dict) -> None:
        input_path = tmp_path / "judged.json"
        report_path = tmp_path / "report.md"
        sample_path = tmp_path / "sample.csv"
        input_path.write_text(json.dumps(sample_judged_dataset), encoding="utf-8")

        ok = generate_report(
            str(input_path),
            str(report_path),
            str(sample_path),
            sample_size=2,
        )

        assert ok is True
        assert report_path.exists()
        assert sample_path.exists()
        assert "# Relatorio de Avaliacao - SB100" in report_path.read_text(encoding="utf-8")

    def test_generate_report_returns_false_when_empty(self, tmp_path) -> None:
        empty = {"metadata": {}, "results": []}
        input_path = tmp_path / "empty.json"
        input_path.write_text(json.dumps(empty), encoding="utf-8")

        ok = generate_report(
            str(input_path),
            str(tmp_path / "report.md"),
            str(tmp_path / "sample.csv"),
        )

        assert ok is False


# ============================================================================
# Smoke integrativo: judge -> report
# ============================================================================


class TestPipelineSmoke:
    def test_judge_to_report_end_to_end(self, tmp_path, monkeypatch) -> None:
        from eval import judge as jd
        from eval import report as rp

        questions = [
            {
                "question_id": f"q-{i:02d}",
                "question": f"Pergunta valida de teste numero {i:02d}?",
                "reference_answers": [
                    {
                        "reference_model": "ref-m",
                        "reference_answer": f"resposta ref {i}",
                        "error": None,
                    }
                ],
            }
            for i in range(3)
        ]
        eval_results = {
            "metadata": {"total_questions": 3},
            "results": [
                {
                    **q,
                    "sb100_answer": f"resposta sb100 {q['question_id']}",
                    "sb100_hallucination_score": 0.1,
                    "sb100_session_id": "session-1",
                    "sb100_success": True,
                }
                for q in questions
            ],
        }
        eval_path = tmp_path / "eval.json"
        judged_path = tmp_path / "judged.json"
        report_path = tmp_path / "report.md"
        sample_path = tmp_path / "sample.csv"
        eval_path.write_text(json.dumps(eval_results), encoding="utf-8")

        monkeypatch.setattr(
            jd,
            "judge_groq",
            lambda q, a, b, m: {
                "score_a": 7.0,
                "score_b": 5.0,
                "justification": "ok",
                "verdict": "A_better",
            },
        )

        jd.run_judge(
            input_path=str(eval_path),
            output_path=str(judged_path),
            provider="groq",
            model="judge-model",
        )

        ok = rp.generate_report(
            str(judged_path),
            str(report_path),
            str(sample_path),
            sample_size=3,
        )

        assert ok is True
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "# Relatorio de Avaliacao - SB100" in content
