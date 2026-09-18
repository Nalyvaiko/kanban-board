"""Database engine and session configuration.

The connection target is controlled entirely by the `DATABASE_URL`
environment variable (any SQLAlchemy URL), so switching databases - e.g.
from local SQLite to Postgres in production - never requires a code change,
only a driver install and a new URL. Defaults to a local SQLite file so the
app still runs with zero setup.

`SessionLocal` is a `scoped_session`: it hands each thread its own `Session`
transparently, so code can use it like a single global object (matching the
old in-memory store's ergonomics) while staying safe under FastAPI's
threaded execution of sync route handlers.
"""

from __future__ import annotations

import os

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kanban.db")

_engine_kwargs: dict[str, object] = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in DATABASE_URL:
        # An in-memory SQLite DB is per-connection; pin the engine to a
        # single connection so every thread sees the same database.
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = scoped_session(sessionmaker(class_=Session, bind=engine, expire_on_commit=False))


def init_db() -> None:
    """Creates any tables that don't already exist. Safe to call repeatedly."""
    SQLModel.metadata.create_all(engine)
