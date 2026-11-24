from __future__ import annotations

import pytest

from kanban_backend import auth
from kanban_backend.routers.attachments import MAX_FILE_SIZE, MAX_FILENAME_LENGTH, _clean_filename


def _task(client, admin):
    response = client.post(
        "/api/tasks",
        json={
            "projectId": admin["project"]["id"],
            "boardId": admin["board"]["id"],
            "columnId": admin["columns"][0]["id"],
            "title": "Has files",
        },
        headers=admin["headers"],
    )
    return response.json()


def _upload(client, admin, task, filename, content=b"hello"):
    return client.post(
        f"/api/tasks/{task['id']}/attachments",
        files={"file": (filename, content, "text/plain")},
        headers=admin["headers"],
    )


def test_upload_records_size_and_type(client, admin):
    task = _task(client, admin)
    response = _upload(client, admin, task, "notes.txt", b"x" * 1234)
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["fileSize"] == 1234
    assert body["fileType"] == "text/plain"


def test_upload_at_limit_is_accepted_and_over_limit_rejected(client, admin):
    task = _task(client, admin)
    assert _upload(client, admin, task, "max.bin", b"x" * MAX_FILE_SIZE).status_code == 201
    assert _upload(client, admin, task, "big.bin", b"x" * (MAX_FILE_SIZE + 1)).status_code == 400
    names = [a["filename"] for a in client.get(f"/api/tasks/{task['id']}/attachments", headers=admin["headers"]).json()]
    assert names == ["max.bin"]


@pytest.mark.parametrize(
    ("sent", "stored"),
    [
        ("C:\\Users\\me\\report.pdf", "report.pdf"),
        ("../../etc/passwd", "passwd"),
        ("  spaced.txt  ", "spaced.txt"),
    ],
)
def test_filenames_are_reduced_to_a_clean_basename(client, admin, sent, stored):
    task = _task(client, admin)
    response = _upload(client, admin, task, sent)
    assert response.status_code == 201
    assert response.json()["filename"] == stored


@pytest.mark.parametrize("sent", ["..", "../.."])
def test_unusable_filenames_are_rejected(client, admin, sent):
    task = _task(client, admin)
    assert _upload(client, admin, task, sent).status_code == 400


# The HTTP client percent-encodes control characters in the multipart
# header, so these go straight at the helper a raw request would reach.
@pytest.mark.parametrize(
    ("raw", "cleaned"),
    [
        ("bad\x00\x1fname.txt", "badname.txt"),
        ("line\nbreak.txt", "linebreak.txt"),
        ("\x00\x01", None),
        ("", None),
        (None, None),
    ],
)
def test_clean_filename_strips_control_characters(raw, cleaned):
    assert _clean_filename(raw) == cleaned


def test_long_filenames_are_truncated_keeping_the_extension(client, admin):
    task = _task(client, admin)
    name = _upload(client, admin, task, "a" * 400 + ".pdf").json()["filename"]
    assert len(name) == MAX_FILENAME_LENGTH
    assert name.endswith(".pdf")


def test_storage_url_is_url_encoded(client, admin):
    task = _task(client, admin)
    body = _upload(client, admin, task, "q3 report #2?.txt").json()
    assert body["filename"] == "q3 report #2?.txt"
    assert body["storageUrl"].endswith("/q3%20report%20%232%3F.txt")


def test_failed_login_does_the_same_hashing_work_for_unknown_emails(client, admin, monkeypatch):
    calls = []
    real_verify = auth.verify_password
    monkeypatch.setattr(auth, "verify_password", lambda pw, stored: calls.append(stored) or real_verify(pw, stored))

    wrong_password = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "nope-nope"})
    unknown_email = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope-nope"})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert len(calls) == 2  # one PBKDF2 verification each - no shortcut for the unknown email


def test_google_only_account_cannot_log_in_with_a_password(client):
    google = client.post("/api/auth/google", json={"idToken": "some-google-token"}).json()
    response = client.post("/api/auth/login", json={"email": google["user"]["email"], "password": "anything"})
    assert response.status_code == 401
