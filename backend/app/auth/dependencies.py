"""Auth dependencies — JWT bearer token → authenticated user."""
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthAppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.repositories.user_repository import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthAppError("Not authenticated")
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise AuthAppError("Invalid or expired token")
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise AuthAppError("User no longer exists")
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 (used by avatar GET,
    which <img> tags hit without an Authorization header and validate by URL
    signature instead)."""
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        return None
    return UserRepository(db).get_by_id(user_id)
