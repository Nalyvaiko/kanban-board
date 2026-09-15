from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import auth
from ..models import User
from ..store import store

router = APIRouter(tags=["Users"])


@router.get("/users", response_model=list[User])
def list_users(_: User = Depends(auth.get_current_user)) -> list[User]:
    return list(store.users.values())
