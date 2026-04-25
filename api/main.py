"""Ponto de entrada da aplicação FastAPI SmartB100.

Este módulo configura a aplicação FastAPI com:

- Middleware CORS para permitir acesso do frontend.
- Routers de chat, autenticação e health check.
- Lifespan handler para inicialização do banco de dados.

Uso:
    uvicorn api.main:app --reload
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, chat, health
from database.db import Base, engine

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação FastAPI.

    Executa setup (criação de tabelas) no startup e cleanup no shutdown.

    Args:
        app: Instância da aplicação FastAPI.

    Yields:
        None: Controle retorna à aplicação após o setup.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SmartB100 API",
    description="API para o sistema SmartB100",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(health.router)
