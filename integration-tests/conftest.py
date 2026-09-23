"""Drives the real docker-compose.yaml stack for the tests in this
directory: `docker compose up --build` once per test session, then
`docker compose down -v` at the end. Individual tests talk to the running
stack over plain HTTP, the same way a real client would - nothing here
imports the backend's Python code.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://localhost:8000"
STARTUP_TIMEOUT_SECONDS = 90


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args], cwd=REPO_ROOT, check=check, capture_output=True, text=True
    )


def wait_until_healthy(timeout: float = STARTUP_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{BASE_URL}/docs", timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError as error:
            last_error = error
        time.sleep(1)
    raise TimeoutError(f"App never became reachable at {BASE_URL} within {timeout}s") from last_error


@pytest.fixture(scope="session", autouse=True)
def compose_stack():
    result = compose("up", "-d", "--build")
    if result.returncode != 0:
        raise RuntimeError(f"docker compose up failed:\n{result.stdout}\n{result.stderr}")
    try:
        wait_until_healthy()
        yield
    finally:
        compose("down", "-v", check=False)


@pytest.fixture()
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        yield client
