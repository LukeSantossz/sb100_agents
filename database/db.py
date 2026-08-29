"""SQLAlchemy engine and session configuration for SmartB100.

Hardening applied to this layer:

- ``connect_args["timeout"]`` avoids ``OperationalError: database is locked``.
- ``PRAGMA foreign_keys=ON`` listener enables CASCADE in SQLite (off by default).
- ``get_db()`` rolls back explicitly on exception before closing the session.
- The file location is overridable, so the container can put it inside a mounted
  directory instead of bind-mounting the file itself. See :func:`resolve_db_path`.
"""

import os
from collections.abc import Generator, Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

#: Environment variable naming the SQLite file. Deliberately not a ``Settings``
#: field and deliberately absent from ``.env.example``: it is a container fact,
#: set in the compose ``environment:`` block beside ``QDRANT_URL``, not a knob an
#: operator tunes. Reading it here also keeps this module free of ``core.config``,
#: so the database layer does not depend on JWT validation passing.
DB_PATH_ENV_VAR = "SMARTB100_DB_PATH"

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "smartb100_v2.db"


def resolve_db_path(environ: Mapping[str, str] | None = None) -> Path:
    """Return the SQLite file location, honouring :data:`DB_PATH_ENV_VAR`.

    The default is the repository root, unchanged, so an existing local database
    keeps working and nobody's file moves. The override exists for the container,
    which points it inside the mounted ``/app/data`` directory: bind-mounting the
    database file itself made Docker create a directory with that name on any
    clean clone, because the file is gitignored and therefore always absent.

    A blank or whitespace-only value falls back to the default rather than
    resolving to the current directory, which is what an unset-but-present
    variable in a ``.env`` would otherwise do.

    Args:
        environ: Mapping to read from; defaults to the process environment.

    Returns:
        Path to the SQLite file, not necessarily existing yet.
    """
    source = os.environ if environ is None else environ
    override = source.get(DB_PATH_ENV_VAR, "").strip()
    return Path(override) if override else DEFAULT_DB_PATH


_db_path = resolve_db_path()
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
