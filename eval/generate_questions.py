"""
Question generator from PDF/TXT documents.

Uses an LLM (Groq API or local Ollama) to extract and formulate
agriculture-domain questions from document content.

Usage:
    python eval/generate_questions.py ./archives/boletim_sb100.pdf --num-questions 300
    python eval/generate_questions.py ./archives/ --num-questions 300 --provider ollama
"""

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import argparse
import json
import os
import re
import sys
import uuid
from datetime import UTC, datetime

import fitz  # PyMuPDF

# Allow `from eval._utils import ...` when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval._utils import DEFAULT_QUESTIONS_PATH, is_valid_question

# Available providers: groq, ollama, openrouter
DEFAULT_PROVIDER = "groq"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OPENROUTER_MODEL = "google/gemma-4-31b-it"

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Prompt for question generation
QUESTION_GENERATION_PROMPT = """You are an expert in agronomy and Brazilian agriculture.
Based on the following excerpt from a technical document, generate {num_questions} relevant
and diverse questions.

The questions must:
- Be specific and technical, covering different aspects of the content
- Vary in complexity (some for beginners, others for experts)
- Cover different topics mentioned in the text
- Be clear and objective
- Be written in Portuguese (pt-BR)

Return ONLY a JSON array with the questions, no extra explanations.
Format: ["question 1", "question 2", ...]

Document excerpt:
---
{text_chunk}
---

JSON array with {num_questions} questions:"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from every page of the PDF."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)
    doc.close()
    return "\n".join(pages_text)


def extract_text_from_txt(txt_path: str) -> str:
    """Read the content of a TXT file."""
    with open(txt_path, encoding="utf-8") as f:
        return f.read()


def extract_text(file_path: str) -> str:
    """Extract text from a PDF or TXT file."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    elif path.suffix.lower() == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported format: {path.suffix}")


