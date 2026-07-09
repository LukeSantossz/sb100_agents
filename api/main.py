"""Entry point of the SmartB100 FastAPI application.

This module configures the FastAPI application with:

- CORS middleware to allow access from the Gradio interface.
- Chat, authentication and health check routers.
- Lifespan handler for database initialization.

Usage:
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
from api.routes import auth, chat, conversations, health
from database.db import Base, engine

# Baseline logging for the application (idempotent; basicConfig is a no-op if already set).
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
    """Manage the FastAPI application lifecycle.

    Runs setup (table creation) on startup and cleanup on shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control returns to the application after setup.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="SmartB100 API",
    description="API for the SmartB100 system",
    lifespan=lifespan,
)

app.state.limiter = limiter
# slowapi: handler takes RateLimitExceeded, but Starlette types the second arg as plain Exception.
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
app.include_router(conversations.router)
app.include_router(health.router)
