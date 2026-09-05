"""Database engine and session factory.

SQLite, per CLAUDE.md's technical constraints -- a single-file
database is all a local-first, single-user tool needs. The file itself
is gitignored (*.db), regenerated from these models, not source.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DB_PATH = Path(__file__).parent.parent.parent / "tracklab.db"
engine = create_engine(f"sqlite:///{DB_PATH}")

# The session factory. Usage: `with SessionLocal() as session: ...` --
# Session itself is a context manager, so no extra wrapper is needed.
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Create all tables that don't already exist. Safe to call every
    startup -- a no-op against tables that are already there."""
    Base.metadata.create_all(engine)
