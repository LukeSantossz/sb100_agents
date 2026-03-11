from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import ollama
from qdrant_client import QdrantClient

app = FastAPI(title="RAG Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHAT_MODEL  = "llama3.1:8b"
EMBED_MODEL = "nomic-embed-text"

QDRANT_URL  = "http://localhost:6333"
COLLECTION  = "archives_v2"
TOP_K       = 3

qdrant = QdrantClient(url=QDRANT_URL)


def gerar_embedding(texto: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=texto)
    return response["embedding"]


def buscar_contexto(question: str) -> str:
    embedding = gerar_embedding(question)

    resultados = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=TOP_K,
        with_payload=True,
    ).points

    chunks = [r.payload.get("text", "") for r in resultados]
    return "\n\n".join(chunks)


def perguntar_ollama(question: str, context: str) -> str:
    prompt = f"""Use o contexto abaixo para responder a pergunta.
Se a resposta não estiver no contexto, diga que não sabe.

Contexto:
{context}

Pergunta:
{question}"""

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]


# ─── Rotas ────────────────────────────────────────────────────────────────────

@app.get("/chat")
def chat(question: str):
    try:
        context = buscar_contexto(question)
        answer  = perguntar_ollama(question, context)
        return {"question": question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "model": CHAT_MODEL}