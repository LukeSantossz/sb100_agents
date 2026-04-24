"""
Julgamento automatico por LLM.

Compara respostas do SB100 com respostas de referencia usando um LLM juiz.
O juiz fornece score numerico (0-10), justificativa e veredicto.

Uso:
    python eval/judge.py
    python eval/judge.py --model llama-3.3-70b-versatile --provider groq
"""

from pathlib import Path
from dotenv import load_dotenv

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / ".env")

import argparse
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

# Provider padrao
DEFAULT_PROVIDER = "groq"

# Modelo juiz padrao (distinto dos modelos de referencia)
DEFAULT_JUDGE_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "ollama": "llama3:70b",
    "openrouter": "google/gemma-4-31b-it",
}

# Configuracao OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Prompt do juiz - solicita score, justificativa e veredicto
JUDGE_PROMPT_TEMPLATE = """Voce e um avaliador especializado em agronomia. Sua tarefa e comparar duas respostas para uma pergunta tecnica e determinar qual e melhor.

**Pergunta:**
{question}

**Resposta A:**
{answer_a}

**Resposta B:**
{answer_b}

**Instrucoes de avaliacao:**
1. Avalie precisao tecnica, completude, clareza e utilidade pratica
2. Considere se as informacoes estao corretas para o contexto agricola brasileiro
3. Penalize respostas vagas, incorretas ou que nao respondem a pergunta

**Formato de resposta (JSON estrito):**
{{
    "score_a": <0-10>,
    "score_b": <0-10>,
    "justification": "<explicacao da avaliacao em 2-3 frases>",
    "verdict": "<A_better|B_better|equivalent>"
}}

Responda APENAS com o JSON, sem texto adicional."""


def judge_groq(
    question: str,
    answer_a: str,
    answer_b: str,
    model: str,
) -> dict:
    """Executa julgamento usando Groq API."""
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        answer_a=answer_a,
        answer_b=answer_b,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Baixa temperatura para consistencia
        max_tokens=500,
    )

    return parse_judge_response(response.choices[0].message.content)


def judge_ollama(
    question: str,
    answer_a: str,
    answer_b: str,
    model: str,
) -> dict:
    """Executa julgamento usando Ollama local."""
    import ollama

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        answer_a=answer_a,
        answer_b=answer_b,
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    return parse_judge_response(response["message"]["content"])


def judge_openrouter(
    question: str,
    answer_a: str,
    answer_b: str,
    model: str,
) -> dict:
    """Executa julgamento usando OpenRouter API (Gemma 4, etc)."""
    from openai import OpenAI

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        answer_a=answer_a,
        answer_b=answer_b,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
    )

    return parse_judge_response(response.choices[0].message.content)


