"""Database engine and session configuration.

The connection target is controlled entirely by the `DATABASE_URL`
environment variable (any SQLAlchemy URL), so switching databases - e.g.
from local SQLite to Postgres in production - never requires a code change,
only a driver install and a new URL. Defaults to a local SQLite file so the
app still runs with zero setup.

`SessionLocal` is a `scoped_session`, scoped to a contextvar rather than the
current OS thread - deliberately, not the SQLAlchemy default. FastAPI runs
each sync route handler (and each sync dependency) via `anyio.to_thread`,
which can hop a single request across *several* worker threads; a
thread-scoped session would hand each of those hops an unrelated Session,
so a "successful" commit in one place could easily be committing an empty
session while the real writes sat uncommitted in another. A contextvar
follows the request's logical task across those thread hops instead (anyio
copies the context into each worker thread), so every hop within one
request shares the same Session, while concurrent requests - each their own
asyncio task - stay isolated from each other. See `new_session_scope` /
`end_session_scope`, used by the commit/rollback middleware in main.py.
"""

from __future__ import annotations

import os
from contextvars import ContextVar, Token
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kanban.db")
_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_sqlite_memory = _is_sqlite and ":memory:" in DATABASE_URL

_engine_kwargs: dict[str, object] = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if _is_sqlite_memory:
        # An in-memory SQLite DB is per-connection; pin the engine to a
        # single connection so every thread sees the same database.
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)

if _is_sqlite and not _is_sqlite_memory:
    # The stdlib sqlite3 driver runs its own implicit transaction handling
    # (issuing BEGIN on its own schedule) that conflicts with SQLAlchemy's,
    # which can leave a commit()'d session without an actual SQLite COMMIT
    # having happened - the write sits uncommitted until something else
    # flushes it, and a killed process can lose it entirely. This is
    # SQLAlchemy's documented fix: hand transaction boundaries entirely to
    # SQLAlchemy by disabling pysqlite's own.
    # https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
    #
    # Skipped for the in-memory test DB: it uses one shared StaticPool
    # connection across every thread, and this fix's manual BEGIN doesn't
    # tolerate two threads' transactions overlapping on one connection.
    # Durability across a process kill isn't a concern for :memory: anyway.
    @event.listens_for(engine, "connect")
    def _sqlite_disable_pysqlite_transactions(dbapi_connection, connection_record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _sqlite_begin(conn) -> None:
        conn.exec_driver_sql("BEGIN")

# Default is a single shared scope for anything that runs outside a request
# (module-level seeding at startup, tests' direct Store() instances) - safe
# since those only ever run single-threaded/sequentially.
_session_scope: ContextVar[str] = ContextVar("kanban_backend_session_scope", default="startup")


def _scopefunc() -> str:
    return _session_scope.get()


SessionLocal = scoped_session(
    sessionmaker(class_=Session, bind=engine, expire_on_commit=False), scopefunc=_scopefunc
)


def init_db() -> None:
    """Creates any tables that don't already exist. Safe to call repeatedly."""
    SQLModel.metadata.create_all(engine)


def new_session_scope() -> Token[str]:
    """Starts a fresh session scope - call once per request, before touching
    the store. Returns a token to pass to `end_session_scope` afterward."""
    return _session_scope.set(str(uuid4()))


def end_session_scope(token: Token[str]) -> None:
    """Tears down the session started by `new_session_scope`. Removes the
    scoped session first (while its scope is still active) so its DBAPI
    connection is actually released back to the pool."""
    SessionLocal.remove()
    _session_scope.reset(token)
