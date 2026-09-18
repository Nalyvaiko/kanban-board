"""FastAPI application entrypoint.

Run with: `uv run uvicorn kanban_backend.main:app --reload`
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .db import SessionLocal, init_db
from .routers import (
    activity,
    attachments,
    auth,
    boards,
    comments,
    dashboard,
    labels,
    members,
    projects,
    relations,
    tasks,
    users,
)
from .seed import seed_demo_data
from .store import store

ALL_ROUTERS = (
    auth.router,
    users.router,
    projects.router,
    members.router,
    boards.router,
    tasks.router,
    comments.router,
    attachments.router,
    labels.router,
    relations.router,
    activity.router,
    dashboard.router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Jira API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def db_session_middleware(request: Request, call_next):
        # Commits whatever this request's thread-local session accumulated,
        # rolls back on an unhandled error, and always tears the session
        # down afterward so a pooled thread starts the next request clean.
        try:
            response = await call_next(request)
            SessionLocal.commit()
            return response
        except Exception:
            SessionLocal.rollback()
            raise
        finally:
            SessionLocal.remove()

    for router in ALL_ROUTERS:
        app.include_router(router, prefix="/api")

    return app


app = create_app()

init_db()

# Seeded once, at import time, so the API has demo data as soon as the
# process starts - no separate setup step required. Tests reset the store
# between cases (see tests/conftest.py) rather than relying on this data.
# Only seeds an empty database, so restarting the server (or pointing it at
# an already-seeded DB) doesn't recreate the demo accounts/projects.
if not store.users.values():
    seed_demo_data(store)
    SessionLocal.commit()
SessionLocal.remove()