def parse_judge_response(content: str) -> dict:
    """Extrai campos do JSON de resposta do juiz."""
    # Tenta extrair JSON
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return {
                "score_a": float(data.get("score_a", 5)),
                "score_b": float(data.get("score_b", 5)),
                "justification": str(data.get("justification", "")),
                "verdict": str(data.get("verdict", "equivalent")),
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: valores neutros
    return {
        "score_a": 5.0,
        "score_b": 5.0,
        "justification": f"[PARSE ERROR] {content[:200]}",
        "verdict": "equivalent",
    }


def normalize_verdict(verdict: str, sb100_was_a: bool) -> str:
    """
    Normaliza veredicto para perspectiva do SB100.

    Args:
        verdict: Veredicto original (A_better, B_better, equivalent)
        sb100_was_a: Se SB100 estava na posicao A

    Returns:
        Veredicto normalizado (better, worse, equivalent)
    """
    verdict = verdict.lower().strip()

    if "equivalent" in verdict or "equal" in verdict:
        return "equivalent"

    if "a_better" in verdict or "a better" in verdict:
        return "better" if sb100_was_a else "worse"

    if "b_better" in verdict or "b better" in verdict:
        return "worse" if sb100_was_a else "better"

    return "equivalent"


def run_judge(
    input_path: str = "eval/results/evaluation_results.json",
    output_path: str = "eval/results/judged_results.json",
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
) -> dict:
    """
    Executa julgamento de todas as comparacoes.

    Args:
        input_path: Caminho do dataset com resultados da avaliacao
        output_path: Caminho do arquivo de saida
        provider: Provider LLM (groq ou ollama)
        model: Modelo juiz

    Returns:
        Dataset com julgamentos
    """
    if model is None:
        model = DEFAULT_JUDGE_MODELS[provider]

    judge_fns = {
        "groq": judge_groq,
        "ollama": judge_ollama,
        "openrouter": judge_openrouter,
    }
    judge_fn = judge_fns[provider]

    # Carrega dataset
    with open(input_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = dataset["results"]
    print(f"Carregados {len(results)} resultados de {input_path}")
    print(f"Modelo juiz: {model} ({provider})")

    # Processa cada resultado
    judged_results = []
    random.seed(42)  # Reproducibilidade

    for result in tqdm(results, desc="Julgando respostas"):
        sb100_answer = result.get("sb100_answer", "")
        reference_answers = result.get("reference_answers", [])

        if not result.get("sb100_success", True):
            # Pula resultados com erro
            judged_results.append(
                {
                    **result,
                    "judgments": [],
                }
            )
            continue

        judgments = []

        for ref in reference_answers:
            ref_model = ref.get("reference_model", "unknown")
            ref_answer = ref.get("reference_answer", "")

            if not ref_answer or ref_answer.startswith("[ERRO]"):
                continue

            # Alterna ordem para evitar vies de posicao (50% cada)
            sb100_is_a = random.random() < 0.5

            if sb100_is_a:
                answer_a, answer_b = sb100_answer, ref_answer
            else:
                answer_a, answer_b = ref_answer, sb100_answer

            try:
                judge_result = judge_fn(
                    result["question"],
                    answer_a,
                    answer_b,
                    model,
                )

                # Normaliza scores e veredicto para perspectiva SB100
                if sb100_is_a:
                    sb100_score = judge_result["score_a"]
                    ref_score = judge_result["score_b"]
                else:
                    sb100_score = judge_result["score_b"]
                    ref_score = judge_result["score_a"]

                verdict = normalize_verdict(judge_result["verdict"], sb100_is_a)

                judgments.append(
                    {
                        "reference_model": ref_model,
                        "judge_score": sb100_score,
                        "reference_score": ref_score,
                        "judge_verdict": verdict,
                        "judge_justification": judge_result["justification"],
                        "sb100_position": "A" if sb100_is_a else "B",
                    }
                )

            except Exception as e:
                judgments.append(
                    {
                        "reference_model": ref_model,
                        "judge_score": None,
                        "reference_score": None,
                        "judge_verdict": "error",
                        "judge_justification": f"[ERRO] {str(e)}",
                        "sb100_position": "A" if sb100_is_a else "B",
                    }
                )

        judged_results.append(
            {
                **result,
                "judgments": judgments,
            }
        )

    # Monta dataset final
    judged_dataset = {
        "metadata": {
            **dataset.get("metadata", {}),
            "judge_model": model,
            "judge_provider": provider,
            "judged_at": datetime.now(timezone.utc).isoformat(),
        },
        "results": judged_results,
    }

    # Salva resultados
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(judged_dataset, f, ensure_ascii=False, indent=2)

    print(f"\nResultados julgados salvos em: {output}")

    # Estatisticas rapidas
    all_judgments = [j for r in judged_results for j in r.get("judgments", [])]
    valid = [j for j in all_judgments if j.get("judge_score") is not None]

    if valid:
        avg_score = sum(j["judge_score"] for j in valid) / len(valid)
        better = sum(1 for j in valid if j["judge_verdict"] == "better")
        equiv = sum(1 for j in valid if j["judge_verdict"] == "equivalent")
        worse = sum(1 for j in valid if j["judge_verdict"] == "worse")

        print(f"Score medio SB100: {avg_score:.2f}")
        print(f"Veredictos: better={better}, equivalent={equiv}, worse={worse}")

    return judged_dataset


def main():
    parser = argparse.ArgumentParser(description="Executa julgamento automatico das respostas")
    parser.add_argument(
        "--input",
        default="eval/results/evaluation_results.json",
        help="Caminho dos resultados da avaliacao (padrao: eval/results/evaluation_results.json)",
    )
    parser.add_argument(
        "--output",
        default="eval/results/judged_results.json",
        help="Caminho do arquivo de saida (padrao: eval/results/judged_results.json)",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter"],
        default=DEFAULT_PROVIDER,
        help=f"Provider LLM (padrao: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--model",
        help="Modelo juiz (padrao depende do provider)",
    )

    args = parser.parse_args()

    # Valida provider
    if args.provider == "groq" and not os.environ.get("GROQ_API_KEY"):
        print("Erro: GROQ_API_KEY nao definida. Use --provider ollama ou defina a variavel.")
        return 1

    if args.provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        print("Erro: OPENROUTER_API_KEY nao definida. Use --provider ollama ou defina a variavel.")
        return 1

    # Verifica se arquivo de entrada existe
    if not Path(args.input).exists():
        print(f"Erro: Arquivo de entrada nao encontrado: {args.input}")
        print("Execute primeiro: python eval/run_evaluation.py")
        return 1

    # Executa julgamento
    run_judge(
        input_path=args.input,
        output_path=args.output,
        provider=args.provider,
        model=args.model,
    )

    return 0


if __name__ == "__main__":
    exit(main())
