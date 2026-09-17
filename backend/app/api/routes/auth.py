"""Auth routes — signup, signin, me, signout."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.errors import AuthAppError
from app.models import User
from app.schemas import SigninRequest, SignupRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService
from app.api.deps import db_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(db_session)):
    _, token = AuthService(db).signup(payload.email, payload.password, payload.full_name)
    return TokenResponse(access_token=token)


@router.post("/signin", response_model=TokenResponse)
def signin(payload: SigninRequest, db: Session = Depends(db_session)):
    _, token = AuthService(db).signin(payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/signout")
def signout(user: User = Depends(get_current_user)):
    # Stateless JWT: the client discards the token; endpoint confirms a valid session.
    return {"detail": "Signed out"}
