from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User


def require_roles(*roles: str) -> Callable:
    allowed = set(roles)

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return _checker
