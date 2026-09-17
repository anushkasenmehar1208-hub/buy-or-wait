"""Authentication service — signup/signin/business rules, no HTTP concerns."""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import AuthAppError, ConflictAppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def signup(self, email: str, password: str, full_name: str) -> tuple[User, str]:
        email = email.strip().lower()
        if self.users.get_by_email(email):
            raise ConflictAppError("An account with this email already exists")
        user = User(email=email, full_name=full_name.strip(), password_hash=hash_password(password))
        self.db.add(user)
        self.db.commit()
        return user, create_access_token(user.id)

    def signin(self, email: str, password: str) -> tuple[User, str]:
        email = email.strip().lower()
        user = self.users.get_by_email(email)
        # Uniform error — never reveal whether the email exists.
        if not user or not verify_password(password, user.password_hash):
            raise AuthAppError("Invalid email or password", 401)
        return user, create_access_token(user.id)

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get_by_id(user_id)
