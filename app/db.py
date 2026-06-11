"""SQLAlchemy engine and session."""

from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
SessionLocal: Optional[sessionmaker[Session]] = None


def init_db(database_url: str) -> None:
    global _engine, SessionLocal
    connect_args: dict = {}
    engine_kwargs: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        from aaf.config import get_settings

        s = get_settings()
        engine_kwargs = {
            "pool_size": s.db_pool_size,
            "max_overflow": s.db_max_overflow,
            "pool_recycle": s.db_pool_recycle_seconds,
        }
    _engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine():
    if _engine is None:
        raise RuntimeError("Database not initialized; call init_db() on startup")
    return _engine


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
