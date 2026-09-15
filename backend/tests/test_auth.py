from __future__ import annotations

from .conftest import auth_header, register


def test_register_creates_account_and_token(client):
    session = register(client, "Alice", "alice@example.com")
    assert session["user"]["email"] == "alice@example.com"
    assert session["user"]["provider"] == "password"
    assert session["token"]

    # The password is never echoed back or stored in the clear.
    assert "password" not in session["user"]


def test_register_rejects_duplicate_email(client):
    register(client, "Alice", "alice@example.com")
    response = client.post(
        "/api/auth/register",
        json={"name": "Alice Two", "email": "alice@example.com", "password": "password123"},
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/auth/register", json={"name": "Alice", "email": "alice@example.com", "password": "abc"}
    )
    assert response.status_code == 400


def test_login_succeeds_with_correct_credentials(client):
    register(client, "Alice", "alice@example.com", password="correct-horse")
    response = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "correct-horse"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "alice@example.com"


def test_login_rejects_wrong_password(client):
    register(client, "Alice", "alice@example.com", password="correct-horse")
    response = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


def test_me_without_token_returns_null(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() is None


def test_me_with_token_returns_current_user(client):
    session = register(client, "Alice", "alice@example.com")
    response = client.get("/api/auth/me", headers=auth_header(session["token"]))
    assert response.status_code == 200
    assert response.json()["id"] == session["user"]["id"]


def test_protected_endpoint_without_token_is_401(client):
    response = client.get("/api/projects")
    assert response.status_code == 401


def test_protected_endpoint_with_bad_token_is_401(client):
    response = client.get("/api/projects", headers=auth_header("not-a-real-token"))
    assert response.status_code == 401


def test_update_profile_changes_name(client):
    session = register(client, "Alice", "alice@example.com")
    response = client.patch(
        "/api/auth/me", json={"name": "Alice Renamed"}, headers=auth_header(session["token"])
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Alice Renamed"


def test_logout_revokes_the_token(client):
    session = register(client, "Alice", "alice@example.com")
    headers = auth_header(session["token"])

    assert client.get("/api/projects", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/projects", headers=headers).status_code == 401


def test_passwords_are_hashed_at_rest(client):
    from kanban_backend.store import store

    register(client, "Alice", "alice@example.com", password="correct-horse")
    (user_id,) = store.users.keys()
    stored = store.credentials[user_id]
    assert "correct-horse" not in stored
    assert "$" in stored
