"""Rotas de autenticação e registro de usuários.

Implementa autenticação baseada em JWT com endpoints para:

- **POST /auth/register**: Criação de novo usuário (rate-limit: 3/hora por IP).
- **POST /auth/token**: Login e geração de token JWT (rate-limit: 5/15min por IP).

Segurança:
    - Senhas hasheadas com bcrypt via passlib (verificação timing-safe).
    - Tokens JWT expiram em 7 dias por padrão.
    - Username validado por regex ``^[a-zA-Z0-9_-]+$`` (máx. 50 chars).
    - Password mínimo de 8 caracteres.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.dependencies import ALGORITHM, limiter
from core.config import settings
from database.db import get_db
from database.models import User

logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])


def get_password_hash(password: str) -> str:
    """Gera hash bcrypt da senha (com salt aleatório embutido).

    Args:
        password: Senha em texto plano.

    Returns:
        Hash bcrypt no formato ``$2b$...``.
    """
    hashed: str = pwd_context.hash(password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha de forma timing-safe contra o hash bcrypt armazenado.

    Args:
        plain_password: Senha em texto plano fornecida pelo usuário.
        hashed_password: Hash bcrypt armazenado no banco.

    Returns:
        True se a senha corresponder, False em qualquer outro caso (incluindo
        hash inválido/corrompido — degrada para falha de autenticação).
    """
    try:
        return bool(pwd_context.verify(plain_password, hashed_password))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Cria token JWT assinado com tempo de expiração.

    Args:
        data: Payload do token (ex: ``{"sub": "username"}``).
        expires_delta: Tempo até expiração. Default: 15 minutos.

    Returns:
        Token JWT codificado como string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


class UserCreate(BaseModel):
    """Schema para criação de novo usuário."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not _USERNAME_PATTERN.match(value):
            raise ValueError("username must contain only letters, digits, hyphen and underscore")
        return value


class Token(BaseModel):
    """Schema de resposta contendo token JWT."""

    access_token: str
    token_type: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Registra um novo usuário no sistema.

    Args:
        request: Requisição HTTP (necessário para slowapi rate-limit).
        user_data: Dados do usuário (username e password validados).
        db: Sessão do banco de dados injetada.

    Returns:
        Mensagem de sucesso com o username criado.

    Raises:
        HTTPException(400): Se o username já estiver em uso.
        HTTPException(429): Se o rate-limit (3/hora por IP) for atingido.
    """
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        logger.info(
            "auth.register.duplicate_username",
            extra={"username": user_data.username},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("auth.register.success", extra={"username": user_data.username})
    return {"message": "User created successfully", "username": str(user.username)}


@router.post("/token", response_model=Token)
@limiter.limit("5/15 minutes")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Autentica usuário e retorna token JWT.

    Endpoint compatível com OAuth2 password flow para uso com Swagger UI.

    Args:
        request: Requisição HTTP (necessário para slowapi rate-limit).
        form_data: Formulário OAuth2 com username e password.
        db: Sessão do banco de dados injetada.

    Returns:
        Token JWT e tipo (``bearer``).

    Raises:
        HTTPException(401): Se credenciais forem inválidas.
        HTTPException(429): Se o rate-limit (5/15min por IP) for atingido.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        logger.info("auth.login.failure", extra={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("auth.login.success", extra={"username": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
