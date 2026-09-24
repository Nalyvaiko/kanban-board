from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from ..db import SessionLocal
from ..errors import ApiError

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Unauthenticated liveness/readiness check: process is up and the
    database is reachable. Used by the CI/CD pipeline to confirm a deploy
    actually came up, not just that the instance is running."""
    try:
        SessionLocal.execute(text("SELECT 1"))
    except Exception as error:
        raise ApiError(503, f"Database unreachable: {error}") from error
    return {"status": "ok"}
