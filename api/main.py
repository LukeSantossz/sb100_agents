"""Ponto de entrada da aplicação FastAPI SmartB100.

Este módulo configura a aplicação FastAPI com:

- Middleware CORS para permitir acesso da interface Gradio.
- Routers de chat, autenticação e health check.
- Lifespan handler para inicialização do banco de dados.

Uso:
    uvicorn api.main:app --reload
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.dependencies import limiter
from api.routes import auth, chat, health
from database.db import Base, engine

# Logging baseline para a aplicação (idempotente; basicConfig é no-op se já configurado).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

ALLOWED_ORIGINS = [
    "http://localhost:7860",
    "http://127.0.0.1:7860",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
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

app.state.limiter = limiter
# slowapi: handler aceita RateLimitExceeded, mas Starlette tipa o segundo arg como Exception genérico.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

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
