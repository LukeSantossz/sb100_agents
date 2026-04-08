from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import ollama
from qdrant_client import QdrantClient
from typing import List

from sb100_agents.database.db import get_db, engine
from sb100_agents.database import models
from sb100_agents.auth import security

# Criar as tabelas no banco de dados se não existirem
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="RAG Chat API", description="API com autenticação JWT e gerenciamento de conversas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHAT_MODEL = "llama3.1:8b"
EMBED_MODEL = "nomic-embed-text"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "archives_v2"
TOP_K = 3

qdrant = QdrantClient(url=QDRANT_URL)

# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatRequest(BaseModel):
    question: str

class ConversationCreate(BaseModel):
    title: str = "Nova Conversa"

# ─── RAG Helpers ──────────────────────────────────────────────────────────────
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

def buscar_contexto_detalhado(question: str) -> dict:
    embedding = gerar_embedding(question)
    resultados = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=TOP_K,
        with_payload=True,
    ).points
    
    chunks = [r.payload.get("text", "") for r in resultados]
    context_str = "\n\n".join(chunks)
    
    return {
        "context_str": context_str,
        "trechos": chunks,
        "valores": [r.payload for r in resultados]
    }

def is_agri_question(question: str) -> bool:
    # Validador para não fazer RAG atoa em "Olá", "Tudo bem?"
    prompt = f"Analise a seguinte mensagem do usuário: '{question}'. Ela parece uma saudação ou conversa casual genérica (olá, bom dia, quem é você) ou ela contém uma dúvida que exigiria buscar informações em manuais técnicos? Responda APENAS com a palavra SAUDACAO ou DUVIDA."
    try:
        response = ollama.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt}])
        return "DUVIDA" in response["message"]["content"].upper()
    except:
        return True # Se falhar, assume true por segurança

def perguntar_ollama(messages_history: list, question: str, context: str) -> str:
    if context:
        prompt = f"""Você é um assistente especializado em AGRONEGÓCIO. Use o contexto abaixo extraído de manuais e arquivos agrícolas para responder.
Se a resposta não estiver no contexto, diga que não sabe.

Contexto:
{context}

Pergunta:
{question}"""
    else:
        prompt = f"""Você é um assistente especializado em AGRONEGÓCIO. O usuário está conversando com você. Responda de forma prestativa, com foco no agronegócio se possível.

Pergunta:
{question}"""
    
    # Adicionar o prompt RAG no lugar da pergunta pura do usuário no histórico que será enviado
    mensagens_para_llm = messages_history.copy()
    mensagens_para_llm.append({"role": "user", "content": prompt})

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=mensagens_para_llm,
    )
    return response["message"]["content"]

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.post("/register", response_model=dict)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Usuário criado com sucesso", "username": new_user.username}

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ─── Conversation Routes ──────────────────────────────────────────────────────

@app.post("/conversations")
def create_conversation(conv: ConversationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    new_conv = models.Conversation(user_id=current_user.id, title=conv.title)
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {"id": new_conv.id, "title": new_conv.title}

@app.get("/conversations")
def list_conversations(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    convs = db.query(models.Conversation).filter(models.Conversation.user_id == current_user.id).order_by(models.Conversation.created_at.desc()).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in convs]

@app.get("/conversations/{conv_id}/messages")
def list_messages(conv_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id, models.Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(models.Message).filter(models.Message.conversation_id == conv_id).order_by(models.Message.created_at.asc()).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

@app.post("/conversations/{conv_id}/chat")
def chat_in_conversation(conv_id: int, req: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id, models.Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Save User message
    user_msg = models.Message(conversation_id=conv_id, role="user", content=req.question)
    db.add(user_msg)
    db.commit()

    # Get history to send to LLM
    history = db.query(models.Message).filter(models.Message.conversation_id == conv_id).order_by(models.Message.created_at.asc()).all()
    
    # Se for a primeira mensagem (só tem a mensagem do usuário que acabamos de adicionar)
    if len(history) == 1:
        # Gerar título via LLM
        prompt_titulo = f"Crie um título muito curto (máximo 4 palavras) que resuma esta mensagem: '{req.question}'. Retorne APENAS o título e nada mais."
        try:
            res_titulo = ollama.chat(model=CHAT_MODEL, messages=[{"role": "user", "content": prompt_titulo}])
            novo_titulo = res_titulo["message"]["content"].replace('"', '').strip()
            conv.title = novo_titulo
            db.commit()
        except:
            pass

    msg_history = [{"role": msg.role, "content": msg.content} for msg in history[:-1]] # exclude the one we just added to send as current
    
    try:
        if is_agri_question(req.question):
            detalhes = buscar_contexto_detalhado(req.question)
            context_str = detalhes["context_str"]
            trechos = detalhes["trechos"]
        else:
            context_str = ""
            trechos = []
            
        answer = perguntar_ollama(msg_history, req.question, context_str)
        
        # Save Assistant message
        assistant_msg = models.Message(conversation_id=conv_id, role="assistant", content=answer)
        db.add(assistant_msg)
        db.commit()
        
        return {"question": req.question, "answer": answer, "context": trechos}
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=traceback.format_exc())

@app.post("/question")
def ask_question(req: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    try:
        if is_agri_question(req.question):
            detalhes = buscar_contexto_detalhado(req.question)
            context_str = detalhes["context_str"]
            trechos = detalhes["trechos"]
            valores = detalhes["valores"]
        else:
            context_str = ""
            trechos = []
            valores = []

        answer = perguntar_ollama([], req.question, context_str)
        
        return {
            "answer": answer,
            "context": trechos,
            "valores_vetor": valores
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "model": CHAT_MODEL}