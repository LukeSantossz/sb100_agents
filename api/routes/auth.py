"""Rotas de autenticação e registro de usuários.

Implementa autenticação baseada em JWT com endpoints para:

- **POST /auth/register**: Criação de novo usuário.
- **POST /auth/token**: Login e geração de token JWT.

Segurança:
    - Senhas são hasheadas com SHA-256 (considerar bcrypt em produção).
    - Tokens JWT expiram em 7 dias por padrão.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from database.db import get_db
from database.models import User

if not settings.jwt_secret_key:
    raise ValueError("JWT_SECRET_KEY must be configured in .env or environment variables")

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias

router = APIRouter(prefix="/auth", tags=["auth"])


def get_password_hash(password: str) -> str:
    """Gera hash SHA-256 da senha.

    Args:
        password: Senha em texto plano.

    Returns:
        Hash hexadecimal da senha.

    Note:
        Para produção, considerar usar bcrypt ou argon2.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash armazenado.

    Args:
        plain_password: Senha em texto plano fornecida pelo usuário.
        hashed_password: Hash armazenado no banco de dados.

    Returns:
        True se a senha corresponder, False caso contrário.
    """
    return get_password_hash(plain_password) == hashed_password


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Cria token JWT assinado com tempo de expiração.

    Args:
        data: Payload do token (ex: {"sub": "username"}).
        expires_delta: Tempo até expiração. Default: 15 minutos.

    Returns:
        Token JWT codificado como string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class UserCreate(BaseModel):
    """Schema para criação de novo usuário."""

    username: str
    password: str


class Token(BaseModel):
    """Schema de resposta contendo token JWT."""

    access_token: str
    token_type: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    """Registra um novo usuário no sistema.

    Args:
        user_data: Dados do usuário (username e password).
        db: Sessão do banco de dados injetada.

    Returns:
        Mensagem de sucesso com o username criado.

    Raises:
        HTTPException(400): Se o username já estiver em uso.
    """
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
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
    return {"message": "User created successfully", "username": str(user.username)}


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Autentica usuário e retorna token JWT.

    Endpoint compatível com OAuth2 password flow para uso com Swagger UI.

    Args:
        form_data: Formulário OAuth2 com username e password.
        db: Sessão do banco de dados injetada.

    Returns:
        Token JWT e tipo ("bearer").

    Raises:
        HTTPException(401): Se credenciais forem inválidas.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}
