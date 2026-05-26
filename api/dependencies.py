"""Dependências compartilhadas das rotas FastAPI.

Concentra autenticação JWT consumida pelas rotas protegidas. O esquema OAuth2 é
exposto via :data:`oauth2_scheme` e a validação completa (token + usuário ativo
no banco) é executada por :func:`verify_token`.
"""

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from core.config import settings
from database.db import get_db
from database.models import User

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
limiter = Limiter(key_func=get_remote_address)


def verify_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Valida JWT bearer e retorna o usuário correspondente.

    Args:
        token: Token JWT extraído do header ``Authorization: Bearer``.
        db: Sessão SQLAlchemy injetada pelo FastAPI.

    Returns:
        Instância de :class:`User` correspondente ao ``sub`` do token.

    Raises:
        HTTPException: 401 se o token for inválido, expirado, sem ``sub``,
            ou se o usuário referenciado não existir mais no banco.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except InvalidTokenError as e:
        logger.info("auth.verify_token.invalid_token", extra={"error": str(e)})
        raise credentials_exception from e

    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        logger.info("auth.verify_token.missing_sub")
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        logger.info("auth.verify_token.user_not_found", extra={"username": username})
        raise credentials_exception
    return user
