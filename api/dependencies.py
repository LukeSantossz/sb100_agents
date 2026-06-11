"""Shared dependencies for the FastAPI routes.

Centralizes the JWT authentication used by protected routes. The OAuth2 scheme
is exposed via :data:`oauth2_scheme` and the full validation (token + active
user in the database) is performed by :func:`verify_token`.
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
    """Validate the bearer JWT and return the matching user.

    Args:
        token: JWT extracted from the ``Authorization: Bearer`` header.
        db: SQLAlchemy session injected by FastAPI.

    Returns:
        :class:`User` instance matching the token's ``sub`` claim.

    Raises:
        HTTPException: 401 if the token is invalid, expired, missing ``sub``,
            or if the referenced user no longer exists in the database.
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
