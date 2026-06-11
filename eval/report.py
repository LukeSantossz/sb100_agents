"""
Evaluation summary report generation.

Produces a report with:
- Score distribution (frequency table)
- Verdict percentages per reference model
- Mean and median of judge_score
- Human sample (10%) exported to CSV

Usage:
    python eval/report.py
    python eval/report.py --sample-size 30
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median

# Allow `from eval._utils import ...` when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval._utils import (
    DEFAULT_HUMAN_SAMPLE_PATH,
    DEFAULT_JUDGED_RESULTS_PATH,
    DEFAULT_REPORT_PATH,
    validate_dataset_schema,
)


def load_judged_results(input_path: str) -> dict:
    """Load the dataset with judged results."""
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def extract_all_judgments(results: list[dict]) -> list[dict]:
    """Extract every valid judgment from the results."""
    judgments = []
    for result in results:
        question = result.get("question", "")
        sb100_answer = result.get("sb100_answer", "")

        for j in result.get("judgments", []):
            if j.get("judge_score") is not None:
                judgments.append(
                    {
                        "question": question,
                        "sb100_answer": sb100_answer,
                        "reference_model": j.get("reference_model", ""),
                        "reference_answer": next(
                            (
                                r["reference_answer"]
                                for r in result.get("reference_answers", [])
                                if r["reference_model"] == j["reference_model"]
                            ),
                            "",
                        ),
                        "judge_score": j["judge_score"],
                        "reference_score": j.get("reference_score", 0),
                        "judge_verdict": j["judge_verdict"],
                        "judge_justification": j.get("judge_justification", ""),
                    }
                )

    return judgments


def generate_score_distribution(judgments: list[dict]) -> dict:
    """Generate the score distribution."""
    scores = [j["judge_score"] for j in judgments]

    # Group into bands
    distribution = Counter()
    for score in scores:
        if score <= 2:
            distribution["0-2 (Poor)"] += 1
        elif score <= 4:
            distribution["3-4 (Weak)"] += 1
        elif score <= 6:
            distribution["5-6 (Fair)"] += 1
        elif score <= 8:
            distribution["7-8 (Good)"] += 1
        else:
            distribution["9-10 (Excellent)"] += 1

    return dict(sorted(distribution.items()))


def generate_verdict_stats(judgments: list[dict]) -> dict:
    """Generate verdict statistics per model."""
    by_model = {}

    for j in judgments:
        model = j["reference_model"]
        if model not in by_model:
            by_model[model] = {"better": 0, "equivalent": 0, "worse": 0, "total": 0}

        by_model[model][j["judge_verdict"]] += 1
        by_model[model]["total"] += 1

    # Compute percentages
    for _model, stats in by_model.items():
        total = stats["total"]
        if total > 0:
            stats["better_pct"] = round(100 * stats["better"] / total, 1)
            stats["equivalent_pct"] = round(100 * stats["equivalent"] / total, 1)
            stats["worse_pct"] = round(100 * stats["worse"] / total, 1)

    return by_model


def generate_report_markdown(
    metadata: dict,
    judgments: list[dict],
    score_distribution: dict,
    verdict_stats: dict,
) -> str:
    """Generate the report in Markdown format."""
    scores = [j["judge_score"] for j in judgments]

    report = f"""# Evaluation Report - SB100

**Generated at:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Summary

| Metric | Value |
|--------|-------|
| Total questions | {metadata.get("total_questions", len(judgments))} |
| Total judgments | {len(judgments)} |
| Judge model | {metadata.get("judge_model", "N/A")} |
| Provider | {metadata.get("judge_provider", "N/A")} |

## SB100 Scores

| Metric | Value |
|--------|-------|
| Mean | {mean(scores):.2f} |
| Median | {median(scores):.2f} |
| Min | {min(scores):.1f} |
| Max | {max(scores):.1f} |

### Score Distribution

| Band | Count | Percentage |
|------|-------|------------|
"""

    total = len(scores)
    for band, count in score_distribution.items():
        pct = round(100 * count / total, 1)
        report += f"| {band} | {count} | {pct}% |\n"

    report += """
## Verdicts per Reference Model

