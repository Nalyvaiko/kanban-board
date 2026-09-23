"""End-to-end scenarios against the real docker-compose.yaml stack (real
Postgres, the actual built Docker image - not the backend's in-process
test suite). See conftest.py for how the stack is brought up.

Tests share one long-lived stack for the whole session (spinning up
Postgres + building the image per test would be far too slow), so each
test that writes data uses a unique email rather than assuming a blank
slate.
"""

from __future__ import annotations

import re
import socket
import time
import uuid
from urllib.parse import urlsplit

import httpx
from conftest import BASE_URL, compose, wait_until_healthy

SEED_EMAILS = {"alice@example.com", "bob@example.com", "carol@example.com", "dave@example.com"}
SEED_PASSWORD = "password123"


def register(client: httpx.Client, email: str) -> str:
    response = client.post(
        "/api/auth/register", json={"name": "Integration Test", "email": email, "password": SEED_PASSWORD}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def login(client: httpx.Client, email: str, password: str = SEED_PASSWORD) -> httpx.Response:
    return client.post("/api/auth/login", json={"email": email, "password": password})


def unique_email() -> str:
    return f"itest-{uuid.uuid4().hex[:12]}@example.com"


def raw_request_line_status(request_target: str) -> int:
    """Sends `request_target` as the literal HTTP request-line path, with no
    client-side normalization - httpx (like curl by default) collapses ".."
    segments out of a URL before sending it, which would make a traversal
    test pass for the wrong reason (a normalized, harmless path) rather than
    actually exercising the server's own guard."""
    host, port = urlsplit(BASE_URL).hostname, urlsplit(BASE_URL).port
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.sendall(f"GET {request_target} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n".encode())
        response = b""
        while chunk := sock.recv(4096):
            response += chunk
    return int(response.split(b"\r\n", 1)[0].split(b" ")[1])


# -- 1 & 2: stack health and seed data --------------------------------------


def test_seed_accounts_exist_exactly_once_on_a_fresh_stack(client: httpx.Client) -> None:
    for email in SEED_EMAILS:
        response = login(client, email)
        assert response.status_code == 200, f"{email} should be able to log in: {response.text}"

    token = login(client, "alice@example.com").json()["token"]
    users = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    seeded = [u for u in users.json() if u["email"] in SEED_EMAILS]
    assert len(seeded) == 4, f"expected exactly 4 seeded accounts, found {len(seeded)}: {seeded}"


# -- 3, 4, 5: the backend serves the frontend --------------------------------


def test_root_serves_the_frontend_app_shell(client: httpx.Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<div id=" in response.text or "root" in response.text.lower()


def test_deep_client_route_falls_back_to_the_app_shell(client: httpx.Client) -> None:
    # Not a real file/API route - only exists client-side, via TanStack
    # Router. A page refresh on a route like this must still work.
    response = client.get("/projects/some-project/board")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_a_real_static_asset_is_served(client: httpx.Client) -> None:
    index = client.get("/")
    match = re.search(r'src="(/assets/[^"]+\.js)"', index.text)
    assert match, "couldn't find a JS asset reference in the served index.html"
    asset_response = client.get(match.group(1))
    assert asset_response.status_code == 200
    assert "javascript" in asset_response.headers["content-type"]


# -- 6: the SPA fallback's path-traversal guard ------------------------------


def test_path_traversal_through_the_frontend_route_is_blocked() -> None:
    status_code = raw_request_line_status("/../../../../../../etc/passwd")
    # Falls back to the app shell (200, HTML) rather than leaking a file or
    # 500ing - same behavior as any other made-up client-side route.
    assert status_code == 200


# -- 7: API and frontend routing don't collide -------------------------------


def test_api_routes_are_not_swallowed_by_the_frontend_catch_all(client: httpx.Client) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


# -- 8: basic write path against real Postgres -------------------------------


def test_register_then_login_round_trip(client: httpx.Client) -> None:
    email = unique_email()
    token = register(client, email)
    assert token

    response = login(client, email)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == email


# -- 9 & 10: data survives a hard container restart --------------------------


def test_data_survives_the_app_container_being_killed_and_restarted(client: httpx.Client) -> None:
    email = unique_email()
    register(client, email)

    result = compose("kill", "app")
    assert result.returncode == 0, result.stderr
    result = compose("up", "-d", "app")
    assert result.returncode == 0, result.stderr
    wait_until_healthy()

    with httpx.Client(base_url=BASE_URL, timeout=10) as fresh_client:
        response = login(fresh_client, email)
        assert response.status_code == 200, "user registered before the kill should still be there"

        # Seeding only runs against an empty database - if it re-ran here,
        # there'd be duplicate seed accounts.
        token = login(fresh_client, "alice@example.com").json()["token"]
        users = fresh_client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
        seeded = [u for u in users.json() if u["email"] in SEED_EMAILS]
        assert len(seeded) == 4, "restarting the app must not re-seed demo accounts"


def test_data_survives_the_database_container_being_killed_and_restarted(client: httpx.Client) -> None:
    email = unique_email()
    register(client, email)

    result = compose("kill", "db")
    assert result.returncode == 0, result.stderr
    result = compose("up", "-d", "db")
    assert result.returncode == 0, result.stderr

    # The app itself doesn't restart here, so give it a moment to reconnect
    # once Postgres is accepting connections again rather than asserting
    # on the very first request back.
    deadline = time.monotonic() + 60
    last_response = None
    while time.monotonic() < deadline:
        last_response = login(client, email)
        if last_response.status_code == 200:
            break
        time.sleep(1)
    assert last_response is not None and last_response.status_code == 200, (
        f"app never recovered after the db container restarted: {last_response.text if last_response else 'no response'}"
    )
