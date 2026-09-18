"""Account routes — profile update, avatar upload/get/delete, account deletion.

All routes authenticate via the JWT bearer token and act exclusively on the
authenticated principal; no user id is ever accepted from the client.
"""
from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.routes.auth import _with_avatar_url
from app.auth.dependencies import get_current_user, get_optional_user
from app.core.errors import AuthAppError, ValidationAppError
from app.core.security import verify_avatar_url_signature
from app.models import User
from app.schemas import UpdateProfileRequest, UserResponse
from app.services.user_service import MAX_AVATAR_BYTES, UserService

router = APIRouter(prefix="/api/account", tags=["account"])


def _service(db: Session) -> UserService:
    return UserService(db)


@router.put("/profile", response_model=UserResponse)
def update_profile(payload: UpdateProfileRequest,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(db_session)):
    return _with_avatar_url(_service(db).update_profile(str(user.id), payload.full_name))


@router.put("/avatar", response_model=UserResponse)
async def upload_avatar(file: UploadFile = File(...),
                        user: User = Depends(get_current_user),
                        db: Session = Depends(db_session)):
    declared = file.content_type or ""
    if declared not in ("image/png", "image/jpeg", "image/webp"):
        raise ValidationAppError("Unsupported image type. Use PNG, JPEG, or WebP.")
    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise ValidationAppError("Image is too large. Maximum size is 2 MB.")
    return _with_avatar_url(_service(db).set_avatar(str(user.id), content, declared))


@router.get("/avatar")
def get_avatar(user_id: str = "", v: int = 0, sig: str = "",
               user: User = Depends(get_optional_user),
               db: Session = Depends(db_session)):
    """Serve an avatar image.

    Access paths:
      * JWT bearer → serve the authenticated user's own avatar (fetch/XHR).
      * No JWT → serve the user named in the URL, but only with a valid HMAC
        signature over (user_id, version). <img> tags cannot send
        Authorization headers; the signature is an unguessable server-minted
        capability (same model as presigned object URLs). It reaches the
        client exclusively via authenticated responses, covers one user's
        picture only, and dies whenever the avatar changes (version binds to
        avatar_updated_at).
    """
    if user is not None:
        target_id = str(user.id)
    elif user_id and v and verify_avatar_url_signature(user_id, v, sig):
        target_id = user_id
    else:
        raise AuthAppError("Not authenticated")
    avatar = _service(db).get_avatar(target_id)
    return Response(
        content=avatar.data,
        media_type=avatar.content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete("/avatar", response_model=UserResponse)
def delete_avatar(user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    return _with_avatar_url(_service(db).delete_avatar(str(user.id)))


@router.delete("", status_code=204)
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    _service(db).delete_account(str(user.id))
    return Response(status_code=204)
