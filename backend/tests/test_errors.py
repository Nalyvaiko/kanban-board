"""Every error response must match openapi.yaml's `Error` schema:
`{"message": str, "status": int}` at the top level - not wrapped in
FastAPI's default `{"detail": ...}`."""

from __future__ import annotations

from .conftest import auth_header, register


def _assert_error(response, status: int, message: str | None = None) -> dict:
    assert response.status_code == status, response.text
    body = response.json()
    assert "detail" not in body
    assert body["status"] == status
    assert isinstance(body["message"], str) and body["message"]
    if message is not None:
        assert body["message"] == message
    return body


def test_api_errors_are_not_wrapped_in_detail(client, admin):
    _assert_error(client.get("/api/projects/proj_missing", headers=admin["headers"]), 404, "Project not found")
    _assert_error(
        client.post("/api/projects", json={"name": "  "}, headers=admin["headers"]), 400, "Project name is required"
    )
    _assert_error(
        client.post("/api/projects", json={"name": "Again", "key": "DEMO"}, headers=admin["headers"]),
        409,
        "That project key is already in use",
    )


def test_auth_errors_use_the_error_shape(client, admin):
    _assert_error(client.get("/api/projects"), 401, "Sign in required")

    outsider = register(client, "Mallory", "mallory@example.com")
    _assert_error(
        client.get(f"/api/projects/{admin['project']['id']}", headers=auth_header(outsider["token"])),
        403,
        "You are not a member of this project",
    )


def test_unknown_route_and_wrong_method_use_the_error_shape(client, admin):
    _assert_error(client.get("/api/no-such-endpoint", headers=admin["headers"]), 404)
    _assert_error(client.put("/api/health"), 405)


def test_validation_errors_keep_422_and_name_the_field(client):
    response = client.post("/api/auth/register", json={"name": "Bob", "email": "not-an-email", "password": "x" * 8})
    body = _assert_error(response, 422)
    assert body["message"].startswith("email: ")
    assert [e["field"] for e in body["errors"]] == ["email"]


def test_validation_error_for_a_missing_field(client):
    body = _assert_error(client.post("/api/auth/login", json={"email": "a@example.com"}), 422)
    assert body["message"].startswith("password: ")


def test_validation_error_for_a_bad_query_parameter(client, admin):
    response = client.get(
        f"/api/projects/{admin['project']['id']}/tasks", params={"priority": "whenever"}, headers=admin["headers"]
    )
    body = _assert_error(response, 422)
    assert body["message"].startswith("priority: ")
