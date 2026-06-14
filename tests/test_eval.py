"""Smoke tests for the evaluation pipeline (eval/).

Covers: helpers in `eval/_utils`, quality filter in
`generate_questions`, structured error format in `collect_references`,
atomic checkpoint in `run_evaluation`, deterministic A/B and error
filtering in `judge`, and exit-code/markdown in `report`.

No real API calls (Groq/Ollama/OpenRouter); every provider is replaced
via `monkeypatch`.
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from unittest.mock import AsyncMock, Mock

import httpx
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
from eval.run_evaluation import (
    EvalAuthError,
    call_chat_api,
    load_checkpoint,
    main,
    resolve_token,
    save_checkpoint,
)

# ============================================================================
# _utils
# ============================================================================


class TestValidateDatasetSchema:
    def test_valid(self) -> None:
        validate_dataset_schema({"a": 1, "b": 2}, ["a", "b"])

    def test_missing_key(self) -> None:
        with pytest.raises(ValueError, match="missing required keys"):
            validate_dataset_schema({"a": 1}, ["a", "b"])

    def test_not_dict(self) -> None:
        with pytest.raises(ValueError, match="must be a dict"):
            validate_dataset_schema([1, 2, 3], ["a"])

    def test_empty_expected_keys(self) -> None:
        validate_dataset_schema({"any": "thing"}, [])


class TestIsValidQuestion:
    @pytest.mark.parametrize(
        "question",
        [
            "What is the best irrigation practice in the cerrado?",
            "How does crop rotation work on small farms in Brazil?",
        ],
    )
    def test_valid(self, question: str) -> None:
        assert is_valid_question(question) is True

    def test_too_short(self) -> None:
        assert is_valid_question("Short?") is False

    def test_too_long(self) -> None:
        assert is_valid_question("A" * 600 + "?") is False

    def test_no_question_mark(self) -> None:
        assert is_valid_question("A declarative statement of reasonable length.") is False

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
        # 1000 ids → ~50/50 distribution (wide tolerance for MD5)
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
            '  "What is the best irrigation practice in the cerrado?",\n'
            '  "How does crop rotation work on rural properties?"\n'
            "]"
        )
        result = parse_questions_json(content)
        assert len(result) == 2

    def test_filters_short_questions(self) -> None:
        content = '["Q?", "A valid question with sufficient length?"]'
        result = parse_questions_json(content)
        # "Q?" has 2 chars → filtered; second has 40 chars → ok
        assert len(result) == 1
        assert result[0] == "A valid question with sufficient length?"

    def test_filters_no_question_mark(self) -> None:
        content = (
            '["A declarative sentence without question mark", '
            '"An interrogative sentence with a proper mark?"]'
        )
        result = parse_questions_json(content)
        assert len(result) == 1
        assert "?" in result[0]

    def test_fallback_lines_parsing(self) -> None:
        content = (
            "1. What is the best planting season for safrinha corn?\n"
            "2. How can soil be fertilized sustainably in the cerrado?"
        )
        result = parse_questions_json(content)
        assert len(result) == 2

    def test_empty_returns_empty(self) -> None:
        assert parse_questions_json("") == []

    def test_non_string_items_filtered(self) -> None:
        content = '["A valid question with sufficient length here?", 42, null]'
        result = parse_questions_json(content)
        assert len(result) == 1


# ============================================================================
# judge
# ============================================================================


class TestParseJudgeResponse:
    def test_valid_json(self) -> None:
        content = (
            '{"score_a": 8, "score_b": 5, "justification": "A is better", "verdict": "A_better"}'
        )
        result = parse_judge_response(content)
        assert result["score_a"] == 8.0
        assert result["score_b"] == 5.0
        assert result["verdict"] == "A_better"

    def test_invalid_json_fallback_neutral(self) -> None:
        result = parse_judge_response("text without valid json here")
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
        assert load_checkpoint(tmp_path / "does_not_exist.json") == []

    def test_corrupted_returns_empty(self, tmp_path) -> None:
        path = tmp_path / "corrupted.json"
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
                        "loose string without question_id",
                        {"no_question_id": True},
                    ]
                }
            ),
            encoding="utf-8",
        )
        loaded = load_checkpoint(path)
        assert loaded == [{"question_id": "q1"}]


# ============================================================================
# collect_references: structured error
# ============================================================================


class TestCollectReferencesErrorStructure:
    def test_error_stored_as_structured_field(self, tmp_path, monkeypatch) -> None:
        from eval import collect_references as cr

        questions_data = {
            "metadata": {"source_documents": ["fake.pdf"]},
            "questions": [
                {
                    "question_id": "q1",
                    "question": "A valid question with sufficient length for testing?",
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
                    "question": "A valid test question that is sufficiently long?",
                    "reference_answers": [],
                }
            ],
        }
        input_path = tmp_path / "questions.json"
        output_path = tmp_path / "references.json"
        input_path.write_text(json.dumps(questions_data), encoding="utf-8")

        monkeypatch.setattr(cr, "get_reference_groq", lambda q, m: "Answer OK")

        cr.collect_references(
            questions_path=str(input_path),
            output_path=str(output_path),
            provider="groq",
            models=["model-ok"],
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))
        ref = data["questions"][0]["reference_answers"][0]
        assert ref["reference_answer"] == "Answer OK"
        assert ref["error"] is None


# ============================================================================
# judge: error filtering + smoke
# ============================================================================


class TestJudgeFiltersErrors:
    def _eval_results(self, refs: list[dict]) -> dict:
        return {
            "metadata": {},
            "results": [
                {
                    "question_id": "q1",
                    "question": "A valid test question?",
                    "sb100_answer": "SB100 answer",
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
                    "reference_answer": "Answer OK",
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
                    "reference_answer": "[ERRO] legacy-format marker",
                }
            ]
        )
        input_path = tmp_path / "eval.json"
        output_path = tmp_path / "judged.json"
        input_path.write_text(json.dumps(data), encoding="utf-8")

        def fake_judge(*_args: object, **_kwargs: object) -> dict:
            pytest.fail("Judge should not be called for refs with errors")

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

        # Same question → same position in both runs
        assert captured[0] == captured[1]


# ============================================================================
# report
# ============================================================================


@pytest.fixture
def sample_judged_dataset() -> dict:
    """Minimal judged dataset for testing report."""
    return {
        "metadata": {
            "total_questions": 2,
            "judge_model": "test-model",
            "judge_provider": "test",
        },
        "results": [
            {
                "question_id": "q1",
                "question": "Test question 1?",
                "sb100_answer": "SB100 answer 1",
                "reference_answers": [{"reference_model": "modelA", "reference_answer": "Ref A"}],
                "judgments": [
                    {
                        "reference_model": "modelA",
                        "judge_score": 7,
                        "reference_score": 5,
                        "judge_verdict": "better",
                        "judge_justification": "Justification 1",
                    }
                ],
            },
            {
                "question_id": "q2",
                "question": "Test question 2?",
                "sb100_answer": "SB100 answer 2",
                "reference_answers": [{"reference_model": "modelB", "reference_answer": "Ref B"}],
                "judgments": [
                    {
                        "reference_model": "modelB",
                        "judge_score": 4,
                        "reference_score": 6,
                        "judge_verdict": "worse",
                        "judge_justification": "Justification 2",
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
                "question": "A valid test question?",
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
        assert dist["7-8 (Good)"] == 1
        assert dist["3-4 (Weak)"] == 1

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
        assert "# Evaluation Report - SB100" in report_path.read_text(encoding="utf-8")

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
# Integration smoke: judge -> report
# ============================================================================


class TestPipelineSmoke:
    def test_judge_to_report_end_to_end(self, tmp_path, monkeypatch) -> None:
        from eval import judge as jd
        from eval import report as rp

        questions = [
            {
                "question_id": f"q-{i:02d}",
                "question": f"A valid test question number {i:02d}?",
                "reference_answers": [
                    {
                        "reference_model": "ref-m",
                        "reference_answer": f"ref answer {i}",
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
                    "sb100_answer": f"sb100 answer {q['question_id']}",
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
        assert "# Evaluation Report - SB100" in content


# ============================================================================
# run_evaluation: authentication of /chat (#90)
# ============================================================================


def _raise_for_status_error(status_code: int) -> Mock:
    """A response Mock whose raise_for_status raises an HTTPStatusError."""
    response = Mock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        str(status_code), request=Mock(), response=Mock(status_code=status_code)
    )
    return response


class TestEvalAuth:
    @staticmethod
    def _clear_credentials(monkeypatch) -> None:
        for var in ("EVAL_API_TOKEN", "EVAL_USERNAME", "EVAL_PASSWORD"):
            monkeypatch.delenv(var, raising=False)

    def test_explicit_token_is_used_directly(self, monkeypatch) -> None:
        self._clear_credentials(monkeypatch)
        monkeypatch.setenv("EVAL_API_TOKEN", "DIRECT-TOKEN")
        client = Mock()
        client.post = AsyncMock()

        token = asyncio.run(resolve_token(client, "http://test"))

        assert token == "DIRECT-TOKEN"
        client.post.assert_not_called()  # no /auth/token exchange

    def test_username_password_exchanged_for_token(self, monkeypatch) -> None:
        self._clear_credentials(monkeypatch)
        monkeypatch.setenv("EVAL_USERNAME", "evaluator")
        monkeypatch.setenv("EVAL_PASSWORD", "s3cret-pass")
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"access_token": "JWT-FROM-LOGIN", "token_type": "bearer"}
        client = Mock()
        client.post = AsyncMock(return_value=response)

        token = asyncio.run(resolve_token(client, "http://test"))

        assert token == "JWT-FROM-LOGIN"
        assert client.post.call_args[0][0] == "http://test/auth/token"
        # OAuth2 password flow uses a form body, not JSON.
        assert client.post.call_args[1]["data"] == {
            "username": "evaluator",
            "password": "s3cret-pass",
        }

    def test_missing_credentials_aborts_before_any_request(self, monkeypatch) -> None:
        self._clear_credentials(monkeypatch)
        client = Mock()
        client.post = AsyncMock()

        with pytest.raises(EvalAuthError):
            asyncio.run(resolve_token(client, "http://test"))
        client.post.assert_not_called()

    def test_token_exchange_failure_aborts_early(self, monkeypatch) -> None:
        self._clear_credentials(monkeypatch)
        monkeypatch.setenv("EVAL_USERNAME", "evaluator")
        monkeypatch.setenv("EVAL_PASSWORD", "wrong")
        client = Mock()
        client.post = AsyncMock(return_value=_raise_for_status_error(401))

        with pytest.raises(EvalAuthError):
            asyncio.run(resolve_token(client, "http://test"))

    def test_call_chat_api_sends_bearer_token(self) -> None:
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"answer": "ok", "hallucination_score": 0.1}
        client = Mock()
        client.post = AsyncMock(return_value=response)

        result = asyncio.run(call_chat_api(client, "question?", "http://test", token="TOK-XYZ"))

        assert result["success"] is True
        assert client.post.call_args[1]["headers"]["Authorization"] == "Bearer TOK-XYZ"

    def test_main_exits_nonzero_when_credentials_missing(self, tmp_path, monkeypatch) -> None:
        self._clear_credentials(monkeypatch)
        dataset = {
            "metadata": {},
            "questions": [
                {
                    "question_id": "q1",
                    "question": "A valid evaluation question of sufficient length?",
                    "reference_answers": [],
                }
            ],
        }
        input_path = tmp_path / "refs.json"
        input_path.write_text(json.dumps(dataset), encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_evaluation.py",
                "--input",
                str(input_path),
                "--output",
                str(tmp_path / "out.json"),
                "--checkpoint",
                str(tmp_path / "ck.json"),
            ],
        )
        # Missing credentials abort before any network call, so main exits non-zero.
        assert main() == 1
