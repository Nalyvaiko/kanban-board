"""Password hashing, bearer tokens, and the auth/role dependencies routers
use to guard endpoints.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib `hashlib`, no extra
dependency) and salted per-user. Sessions are opaque bearer tokens, handed
to the client by `/auth/register`, `/auth/login`, and `/auth/google`, and
sent back as `Authorization: Bearer <token>`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import forbidden, unauthorized
from .models import ProjectMember, Role, User
from .store import Store, store

_PBKDF2_ITERATIONS = 200_000

# auto_error=False so routes that allow anonymous access (e.g. GET /auth/me)
# can inspect "no credentials" themselves instead of getting a 403 from
# FastAPI's security layer before the handler even runs.
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hex_digest = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), hex_digest)


def issue_token(user_id: str, db: Store = store) -> str:
    token = secrets.token_urlsafe(32)
    db.tokens[token] = user_id
    return token


def revoke_token(token: str, db: Store = store) -> None:
    db.tokens.pop(token, None)


def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None, db: Store
) -> User | None:
    if credentials is None:
        return None
    user_id = db.tokens.get(credentials.credentials)
    if user_id is None:
        return None
    return db.users.get(user_id)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User | None:
    return _user_from_credentials(credentials, store)


def get_token_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    return credentials.credentials if credentials else None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    user = _user_from_credentials(credentials, store)
    if user is None:
        raise unauthorized("Sign in required")
    return user


# ---------------------------------------------------------------------------
# Project-role helpers
# ---------------------------------------------------------------------------


def require_member(project_id: str, user: User, db: Store = store) -> ProjectMember:
    """Raise 403 unless `user` belongs to `project_id`; otherwise return the membership."""
    member = db.get_member(project_id, user.id)
    if member is None:
        raise forbidden("You are not a member of this project")
    return member


def require_role(project_id: str, user: User, roles: set[Role], db: Store = store) -> ProjectMember:
    """Raise 403 unless `user`'s role on `project_id` is one of `roles`."""
    member = require_member(project_id, user, db)
    if member.role not in roles:
        raise forbidden("You do not have permission to perform this action")
    return member


def require_admin(project_id: str, user: User, db: Store = store) -> ProjectMember:
    return require_role(project_id, user, {Role.admin}, db)


def require_contributor(project_id: str, user: User, db: Store = store) -> ProjectMember:
    """member or admin - i.e. anyone but a viewer."""
    return require_role(project_id, user, {Role.admin, Role.member}, db)
