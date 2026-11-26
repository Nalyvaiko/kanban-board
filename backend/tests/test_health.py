from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from kanban_backend.db import SessionLocal


def test_health_reports_ok_with_no_auth(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_the_deployed_version(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("APP_VERSION", "20261125-120000-abc1234")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    assert client.get("/api/health").json() == {
        "status": "ok",
        "version": "20261125-120000-abc1234",
        "environment": "dev",
    }


def test_health_defaults_when_not_deployed(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    body = client.get("/api/health").json()
    assert body["version"] == "unknown"
    assert body["environment"] == "development"


def test_health_does_not_leak_database_error_details(client: TestClient, monkeypatch) -> None:
    secret_detail = 'password authentication failed for user "kanban" at db.internal:5432'

    def failing_execute(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception(secret_detail))

    monkeypatch.setattr(SessionLocal, "execute", failing_execute)
    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == {"message": "Database unreachable", "status": 503}
    assert "kanban" not in response.text
    assert "db.internal" not in response.text
