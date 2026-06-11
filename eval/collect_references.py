"""
Collect reference answers from open-source models.

Iterates over the question dataset produced by generate_questions.py
and collects answers from at least two open-source models.

Usage:
    python eval/collect_references.py
    python eval/collect_references.py --models llama3:8b,mistral:7b --provider ollama
    python eval/collect_references.py --models llama-3.1-8b-instant,gemma2-9b-it --provider groq
"""

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import argparse
import json
import os
import sys
from datetime import UTC, datetime

from tqdm import tqdm

# Allow `from eval._utils import ...` when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval._utils import (
    DEFAULT_QUESTIONS_PATH,
    DEFAULT_REFERENCES_PATH,
    validate_dataset_schema,
)

# Available providers: groq, ollama, openrouter
DEFAULT_PROVIDER = "groq"

# Default models per provider
DEFAULT_MODELS = {
    "groq": ["llama-3.1-8b-instant", "gemma2-9b-it"],
    "ollama": ["llama3:8b", "mistral:7b"],
    "openrouter": ["google/gemma-4-31b-it", "google/gemma-4-26b-a4b-it"],
}

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Prompt for reference answers
REFERENCE_ANSWER_PROMPT = """You are an assistant specialized in agronomy and Brazilian agriculture.
Answer the following question clearly, objectively and with technical precision.
Use your knowledge to provide the best possible answer.
Write the answer in Portuguese (pt-BR).

Question: {question}

Answer:"""


def get_reference_groq(
    question: str,
    model: str,
) -> str:
    """Get a reference answer using the Groq API."""
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
    """Get a reference answer using local Ollama."""
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
    """Get a reference answer using the OpenRouter API (Gemma 4, etc)."""
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
    questions_path: str = str(DEFAULT_QUESTIONS_PATH),
    output_path: str = str(DEFAULT_REFERENCES_PATH),
    provider: str = DEFAULT_PROVIDER,
    models: list[str] | None = None,
) -> dict:
    """
    Collect reference answers for every question.

    Args:
        questions_path: Path to the question dataset
        output_path: Path to the output file
        provider: LLM provider (groq or ollama)
        models: List of models to use

    Returns:
        Dataset with reference answers
    """
    if models is None:
        models = DEFAULT_MODELS[provider]

    get_reference_fns = {
        "groq": get_reference_groq,
        "ollama": get_reference_ollama,
        "openrouter": get_reference_openrouter,
    }
    get_reference_fn = get_reference_fns[provider]

    # Load question dataset
    with open(questions_path, encoding="utf-8") as f:
        dataset = json.load(f)

    validate_dataset_schema(dataset, ["metadata", "questions"])

    questions = dataset["questions"]
    print(f"Loaded {len(questions)} questions from {questions_path}")
    print(f"Reference models: {models}")
    print(f"Provider: {provider}")

    # Collect answers
    for question_obj in tqdm(questions, desc="Collecting answers"):
        question = question_obj["question"]

        for model in models:
            # Skip if this model already has an answer
            existing = [
                r for r in question_obj["reference_answers"] if r["reference_model"] == model
            ]
            if existing:
                continue

            try:
                answer = get_reference_fn(question, model)
                question_obj["reference_answers"].append(
                    {
                        "reference_model": model,
                        "reference_answer": answer,
                        "error": None,
                    }
                )
            except Exception as e:  # noqa: BLE001 - propagated via `error` field
                print(f"\nError with model {model}: {e}")
                question_obj["reference_answers"].append(
                    {
                        "reference_model": model,
                        "reference_answer": None,
                        "error": str(e),
                    }
                )

    # Update metadata
    dataset["metadata"]["reference_models"] = models
    dataset["metadata"]["references_collected_at"] = datetime.now(UTC).isoformat()
    dataset["metadata"]["reference_provider"] = provider

    # Save dataset
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\nDataset with references saved to: {output}")

    # Statistics
    total_refs = sum(len(q["reference_answers"]) for q in questions)
    print(f"Total answers collected: {total_refs}")

    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Collect reference answers from open-source models"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_QUESTIONS_PATH),
        help=f"Path to the question dataset (default: {DEFAULT_QUESTIONS_PATH})",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REFERENCES_PATH),
        help=f"Path to the output file (default: {DEFAULT_REFERENCES_PATH})",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter"],
        default=DEFAULT_PROVIDER,
        help=f"LLM provider (default: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--models",
        help="Comma-separated models (default depends on provider)",
    )

    args = parser.parse_args()

    # Validate provider
    if args.provider == "groq" and not os.environ.get("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not set. Use --provider ollama or set the variable.")
        return 1

    if args.provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set. Use --provider ollama or set the variable.")
        return 1

    # Check that the input file exists
    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}")
        print("Run first: python eval/generate_questions.py <document>")
        return 1

    # Parse models
    models = None
    if args.models:
        models = [m.strip() for m in args.models.split(",")]

    # Collect references
    collect_references(
        questions_path=args.input,
        output_path=args.output,
        provider=args.provider,
        models=models,
    )

    return 0


if __name__ == "__main__":
    exit(main())
