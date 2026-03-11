

import os
import re
import uuid
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, PayloadSchemaType
)
import ollama


# ─────────────────────────────────────────────
# Configurações globais
# ─────────────────────────────────────────────

OLLAMA_MODEL       = "llama3.1:8b"   # modelo de embeddings via Ollama
EMBED_DIM          = 4096            # dimensão dos embeddings do Llama 3.1:8b
QDRANT_URL         = "http://localhost:6333"
COLLECTION_NAME    = "archives"

# Thresholds do chunking semântico
SIMILARITY_THRESHOLD = 0.75   # abaixo disso → novo chunk
MIN_CHUNK_SENTENCES  = 3      # mínimo de frases por chunk
MAX_CHUNK_SENTENCES  = 20     # máximo de frases por chunk


# ─────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────

@dataclass
class Sentence:
    text: str
    embedding: np.ndarray = field(default=None, repr=False)

@dataclass
class Chunk:
    text: str
    sentences: List[str]
    embedding: np.ndarray = field(default=None, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────
# Extração de texto do PDF
# ─────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto de todas as páginas do PDF."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)
    doc.close()
    return "\n".join(pages_text)


def split_into_sentences(text: str) -> List[str]:
    """
    Divide o texto em frases usando regex simples (sem NLTK).
    Funciona bem para textos em português e inglês.
    """
    # Normaliza espaços e quebras de linha
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # Divide por pontuação de fim de frase
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÀÂÊÔÃÕ])', text)

    # Remove frases muito curtas (ruído do PDF)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    return sentences


# ─────────────────────────────────────────────
# Embeddings via Ollama (Llama)
# ─────────────────────────────────────────────

def get_embedding(text: str) -> np.ndarray:
    """Gera embedding de um texto usando o modelo Llama via Ollama."""
    response = ollama.embeddings(model=OLLAMA_MODEL, prompt=text)
    return np.array(response["embedding"], dtype=np.float32)


def get_embeddings_batch(texts: List[str], batch_size: int = 16) -> List[np.ndarray]:
    """Gera embeddings em lotes para eficiência."""
    embeddings = []
    for i in tqdm(range(0, len(texts), batch_size), desc="  Gerando embeddings", leave=False):
        batch = texts[i:i + batch_size]
        for text in batch:
            emb = get_embedding(text)
            embeddings.append(emb)
    return embeddings


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Similaridade de cosseno entre dois vetores."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ─────────────────────────────────────────────
# Chunking Semântico
# ─────────────────────────────────────────────

def semantic_chunking(sentences: List[Sentence]) -> List[List[Sentence]]:
    """
    Agrupa frases em chunks com base na similaridade semântica.

    Algoritmo:
      1. Começa um chunk com a primeira frase.
      2. Para cada frase seguinte, compara com o embedding médio do chunk atual.
      3. Se similaridade < threshold (ou chunk ficou grande demais) → novo chunk.
      4. Respeita tamanhos mínimo e máximo.
    """
    if not sentences:
        return []

    chunks: List[List[Sentence]] = []
    current_chunk: List[Sentence] = [sentences[0]]

    for i in range(1, len(sentences)):
        sentence = sentences[i]

        # Embedding médio do chunk atual
        chunk_embeddings = np.stack([s.embedding for s in current_chunk])
        chunk_mean = chunk_embeddings.mean(axis=0)

        similarity = cosine_similarity(chunk_mean, sentence.embedding)
        too_large  = len(current_chunk) >= MAX_CHUNK_SENTENCES
        too_small  = len(current_chunk) < MIN_CHUNK_SENTENCES

        if (similarity < SIMILARITY_THRESHOLD and not too_small) or too_large:
            # Fecha chunk atual e inicia novo
            chunks.append(current_chunk)
            current_chunk = [sentence]
        else:
            current_chunk.append(sentence)

    # Adiciona o último chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def build_chunks(sentence_groups: List[List[Sentence]], metadata: Dict) -> List[Chunk]:
    """Converte grupos de frases em objetos Chunk com embedding representativo."""
    chunks = []
    for group in sentence_groups:
        text = " ".join(s.text for s in group)

        # Embedding do chunk = média dos embeddings das frases
        embeddings = np.stack([s.embedding for s in group])
        chunk_embedding = embeddings.mean(axis=0)

        chunk = Chunk(
            text=text,
            sentences=[s.text for s in group],
            embedding=chunk_embedding,
            metadata={**metadata, "num_sentences": len(group)}
        )
        chunks.append(chunk)
    return chunks


# ─────────────────────────────────────────────
# Qdrant
# ─────────────────────────────────────────────

