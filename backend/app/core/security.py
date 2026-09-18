"""Security utilities — password hashing (bcrypt), JWT (HS256), avatar URL signatures."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.access_token_expire_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Return the subject (user id) or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------- avatar URLs
# <img> elements cannot send an Authorization header, so avatar *reads* use an
# HMAC-signed URL instead (same idea as S3 presigned URLs). Mutations (upload/
# delete) always require the JWT. The signature is derived from SECRET_KEY and
# the user's current avatar timestamp, so it stops working the moment the
# avatar changes and leaks grant read access to one user's picture only.


def avatar_url_signature(user_id: str, version: int) -> str:
    payload = f"avatar:{user_id}:{version}".encode()
    return hmac.new(settings.secret_key.encode(), payload, hashlib.sha256).hexdigest()


def verify_avatar_url_signature(user_id: str, version: int, signature: str) -> bool:
    if not signature or not version:
        return False
    expected = avatar_url_signature(user_id, version)
    return hmac.compare_digest(expected, signature)
