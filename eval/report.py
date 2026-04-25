"""
Geracao de relatorio sumario da avaliacao.

Gera relatorio com:
- Distribuicao de scores (tabela de frequencias)
- Percentual de veredictos por modelo de referencia
- Media e mediana de judge_score
- Amostra humana (10%) exportada para CSV

Uso:
    python eval/report.py
    python eval/report.py --sample-size 30
"""

import argparse
import csv
import json
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median


def load_judged_results(input_path: str) -> dict:
    """Carrega dataset com resultados julgados."""
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def extract_all_judgments(results: list[dict]) -> list[dict]:
    """Extrai todos os julgamentos validos dos resultados."""
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
    """Gera distribuicao de scores."""
    scores = [j["judge_score"] for j in judgments]

    # Agrupa em faixas
    distribution = Counter()
    for score in scores:
        if score <= 2:
            distribution["0-2 (Ruim)"] += 1
        elif score <= 4:
            distribution["3-4 (Fraco)"] += 1
        elif score <= 6:
            distribution["5-6 (Regular)"] += 1
        elif score <= 8:
            distribution["7-8 (Bom)"] += 1
        else:
            distribution["9-10 (Excelente)"] += 1

    return dict(sorted(distribution.items()))


def generate_verdict_stats(judgments: list[dict]) -> dict:
    """Gera estatisticas de veredictos por modelo."""
    by_model = {}

    for j in judgments:
        model = j["reference_model"]
        if model not in by_model:
            by_model[model] = {"better": 0, "equivalent": 0, "worse": 0, "total": 0}

        by_model[model][j["judge_verdict"]] += 1
        by_model[model]["total"] += 1

    # Calcula percentuais
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
    """Gera relatorio em formato Markdown."""
    scores = [j["judge_score"] for j in judgments]

    report = f"""# Relatorio de Avaliacao - SB100

**Gerado em:** {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Resumo

| Metrica | Valor |
|---------|-------|
| Total de perguntas | {metadata.get("total_questions", len(judgments))} |
| Total de julgamentos | {len(judgments)} |
| Modelo juiz | {metadata.get("judge_model", "N/A")} |
| Provider | {metadata.get("judge_provider", "N/A")} |

## Scores do SB100

| Metrica | Valor |
|---------|-------|
| Media | {mean(scores):.2f} |
| Mediana | {median(scores):.2f} |
| Minimo | {min(scores):.1f} |
| Maximo | {max(scores):.1f} |

### Distribuicao de Scores

| Faixa | Quantidade | Percentual |
|-------|------------|------------|
"""

    total = len(scores)
    for faixa, count in score_distribution.items():
        pct = round(100 * count / total, 1)
        report += f"| {faixa} | {count} | {pct}% |\n"

    report += """
## Veredictos por Modelo de Referencia

| Modelo | Better | Equivalent | Worse | Total |
|--------|--------|------------|-------|-------|
"""

    for model, stats in verdict_stats.items():
        report += (
            f"| {model} | "
            f"{stats['better']} ({stats['better_pct']}%) | "
            f"{stats['equivalent']} ({stats['equivalent_pct']}%) | "
            f"{stats['worse']} ({stats['worse_pct']}%) | "
            f"{stats['total']} |\n"
        )

    # Totais gerais
    total_better = sum(s["better"] for s in verdict_stats.values())
    total_equiv = sum(s["equivalent"] for s in verdict_stats.values())
    total_worse = sum(s["worse"] for s in verdict_stats.values())
    grand_total = total_better + total_equiv + total_worse

    if grand_total > 0:
        report += f"""
### Totais Gerais

| Veredicto | Quantidade | Percentual |
|-----------|------------|------------|
| SB100 Melhor | {total_better} | {round(100 * total_better / grand_total, 1)}% |
| Equivalente | {total_equiv} | {round(100 * total_equiv / grand_total, 1)}% |
| SB100 Pior | {total_worse} | {round(100 * total_worse / grand_total, 1)}% |
"""

    report += """
## Notas

- **Better**: SB100 teve resposta melhor que o modelo de referencia
- **Equivalent**: Respostas de qualidade similar
- **Worse**: Modelo de referencia teve resposta melhor

---

*Relatorio gerado automaticamente pelo pipeline de avaliacao SB100.*
"""

    return report


def export_human_sample(
    judgments: list[dict],
    output_path: str,
    sample_size: int = 30,
) -> list[dict]:
    """
    Exporta amostra aleatoria para validacao humana.

    Args:
        judgments: Lista de julgamentos
        output_path: Caminho do CSV de saida
        sample_size: Tamanho da amostra (padrao: 30 = 10% de 300)

    Returns:
        Lista com os itens da amostra
    """
    random.seed(42)  # Reproducibilidade

    # Seleciona amostra
    sample_size = min(sample_size, len(judgments))
    sample = random.sample(judgments, sample_size)

    # Exporta CSV
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
    input_path: str = "eval/results/judged_results.json",
    report_path: str = "eval/results/report.md",
    sample_path: str = "eval/results/human_sample.csv",
    sample_size: int = 30,
) -> None:
    """
    Gera relatorio completo da avaliacao.

    Args:
        input_path: Caminho do dataset julgado
        report_path: Caminho do relatorio MD
        sample_path: Caminho do CSV de amostra humana
        sample_size: Tamanho da amostra humana
    """
    # Carrega dados
    dataset = load_judged_results(input_path)
    results = dataset.get("results", [])
    metadata = dataset.get("metadata", {})

    print(f"Carregados {len(results)} resultados de {input_path}")

    # Extrai julgamentos
    judgments = extract_all_judgments(results)
    print(f"Total de julgamentos validos: {len(judgments)}")

    if not judgments:
        print("Nenhum julgamento encontrado. Verifique o arquivo de entrada.")
        return

    # Gera estatisticas
    score_distribution = generate_score_distribution(judgments)
    verdict_stats = generate_verdict_stats(judgments)

    # Gera relatorio MD
    report = generate_report_markdown(
        metadata,
        judgments,
        score_distribution,
        verdict_stats,
    )

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Relatorio salvo em: {report_path}")

    # Exporta amostra humana
    sample = export_human_sample(judgments, sample_path, sample_size)
    print(f"Amostra humana ({len(sample)} itens) salva em: {sample_path}")


def main():
    parser = argparse.ArgumentParser(description="Gera relatorio sumario da avaliacao")
    parser.add_argument(
        "--input",
        default="eval/results/judged_results.json",
        help="Caminho do dataset julgado (padrao: eval/results/judged_results.json)",
    )
    parser.add_argument(
        "--report",
        default="eval/results/report.md",
        help="Caminho do relatorio (padrao: eval/results/report.md)",
    )
    parser.add_argument(
        "--sample",
        default="eval/results/human_sample.csv",
        help="Caminho do CSV de amostra humana (padrao: eval/results/human_sample.csv)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help="Tamanho da amostra humana (padrao: 30)",
    )

    args = parser.parse_args()

    # Verifica se arquivo de entrada existe
    if not Path(args.input).exists():
        print(f"Erro: Arquivo de entrada nao encontrado: {args.input}")
        print("Execute primeiro: python eval/judge.py")
        return 1

    # Gera relatorio
    generate_report(
        input_path=args.input,
        report_path=args.report,
        sample_path=args.sample,
        sample_size=args.sample_size,
    )

    return 0


if __name__ == "__main__":
    exit(main())
