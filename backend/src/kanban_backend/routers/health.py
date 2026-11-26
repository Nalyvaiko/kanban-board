from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from sqlalchemy import text

from ..db import SessionLocal
from ..errors import ApiError

router = APIRouter(tags=["Health"])
logger = logging.getLogger("kanban_backend.health")


@router.get("/health")
def health() -> dict[str, str]:
    """Unauthenticated liveness/readiness check: process is up and the
    database is reachable. Used by the CI/CD pipeline to confirm a deploy
    actually came up, not just that the instance is running.

    `version` is the deployed image tag (APP_VERSION, set by deploy-app.sh),
    so the pipeline can check that the build it just deployed is the one
    answering - not a previous container that's still up.
    """
    try:
        SessionLocal.execute(text("SELECT 1"))
    except Exception:
        # The details (host, user, driver message) go to the logs only:
        # this endpoint is public, so it mustn't describe the database to
        # whoever asks.
        logger.exception("health check: database unreachable")
        raise ApiError(503, "Database unreachable") from None
    return {
        "status": "ok",
        "version": os.environ.get("APP_VERSION", "unknown"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
    }
