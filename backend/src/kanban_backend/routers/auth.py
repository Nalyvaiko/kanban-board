from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from .. import auth
from ..errors import ApiError, unauthorized
from ..models import (
    GoogleLoginInput,
    LoginInput,
    Provider,
    RegisterInput,
    TokenResponse,
    UpdateProfileInput,
    User,
    utcnow_iso,
)
from ..store import new_id, store

router = APIRouter(tags=["Auth"])


@router.post("/auth/register", status_code=201, response_model=TokenResponse)
def register(input: RegisterInput) -> TokenResponse:
    if not input.name.strip():
        raise ApiError(400, "Name is required")
    if len(input.password) < 6:
        raise ApiError(400, "Password must be at least 6 characters")
    email = input.email.lower()
    if any(u.email.lower() == email for u in store.users.values()):
        raise ApiError(409, "An account with that email already exists")

    now = utcnow_iso()
    palette = ["#3b82f6", "#f97316", "#10b981", "#a855f7", "#ef4444", "#06b6d4"]
    user = User(
        id=new_id("user"),
        name=input.name.strip(),
        email=email,
        avatarColor=palette[len(store.users) % len(palette)],
        provider=Provider.password,
        createdAt=now,
    )
    store.users[user.id] = user
    store.credentials[user.id] = auth.hash_password(input.password)
    token = auth.issue_token(user.id)
    return TokenResponse(token=token, user=user)


@router.post("/auth/login", response_model=TokenResponse)
def login(input: LoginInput) -> TokenResponse:
    email = input.email.lower()
    user = next((u for u in store.users.values() if u.email.lower() == email), None)
    stored_hash = store.credentials.get(user.id) if user else None
    if user is None or stored_hash is None or not auth.verify_password(input.password, stored_hash):
        raise unauthorized("Incorrect email or password")
    token = auth.issue_token(user.id)
    return TokenResponse(token=token, user=user)


@router.post("/auth/google", response_model=TokenResponse)
def login_with_google(input: GoogleLoginInput) -> TokenResponse:
    # MVP stand-in: a real implementation verifies `idToken` with Google and
    # reads the verified email/name from its claims. Here we just require a
    # non-empty token and derive a stable demo identity from it, creating
    # the account on first sign-in.
    if not input.idToken.strip():
        raise unauthorized("The Google token could not be verified")

    email = f"{input.idToken.strip()[:24].lower()}@google.example"
    user = next((u for u in store.users.values() if u.email.lower() == email), None)
    if user is None:
        now = utcnow_iso()
        user = User(
            id=new_id("user"),
            name="Google User",
            email=email,
            avatarColor="#3b82f6",
            provider=Provider.google,
            createdAt=now,
        )
        store.users[user.id] = user
    token = auth.issue_token(user.id)
    return TokenResponse(token=token, user=user)


@router.post("/auth/logout", status_code=204)
def logout(token: str | None = Depends(auth.get_token_optional)) -> Response:
    if token:
        auth.revoke_token(token)
    return Response(status_code=204)


@router.get("/auth/me", response_model=User | None)
def get_me(user: User | None = Depends(auth.get_current_user_optional)) -> User | None:
    return user


@router.patch("/auth/me", response_model=User)
def update_me(input: UpdateProfileInput, user: User = Depends(auth.get_current_user)) -> User:
    user.name = input.name
    return user