def init_qdrant(client: QdrantClient, embed_dim: int):
    """Cria a collection no Qdrant se não existir."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=embed_dim, distance=Distance.COSINE),
        )
        print(f"  ✓ Collection '{COLLECTION_NAME}' criada (dim={embed_dim})")
    else:
        print(f"  ✓ Collection '{COLLECTION_NAME}' já existe, reutilizando.")


def upsert_chunks(client: QdrantClient, chunks: List[Chunk]):
    """Insere chunks no Qdrant."""
    points = []
    for chunk in chunks:
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk.embedding.tolist(),
            payload={
                "text": chunk.text,
                "num_sentences": chunk.metadata.get("num_sentences", 0),
                "source_file": chunk.metadata.get("source_file", ""),
                "source_path": chunk.metadata.get("source_path", ""),
            }
        )
        points.append(point)

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


# ─────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────

def process_pdf(pdf_path: str, client: QdrantClient) -> int:
    """Processa um único PDF e indexa no Qdrant. Retorna número de chunks."""
    filename = Path(pdf_path).name
    print(f"\n📄 Processando: {filename}")

    # 1. Extração de texto
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        print("  ⚠️  Nenhum texto extraído (PDF pode ser imagem). Pulando.")
        return 0

    # 2. Divisão em frases
    raw_sentences = split_into_sentences(raw_text)
    print(f"  → {len(raw_sentences)} frases extraídas")

    if len(raw_sentences) == 0:
        return 0

    # 3. Embeddings das frases
    print(f"  → Gerando embeddings via {OLLAMA_MODEL}...")
    texts = [s for s in raw_sentences]
    embeddings = get_embeddings_batch(texts)

    sentences = [
        Sentence(text=t, embedding=e)
        for t, e in zip(raw_sentences, embeddings)
    ]

    # 4. Chunking semântico
    sentence_groups = semantic_chunking(sentences)
    print(f"  → {len(sentence_groups)} chunks semânticos gerados")

    # 5. Construção dos chunks com metadados
    metadata = {
        "source_file": filename,
        "source_path": str(Path(pdf_path).resolve()),
    }
    chunks = build_chunks(sentence_groups, metadata)

    # 6. Indexação no Qdrant
    count = upsert_chunks(client, chunks)
    print(f"  ✓ {count} chunks indexados no Qdrant")
    return count


def process_folder(folder_path: str):
    """Processa todos os PDFs de uma pasta."""
    pdf_files = list(Path(folder_path).glob("**/*.pdf"))
    if not pdf_files:
        print(f"Nenhum PDF encontrado em: {folder_path}")
        return

    print(f"🔍 {len(pdf_files)} PDFs encontrados em '{folder_path}'")

    # Inicializa Qdrant
    client = QdrantClient(url=QDRANT_URL)
    init_qdrant(client, EMBED_DIM)

    total_chunks = 0
    for pdf_path in tqdm(pdf_files, desc="Processando PDFs"):
        total_chunks += process_pdf(str(pdf_path), client)

    print(f"\n✅ Pipeline concluído!")
    print(f"   PDFs processados : {len(pdf_files)}")
    print(f"   Chunks indexados : {total_chunks}")
    print(f"   Collection       : {COLLECTION_NAME}")
    print(f"   Qdrant URL       : {QDRANT_URL}")


# ─────────────────────────────────────────────
# Busca (exemplo de uso)
# ─────────────────────────────────────────────

def search(query: str, top_k: int = 5):
    """Busca semântica na collection."""
    client = QdrantClient(url=QDRANT_URL)
    query_embedding = get_embedding(query)

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding.tolist(),
        limit=top_k,
        with_payload=True,
    )

    print(f"\n🔎 Query: \"{query}\"\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] Score: {r.score:.4f} | Arquivo: {r.payload.get('source_file')}")
        print(f"    {r.payload['text'][:300]}...")
        print()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic Chunking Pipeline com Llama + Qdrant")
    subparsers = parser.add_subparsers(dest="command")

    # Comando: indexar
    index_parser = subparsers.add_parser("index", help="Indexa PDFs de uma pasta")
    index_parser.add_argument("folder", help="Caminho da pasta com os PDFs")
    index_parser.add_argument("--model", default=OLLAMA_MODEL, help="Modelo Ollama para embeddings")
    index_parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD,
                              help="Threshold de similaridade para novo chunk (padrão: 0.75)")
    index_parser.add_argument("--qdrant-url", default=QDRANT_URL, help="URL do Qdrant")
    index_parser.add_argument("--collection", default=COLLECTION_NAME, help="Nome da collection")

    # Comando: buscar
    search_parser = subparsers.add_parser("search", help="Busca semântica na collection")
    search_parser.add_argument("query", help="Texto da busca")
    search_parser.add_argument("--top-k", type=int, default=5, help="Número de resultados")
    search_parser.add_argument("--qdrant-url", default=QDRANT_URL)
    search_parser.add_argument("--collection", default=COLLECTION_NAME)

    args = parser.parse_args()

    if args.command == "index":
        OLLAMA_MODEL         = args.model
        SIMILARITY_THRESHOLD = args.threshold
        QDRANT_URL           = args.qdrant_url
        COLLECTION_NAME      = args.collection
        process_folder(args.folder)

    elif args.command == "search":
        QDRANT_URL      = args.qdrant_url
        COLLECTION_NAME = args.collection
        search(args.query, top_k=args.top_k)

    else:
        parser.print_help()
