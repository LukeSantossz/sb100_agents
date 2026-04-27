from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# SQLite database file relative to the project root
_db_path = Path(__file__).resolve().parents[1] / "smartb100_v2.db"
if _db_path.exists() and _db_path.is_dir():
    msg = (
        f"SQLite path {_db_path} is a directory, not a database file. "
        "Delete that folder. On Windows, a Docker bind mount to a missing path can create "
        "a directory with this name: create an empty file first, or remove the bad folder."
    )
    raise RuntimeError(msg)
_resolved_db = _db_path.resolve()
DB_PATH = str(_resolved_db)
# Barras à frente no URL evitam ambiguidade do SQLite no Windows (recomendado pelo SQLAlchemy).
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_resolved_db.as_posix()}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
