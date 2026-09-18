"""User account service — profile updates, avatar storage, account deletion.

Avatar bytes live in the `user_avatars` table (bytea). Rationale: the app runs
on hosts with ephemeral disks (Render free tier), so file-system storage would
silently lose uploads; Postgres (Neon) is the durable layer the project already
uses, keeps avatar deletion transactional with account deletion via FK cascade,
and needs no new paid service. Images are size-capped (2 MB) and constrained
to PNG/JPEG/WebP, which keeps rows small and Content-Type honest.

Ownership: every method takes the authenticated user's id (a str) — mirroring
ProfileService — and re-fetches the row in its own session. A caller can never
name another user because the id comes from the verified JWT, never the client.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import NotFoundAppError, ValidationAppError
from app.models import User, UserAvatar
from app.repositories.user_repository import UserRepository

MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB
ALLOWED_AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _validate_image(content: bytes, content_type: str) -> str:
    if content_type not in ALLOWED_AVATAR_TYPES:
        raise ValidationAppError(
            "Unsupported image type. Use PNG, JPEG, or WebP.",
            {"details": {"allowed": sorted(ALLOWED_AVATAR_TYPES)}},
        )
    if not content:
        raise ValidationAppError("The selected file is empty.")
    if len(content) > MAX_AVATAR_BYTES:
        raise ValidationAppError("Image is too large. Maximum size is 2 MB.")
    # Magic-byte check: never trust the client-declared Content-Type alone.
    sigs = ((b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"RIFF", "image/webp"))
    if not any(content.startswith(sig) for sig, _ in sigs):
        raise ValidationAppError("That file does not look like a valid image.")
    return content_type


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def _user(self, user_id: str) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundAppError("User no longer exists")
        return user

    # ---------------------------------------------------------------- account
    def update_profile(self, user_id: str, full_name: str) -> User:
        user = self._user(user_id)
        user.full_name = full_name.strip()
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # ---------------------------------------------------------------- avatar
    def set_avatar(self, user_id: str, content: bytes, content_type: str) -> User:
        user = self._user(user_id)
        validated_type = _validate_image(content, content_type)
        avatar = self.db.get(UserAvatar, user_id)
        if avatar is None:
            avatar = UserAvatar(user_id=user_id, content_type=validated_type, data=content)
        else:
            avatar.content_type = validated_type
            avatar.data = content
        self.db.add(avatar)
        user.avatar_updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_avatar(self, user_id: str) -> UserAvatar:
        avatar = self.db.get(UserAvatar, user_id)
        if avatar is None:
            raise NotFoundAppError("Avatar not found")
        return avatar

    def delete_avatar(self, user_id: str) -> User:
        user = self._user(user_id)
        avatar = self.db.get(UserAvatar, user_id)
        if avatar is None:
            raise NotFoundAppError("Avatar not found")
        self.db.delete(avatar)
        user.avatar_updated_at = None
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # ---------------------------------------------------------------- delete
    def delete_account(self, user_id: str) -> None:
        """Delete the user; all owned rows go via FK ON DELETE CASCADE.

        Verifies the row is actually gone before returning.
        """
        user = self._user(user_id)
        self.db.delete(user)
        self.db.commit()
        if self.users.get_by_id(user_id) is not None:
            raise NotFoundAppError("Account could not be deleted")
