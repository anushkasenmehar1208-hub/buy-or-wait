"""Shared API dependencies — DB session + error mapping."""
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models import User
from app.auth.dependencies import get_current_user


def db_session(request: Request):
    """Yield a session bound to the request lifecycle."""
    db = next(get_db())
    request.state.db = db
    try:
        yield db
    finally:
        db.close()


def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.__class__.__name__, "message": exc.message,
                           "details": exc.details}},
    )


CurrentUser = User
__all__ = ["db_session", "app_error_handler", "get_current_user", "CurrentUser", "Depends"]
