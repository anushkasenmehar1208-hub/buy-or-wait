"""User repository — all direct DB access for users."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower()).one_or_none()

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.get(User, user_id)

    def create(self, email: str, password_hash: str, full_name: str) -> User:
        user = User(email=email.lower(), password_hash=password_hash, full_name=full_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
