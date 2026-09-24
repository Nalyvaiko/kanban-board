from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_ok_with_no_auth(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
