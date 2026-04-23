"""
Coleta respostas de referencia de modelos open-source.

Itera sobre o dataset de perguntas gerado por generate_questions.py
e coleta respostas de ao menos dois modelos open-source.

Uso:
    python eval/collect_references.py
    python eval/collect_references.py --models llama3:8b,mistral:7b --provider ollama
    python eval/collect_references.py --models llama-3.1-8b-instant,gemma2-9b-it --provider groq
"""

from pathlib import Path
from dotenv import load_dotenv

# Carrega variaveis de ambiente do .env
load_dotenv(Path(__file__).parent.parent / ".env")

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tqdm import tqdm

# Providers disponiveis: groq, ollama, openrouter
DEFAULT_PROVIDER = "groq"

# Modelos padrao por provider
DEFAULT_MODELS = {
    "groq": ["llama-3.1-8b-instant", "gemma2-9b-it"],
    "ollama": ["llama3:8b", "mistral:7b"],
    "openrouter": ["google/gemma-4-31b-it", "google/gemma-4-26b-a4b-it"],
}

# Configuracao OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Prompt para resposta de referencia
REFERENCE_ANSWER_PROMPT = """Voce e um assistente especializado em agronomia e agricultura brasileira.
Responda a seguinte pergunta de forma clara, objetiva e tecnicamente precisa.
Use seu conhecimento para fornecer a melhor resposta possivel.

Pergunta: {question}

Resposta:"""


def get_reference_groq(
    question: str,
    model: str,
) -> str:
    """Obtem resposta de referencia usando Groq API."""
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = REFERENCE_ANSWER_PROMPT.format(question=question)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    return response.choices[0].message.content.strip()


def get_reference_ollama(
    question: str,
    model: str,
) -> str:
    """Obtem resposta de referencia usando Ollama local."""
    import ollama

    prompt = REFERENCE_ANSWER_PROMPT.format(question=question)

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"].strip()


def get_reference_openrouter(
    question: str,
    model: str,
) -> str:
    """Obtem resposta de referencia usando OpenRouter API (Gemma 4, etc)."""
    from openai import OpenAI

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

    prompt = REFERENCE_ANSWER_PROMPT.format(question=question)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    return response.choices[0].message.content.strip()


def collect_references(
    questions_path: str = "eval/dataset/questions.json",
    output_path: str = "eval/dataset/reference_answers.json",
    provider: str = DEFAULT_PROVIDER,
    models: Optional[list[str]] = None,
) -> dict:
    """
    Coleta respostas de referencia para todas as perguntas.

    Args:
        questions_path: Caminho do dataset de perguntas
        output_path: Caminho do arquivo de saida
        provider: Provider LLM (groq ou ollama)
        models: Lista de modelos a usar

    Returns:
        Dataset com respostas de referencia
    """
    if models is None:
        models = DEFAULT_MODELS[provider]

    get_reference_fns = {
        "groq": get_reference_groq,
        "ollama": get_reference_ollama,
        "openrouter": get_reference_openrouter,
    }
    get_reference_fn = get_reference_fns[provider]

    # Carrega dataset de perguntas
    with open(questions_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    questions = dataset["questions"]
    print(f"Carregadas {len(questions)} perguntas de {questions_path}")
    print(f"Modelos de referencia: {models}")
    print(f"Provider: {provider}")

    # Coleta respostas
    for question_obj in tqdm(questions, desc="Coletando respostas"):
        question = question_obj["question"]

        for model in models:
            # Verifica se ja tem resposta deste modelo
            existing = [
                r for r in question_obj["reference_answers"]
                if r["reference_model"] == model
            ]
            if existing:
                continue

            try:
                answer = get_reference_fn(question, model)
                question_obj["reference_answers"].append({
                    "reference_model": model,
                    "reference_answer": answer,
                })
            except Exception as e:
                print(f"\nErro com modelo {model}: {e}")
                question_obj["reference_answers"].append({
                    "reference_model": model,
                    "reference_answer": f"[ERRO] {str(e)}",
                })

    # Atualiza metadata
    dataset["metadata"]["reference_models"] = models
    dataset["metadata"]["references_collected_at"] = datetime.now(timezone.utc).isoformat()
    dataset["metadata"]["reference_provider"] = provider

    # Salva dataset
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\nDataset com referencias salvo em: {output}")

    # Estatisticas
    total_refs = sum(len(q["reference_answers"]) for q in questions)
    print(f"Total de respostas coletadas: {total_refs}")

    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Coleta respostas de referencia de modelos open-source"
    )
    parser.add_argument(
        "--input",
        default="eval/dataset/questions.json",
        help="Caminho do dataset de perguntas (padrao: eval/dataset/questions.json)",
    )
    parser.add_argument(
        "--output",
        default="eval/dataset/reference_answers.json",
        help="Caminho do arquivo de saida (padrao: eval/dataset/reference_answers.json)",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter"],
        default=DEFAULT_PROVIDER,
        help=f"Provider LLM (padrao: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--models",
        help="Modelos separados por virgula (padrao depende do provider)",
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
        print("Execute primeiro: python eval/generate_questions.py <documento>")
        return 1

    # Parse models
    models = None
    if args.models:
        models = [m.strip() for m in args.models.split(",")]

    # Coleta referencias
    collect_references(
        questions_path=args.input,
        output_path=args.output,
        provider=args.provider,
        models=models,
    )

    return 0


if __name__ == "__main__":
    exit(main())