def split_into_chunks(text: str, chunk_size: int = 4000, overlap: int = 500) -> list[str]:
    """Split text into chunks for LLM processing."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def generate_questions_groq(
    text_chunk: str,
    num_questions: int,
    model: str = DEFAULT_GROQ_MODEL,
) -> list[str]:
    """Generate questions using the Groq API."""
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = QUESTION_GENERATION_PROMPT.format(
        text_chunk=text_chunk,
        num_questions=num_questions,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()
    return parse_questions_json(content)


def generate_questions_ollama(
    text_chunk: str,
    num_questions: int,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> list[str]:
    """Generate questions using local Ollama."""
    import ollama

    prompt = QUESTION_GENERATION_PROMPT.format(
        text_chunk=text_chunk,
        num_questions=num_questions,
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response["message"]["content"].strip()
    return parse_questions_json(content)


def generate_questions_openrouter(
    text_chunk: str,
    num_questions: int,
    model: str = DEFAULT_OPENROUTER_MODEL,
) -> list[str]:
    """Generate questions using the OpenRouter API (Gemma 4, etc)."""
    from openai import OpenAI

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

    prompt = QUESTION_GENERATION_PROMPT.format(
        text_chunk=text_chunk,
        num_questions=num_questions,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()
    return parse_questions_json(content)


def parse_questions_json(content: str) -> list[str]:
    """Extract the question list from the JSON returned by the LLM.

    Applies the `is_valid_question` quality filter (contains '?', 20-500
    chars) to discard LLM noise (empty lines, fragments, preambles).
    """
    candidates: list[str] = []

    # Try to extract a JSON array from the content
    json_match = re.search(r"\[.*\]", content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                candidates = [q for q in parsed if isinstance(q, str) and q.strip()]
        except json.JSONDecodeError:
            pass

    if not candidates:
        # Fallback: extract lines that look like questions
        for raw_line in content.split("\n"):
            line = raw_line.strip()
            # Strip numbered prefixes
            line = re.sub(r"^[\d]+[.\-\)]\s*", "", line)
            line = re.sub(r'^["\']\s*', "", line)
            line = re.sub(r'\s*["\']$', "", line)
            if line and "?" in line:
                candidates.append(line)

    return [q.strip() for q in candidates if is_valid_question(q)]


def collect_files(path: str) -> list[str]:
    """Collect PDF/TXT files from a path (file or directory)."""
    p = Path(path)
    if p.is_file():
        return [str(p)]
    elif p.is_dir():
        files = list(p.glob("**/*.pdf")) + list(p.glob("**/*.txt"))
        return [str(f) for f in files]
    else:
        raise ValueError(f"Path not found: {path}")


def generate_questions_from_files(
    file_paths: list[str],
    num_questions: int = 300,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
) -> dict:
    """
    Generate questions from a list of files.

    Returns:
        Structured dataset with metadata and questions
    """
    if model is None:
        model_defaults = {
            "groq": DEFAULT_GROQ_MODEL,
            "ollama": DEFAULT_OLLAMA_MODEL,
            "openrouter": DEFAULT_OPENROUTER_MODEL,
        }
        model = model_defaults[provider]

    generate_fns = {
        "groq": generate_questions_groq,
        "ollama": generate_questions_ollama,
        "openrouter": generate_questions_openrouter,
    }
    generate_fn = generate_fns[provider]

    # Extract text from all files
    all_text = ""
    source_files = []
    for file_path in file_paths:
        print(f"Extracting text from: {file_path}")
        text = extract_text(file_path)
        all_text += f"\n\n--- {Path(file_path).name} ---\n\n{text}"
        source_files.append(Path(file_path).name)

    # Split into chunks
    chunks = split_into_chunks(all_text)
    print(f"Document split into {len(chunks)} chunks")

    # Compute questions per chunk
    questions_per_chunk = max(1, num_questions // len(chunks))
    extra_questions = num_questions % len(chunks)

    # Generate questions
    all_questions = []
    for i, chunk in enumerate(chunks):
        target = questions_per_chunk + (1 if i < extra_questions else 0)
        print(f"Generating {target} questions from chunk {i + 1}/{len(chunks)}...")

        try:
            questions = generate_fn(chunk, target, model)
            all_questions.extend(questions)
            print(f"  -> {len(questions)} questions generated")
        except Exception as e:
            print(f"  -> Error: {e}")
            continue

    # Remove duplicates preserving order
    seen = set()
    unique_questions = []
    for q in all_questions:
        q_normalized = q.lower().strip()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_questions.append(q)

    # Cap at the requested number
    unique_questions = unique_questions[:num_questions]

    # Build structured dataset
    dataset = {
        "metadata": {
            "source_documents": source_files,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_questions": len(unique_questions),
            "provider": provider,
            "model": model,
        },
        "questions": [
            {
                "question_id": str(uuid.uuid4()),
                "question": q,
                "reference_answers": [],  # Filled in by collect_references.py
            }
            for q in unique_questions
        ],
    }

    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Generate agriculture-domain questions from documents"
    )
    parser.add_argument(
        "input",
        help="PDF/TXT file or directory with documents",
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=300,
        help="Total number of questions to generate (default: 300)",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "ollama", "openrouter"],
        default=DEFAULT_PROVIDER,
        help=f"LLM provider (default: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--model",
        help="LLM model (default depends on provider)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_QUESTIONS_PATH),
        help=f"Path to the output file (default: {DEFAULT_QUESTIONS_PATH})",
    )

    args = parser.parse_args()

    # Validate provider
    if args.provider == "groq" and not os.environ.get("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not set. Use --provider ollama or set the variable.")
        return 1

    if args.provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set. Use --provider ollama or set the variable.")
        return 1

    # Collect files
    try:
        files = collect_files(args.input)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    if not files:
        print(f"No PDF/TXT files found in: {args.input}")
        return 1

    print(f"Files found: {len(files)}")
    for f in files:
        print(f"  - {f}")

    # Generate questions
    dataset = generate_questions_from_files(
        files,
        num_questions=args.num_questions,
        provider=args.provider,
        model=args.model,
    )

    # Save dataset
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\nDataset saved to: {output_path}")
    print(f"Total questions: {dataset['metadata']['total_questions']}")

    return 0


if __name__ == "__main__":
    exit(main())
