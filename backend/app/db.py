"""SQLAlchemy engine + session management."""
from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite"):
        rest = url.split("sqlite:///", 1)[1] if "sqlite:///" in url else ""
        if rest and rest != ":memory:":
            Path(rest).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

_engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_engine():
    return _engine


def get_session() -> Generator[Session, None, None]:
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sync_session() -> Session:
    return _SessionLocal()


def init_db() -> None:
    from app.models.base import Base  # noqa: F401

    Base.metadata.create_all(bind=_engine)

def override_session_factory(new_factory):
    global _SessionLocal
    _SessionLocal = new_factory
