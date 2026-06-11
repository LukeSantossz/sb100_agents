"""User authentication and registration routes.

Implements JWT-based authentication with endpoints for:

- **POST /auth/register**: Create a new user (rate-limit: 3/hour per IP).
- **POST /auth/token**: Log in and issue a JWT (rate-limit: 5/15min per IP).

Security:
    - Passwords hashed with bcrypt via passlib (timing-safe verification).
    - JWTs expire in 7 days by default.
    - Username validated by regex ``^[a-zA-Z0-9_-]+$`` (max 50 chars).
    - Password must be at least 8 characters.
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

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])


def get_password_hash(password: str) -> str:
    """Hash the password with bcrypt (random salt embedded).

    Args:
        password: Plain-text password.

    Returns:
        Bcrypt hash in the ``$2b$...`` format.
    """
    hashed: str = pwd_context.hash(password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against the stored bcrypt hash (timing-safe).

    Args:
        plain_password: Plain-text password supplied by the user.
        hashed_password: Bcrypt hash stored in the database.

    Returns:
        True if the password matches, False in any other case (including an
        invalid/corrupted hash — degrades to an authentication failure).
    """
    try:
        return bool(pwd_context.verify(plain_password, hashed_password))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT with an expiration time.

    Args:
        data: Token payload (e.g. ``{"sub": "username"}``).
        expires_delta: Time until expiration. Default: 15 minutes.

    Returns:
        Encoded JWT as a string.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not _USERNAME_PATTERN.match(value):
            raise ValueError("username must contain only letters, digits, hyphen and underscore")
        return value


class Token(BaseModel):
    """Response schema containing the JWT."""

    access_token: str
    token_type: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Register a new user in the system.

    Args:
        request: HTTP request (required by the slowapi rate-limit).
        user_data: User data (validated username and password).
        db: Injected database session.

    Returns:
        Success message with the created username.

    Raises:
        HTTPException(400): If the username is already taken.
        HTTPException(429): If the rate-limit (3/hour per IP) is hit.
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
    """Authenticate the user and return a JWT.

    Endpoint compatible with the OAuth2 password flow for use with Swagger UI.

    Args:
        request: HTTP request (required by the slowapi rate-limit).
        form_data: OAuth2 form with username and password.
        db: Injected database session.

    Returns:
        JWT and token type (``bearer``).

    Raises:
        HTTPException(401): If the credentials are invalid.
        HTTPException(429): If the rate-limit (5/15min per IP) is hit.
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
