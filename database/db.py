"""Configuração de engine e sessão SQLAlchemy para o SmartB100.

TASK-T63 endurece a camada:

- ``connect_args["timeout"]`` evita ``OperationalError: database is locked``.
- Listener ``PRAGMA foreign_keys=ON`` ativa CASCADE em SQLite (off por default).
- ``get_db()`` faz rollback explícito em exceção antes de fechar a sessão.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
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

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """Ativa PRAGMA foreign_keys em conexões SQLite para garantir CASCADE."""
    # Apenas SQLite precisa do PRAGMA; outros dialetos não expõem ``execute`` nesse formato.
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:  # noqa: BLE001
        # Não-SQLite ou cursor incompatível — ignora silenciosamente.
        return


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Provê uma sessão de DB com rollback em exceção e cleanup garantido.

    Uso típico via dependency injection do FastAPI::

        @router.get("/")
        def handler(db: Session = Depends(get_db)) -> ...:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
