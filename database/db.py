"""SQLAlchemy engine and session configuration for SmartB100.

Hardening applied to this layer:

- ``connect_args["timeout"]`` avoids ``OperationalError: database is locked``.
- ``PRAGMA foreign_keys=ON`` listener enables CASCADE in SQLite (off by default).
- ``get_db()`` rolls back explicitly on exception before closing the session.
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
# Forward slashes in the URL avoid SQLite ambiguity on Windows (recommended by SQLAlchemy).
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_resolved_db.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable PRAGMA foreign_keys on SQLite connections to ensure CASCADE."""
    # Only SQLite needs the PRAGMA; other dialects do not expose ``execute`` this way.
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:  # noqa: BLE001
        # Non-SQLite or incompatible cursor — ignore silently.
        return


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Provide a DB session with rollback on exception and guaranteed cleanup.

    Typical use via FastAPI dependency injection::

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
