"""Unit tests for the store/seed modules directly, without going through
the HTTP layer.
"""

from __future__ import annotations

from kanban_backend import auth
from kanban_backend.seed import DEMO_PASSWORD, seed_demo_data
from kanban_backend.store import Store


def test_seed_produces_internally_consistent_data():
    db = Store()
    seed_demo_data(db)

    assert len(db.users) >= 4
    assert len(db.projects) == 2

    for task in db.tasks.values():
        assert task.projectId in db.projects
        assert task.boardId in db.boards
        assert task.columnId in db.columns
        assert db.columns[task.columnId].boardId == task.boardId
        if task.assigneeId is not None:
            assert task.assigneeId in db.users
        for label_id in task.labelIds:
            assert label_id in db.labels

    for member in db.members.values():
        assert member.projectId in db.projects
        assert member.userId in db.users

    # Every project has at least one admin.
    for project in db.projects.values():
        admins = [m for m in db.members.values() if m.projectId == project.id and m.role.value == "admin"]
        assert admins, f"{project.name} has no admin"


def test_seeded_users_can_log_in_with_the_documented_demo_password():
    db = Store()
    seed_demo_data(db)

    for stored_hash in db.credentials.values():
        assert auth.verify_password(DEMO_PASSWORD, stored_hash)
        assert not auth.verify_password("wrong-password", stored_hash)


def test_password_hashing_is_salted_and_verifiable():
    hash_a = auth.hash_password("same-password")
    hash_b = auth.hash_password("same-password")
    assert hash_a != hash_b  # different salts
    assert auth.verify_password("same-password", hash_a)
    assert auth.verify_password("same-password", hash_b)
    assert not auth.verify_password("different", hash_a)


def test_store_reset_clears_everything():
    db = Store()
    seed_demo_data(db)
    assert db.users

    db.reset()

    assert not db.users
    assert not db.projects
    assert not db.tasks
    assert not db.tokens
