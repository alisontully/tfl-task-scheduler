from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Allow override via env var; default to local SQLite file.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# SQLite needs a special connect arg; other engines don't.
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine: Engine = create_engine(DATABASE_URL, connect_args=_connect_args)


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """Declarative base for ORM models."""


# Typed session factory
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, autocommit=False
)


def init_db() -> None:
    """Create all tables defined on the declarative base."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """Return a DB session for FastAPI dependency injection; closes it afterwards."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
