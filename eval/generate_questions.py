"""
Gerador de perguntas a partir de documentos PDF/TXT.

Usa LLM (Groq API ou Ollama local) para extrair e formular perguntas
de dominio agricola a partir do conteudo dos documentos.

Uso:
    python eval/generate_questions.py ./archives/boletim_sb100.pdf --num-questions 300
    python eval/generate_questions.py ./archives/ --num-questions 300 --provider ollama
"""

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

# Providers disponiveis: groq, ollama
DEFAULT_PROVIDER = "groq"
DEFAULT_GROQ_MODEL = "llama-3.1-70b-versatile"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

# Prompt para geracao de perguntas
QUESTION_GENERATION_PROMPT = """Voce e um especialista em agronomia e agricultura brasileira.
Com base no seguinte trecho de documento tecnico, gere {num_questions} perguntas relevantes e diversificadas.

As perguntas devem:
- Ser especificas e tecnicas, cobrindo diferentes aspectos do conteudo
- Variar em complexidade (algumas para iniciantes, outras para especialistas)
- Cobrir diferentes topicos mencionados no texto
- Ser claras e objetivas, formuladas em portugues

Retorne APENAS um JSON array com as perguntas, sem explicacoes adicionais.
Formato: ["pergunta 1", "pergunta 2", ...]

Trecho do documento:
---
{text_chunk}
---

JSON array com {num_questions} perguntas:"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto de todas as paginas do PDF."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)
    doc.close()
    return "\n".join(pages_text)


def extract_text_from_txt(txt_path: str) -> str:
    """Le conteudo de arquivo TXT."""
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_text(file_path: str) -> str:
    """Extrai texto de arquivo PDF ou TXT."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    elif path.suffix.lower() == ".txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Formato nao suportado: {path.suffix}")


def split_into_chunks(text: str, chunk_size: int = 4000, overlap: int = 500) -> list[str]:
    """Divide texto em chunks para processar com LLM."""
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
    """Gera perguntas usando Groq API."""
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
    """Gera perguntas usando Ollama local."""
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


def parse_questions_json(content: str) -> list[str]:
    """Extrai lista de perguntas do JSON retornado pelo LLM."""
    # Tenta extrair JSON array do conteudo
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        try:
            questions = json.loads(json_match.group())
            if isinstance(questions, list):
                return [q for q in questions if isinstance(q, str) and q.strip()]
        except json.JSONDecodeError:
            pass

    # Fallback: extrai linhas que parecem perguntas
    lines = content.split('\n')
    questions = []
    for line in lines:
        line = line.strip()
        # Remove prefixos numerados
        line = re.sub(r'^[\d]+[.\-\)]\s*', '', line)
        line = re.sub(r'^["\']\s*', '', line)
        line = re.sub(r'\s*["\']$', '', line)
        if line and '?' in line:
            questions.append(line)

    return questions


def collect_files(path: str) -> list[str]:
    """Coleta arquivos PDF/TXT de um caminho (arquivo ou diretorio)."""
    p = Path(path)
    if p.is_file():
        return [str(p)]
    elif p.is_dir():
        files = list(p.glob("**/*.pdf")) + list(p.glob("**/*.txt"))
        return [str(f) for f in files]
    else:
        raise ValueError(f"Caminho nao encontrado: {path}")


def generate_questions_from_files(
    file_paths: list[str],
    num_questions: int = 300,
    provider: str = DEFAULT_PROVIDER,
    model: Optional[str] = None,
) -> dict:
    """
    Gera perguntas a partir de uma lista de arquivos.

    Returns:
        Dataset estruturado com metadata e questions
    """
    if model is None:
        model = DEFAULT_GROQ_MODEL if provider == "groq" else DEFAULT_OLLAMA_MODEL

    generate_fn = generate_questions_groq if provider == "groq" else generate_questions_ollama

    # Extrai texto de todos os arquivos
    all_text = ""
    source_files = []
    for file_path in file_paths:
        print(f"Extraindo texto de: {file_path}")
        text = extract_text(file_path)
        all_text += f"\n\n--- {Path(file_path).name} ---\n\n{text}"
        source_files.append(Path(file_path).name)

    # Divide em chunks
    chunks = split_into_chunks(all_text)
    print(f"Documento dividido em {len(chunks)} chunks")

    # Calcula perguntas por chunk
    questions_per_chunk = max(1, num_questions // len(chunks))
    extra_questions = num_questions % len(chunks)

    # Gera perguntas
    all_questions = []
    for i, chunk in enumerate(chunks):
        target = questions_per_chunk + (1 if i < extra_questions else 0)
        print(f"Gerando {target} perguntas do chunk {i+1}/{len(chunks)}...")

        try:
            questions = generate_fn(chunk, target, model)
            all_questions.extend(questions)
            print(f"  -> {len(questions)} perguntas geradas")
        except Exception as e:
            print(f"  -> Erro: {e}")
            continue

    # Remove duplicatas mantendo ordem
    seen = set()
    unique_questions = []
    for q in all_questions:
        q_normalized = q.lower().strip()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_questions.append(q)

    # Limita ao numero solicitado
    unique_questions = unique_questions[:num_questions]

    # Monta dataset estruturado
    dataset = {
        "metadata": {
            "source_documents": source_files,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_questions": len(unique_questions),
            "provider": provider,
            "model": model,
        },
        "questions": [
            {
                "question_id": str(uuid.uuid4()),
                "question": q,
                "reference_answers": [],  # Sera preenchido por collect_references.py
            }
            for q in unique_questions
        ],
    }

    return dataset


def main():
    parser = argparse.ArgumentParser(
        description="Gera perguntas de dominio agricola a partir de documentos"
    )
    parser.add_argument(
        "input",
        help="Arquivo PDF/TXT ou diretorio com documentos",
    )
    parser.add_argument(
        "--num-questions",
        type=int,
        default=300,
        help="Numero total de perguntas a gerar (padrao: 300)",
    )
    parser.add_argument(
        "--provider",
        choices=["groq", "ollama"],
        default=DEFAULT_PROVIDER,
        help=f"Provider LLM (padrao: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--model",
        help="Modelo LLM (padrao depende do provider)",
    )
    parser.add_argument(
        "--output",
        default="eval/dataset/questions.json",
        help="Caminho do arquivo de saida (padrao: eval/dataset/questions.json)",
    )

    args = parser.parse_args()

    # Valida provider
    if args.provider == "groq" and not os.environ.get("GROQ_API_KEY"):
        print("Erro: GROQ_API_KEY nao definida. Use --provider ollama ou defina a variavel.")
        return 1

    # Coleta arquivos
    try:
        files = collect_files(args.input)
    except ValueError as e:
        print(f"Erro: {e}")
        return 1

    if not files:
        print(f"Nenhum arquivo PDF/TXT encontrado em: {args.input}")
        return 1

    print(f"Arquivos encontrados: {len(files)}")
    for f in files:
        print(f"  - {f}")

    # Gera perguntas
    dataset = generate_questions_from_files(
        files,
        num_questions=args.num_questions,
        provider=args.provider,
        model=args.model,
    )

    # Salva dataset
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\nDataset salvo em: {output_path}")
    print(f"Total de perguntas: {dataset['metadata']['total_questions']}")

    return 0


if __name__ == "__main__":
    exit(main())