| Model | Better | Equivalent | Worse | Total |
|-------|--------|------------|-------|-------|
"""

    for model, stats in verdict_stats.items():
        report += (
            f"| {model} | "
            f"{stats['better']} ({stats['better_pct']}%) | "
            f"{stats['equivalent']} ({stats['equivalent_pct']}%) | "
            f"{stats['worse']} ({stats['worse_pct']}%) | "
            f"{stats['total']} |\n"
        )

    # Grand totals
    total_better = sum(s["better"] for s in verdict_stats.values())
    total_equiv = sum(s["equivalent"] for s in verdict_stats.values())
    total_worse = sum(s["worse"] for s in verdict_stats.values())
    grand_total = total_better + total_equiv + total_worse

    if grand_total > 0:
        report += f"""
### Grand Totals

| Verdict | Count | Percentage |
|---------|-------|------------|
| SB100 Better | {total_better} | {round(100 * total_better / grand_total, 1)}% |
| Equivalent | {total_equiv} | {round(100 * total_equiv / grand_total, 1)}% |
| SB100 Worse | {total_worse} | {round(100 * total_worse / grand_total, 1)}% |
"""

    report += """
## Notes

- **Better**: SB100 answered better than the reference model
- **Equivalent**: Answers of similar quality
- **Worse**: The reference model answered better

---

*Report generated automatically by the SB100 evaluation pipeline.*
"""

    return report


def export_human_sample(
    judgments: list[dict],
    output_path: str,
    sample_size: int = 30,
) -> list[dict]:
    """
    Export a random sample for human validation.

    Args:
        judgments: List of judgments
        output_path: Path to the output CSV
        sample_size: Sample size (default: 30 = 10% of 300)

    Returns:
        List with the sampled items
    """
    random.seed(42)  # Reproducibility

    # Select sample
    sample_size = min(sample_size, len(judgments))
    sample = random.sample(judgments, sample_size)

    # Export CSV
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "question",
                "sb100_answer",
                "reference_model",
                "reference_answer",
                "judge_score",
                "judge_verdict",
                "judge_justification",
            ],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()

        for item in sample:
            writer.writerow(
                {
                    "question": item["question"],
                    "sb100_answer": item["sb100_answer"],
                    "reference_model": item["reference_model"],
                    "reference_answer": item["reference_answer"],
                    "judge_score": item["judge_score"],
                    "judge_verdict": item["judge_verdict"],
                    "judge_justification": item["judge_justification"],
                }
            )

    return sample


def generate_report(
    input_path: str = str(DEFAULT_JUDGED_RESULTS_PATH),
    report_path: str = str(DEFAULT_REPORT_PATH),
    sample_path: str = str(DEFAULT_HUMAN_SAMPLE_PATH),
    sample_size: int = 30,
) -> bool:
    """
    Generate the full evaluation report.

    Args:
        input_path: Path to the judged dataset
        report_path: Path to the MD report
        sample_path: Path to the human-sample CSV
        sample_size: Human sample size

    Returns:
        True if the report was generated; False if there were no valid judgments.
    """
    # Load data
    dataset = load_judged_results(input_path)
    validate_dataset_schema(dataset, ["results"])
    results = dataset.get("results", [])
    metadata = dataset.get("metadata", {})

    print(f"Loaded {len(results)} results from {input_path}")

    # Extract judgments
    judgments = extract_all_judgments(results)
    print(f"Total valid judgments: {len(judgments)}")

    if not judgments:
        print("No judgments found. Check the input file.")
        return False

    # Generate statistics
    score_distribution = generate_score_distribution(judgments)
    verdict_stats = generate_verdict_stats(judgments)

    # Generate MD report
    report = generate_report_markdown(
        metadata,
        judgments,
        score_distribution,
        verdict_stats,
    )

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to: {report_path}")

    # Export human sample
    sample = export_human_sample(judgments, sample_path, sample_size)
    print(f"Human sample ({len(sample)} items) saved to: {sample_path}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Generate the evaluation summary report")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_JUDGED_RESULTS_PATH),
        help=f"Path to the judged dataset (default: {DEFAULT_JUDGED_RESULTS_PATH})",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help=f"Path to the report (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--sample",
        default=str(DEFAULT_HUMAN_SAMPLE_PATH),
        help=f"Path to the human-sample CSV (default: {DEFAULT_HUMAN_SAMPLE_PATH})",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help="Human sample size (default: 30)",
    )

    args = parser.parse_args()

    # Check that the input file exists
    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}")
        print("Run first: python eval/judge.py")
        return 1

    # Generate report; exit 1 when there are no valid judgments
    ok = generate_report(
        input_path=args.input,
        report_path=args.report,
        sample_path=args.sample,
        sample_size=args.sample_size,
    )

    return 0 if ok else 1


if __name__ == "__main__":
    exit(main())
