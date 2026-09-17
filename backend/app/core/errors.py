"""Cross-cutting exceptions mapped to HTTP responses in api/deps.py."""
from typing import Optional

from fastapi import status


class AppError(Exception):
    """Base for expected domain errors."""

    def __init__(self, message: str, status_code: int = 400, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationAppError(AppError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class NotFoundAppError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class AuthAppError(AppError):
    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(message, status_code)


class ConflictAppError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_409_CONFLICT)
