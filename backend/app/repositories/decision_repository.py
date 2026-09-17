"""Decision repository — purchase requests + affordability decisions."""
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import AffordabilityDecision, PurchaseRequest


def _profile_user_filter(user_id: str):
    from app.models import FinancialProfile
    return FinancialProfile.user_id == user_id


class DecisionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_requests_for_user(self, user_id: str, limit: int = 50, offset: int = 0):
        return (
            self.db.query(PurchaseRequest)
            .filter(PurchaseRequest.profile.has(_profile_user_filter(user_id)))
            .order_by(PurchaseRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_requests_for_user(self, user_id: str) -> int:
        return (
            self.db.query(PurchaseRequest)
            .filter(PurchaseRequest.profile.has(_profile_user_filter(user_id)))
            .count()
        )

    def get_request_for_user(self, user_id: str, request_id: str) -> Optional[PurchaseRequest]:
        return (
            self.db.query(PurchaseRequest)
            .filter(
                PurchaseRequest.id == request_id,
                PurchaseRequest.profile.has(_profile_user_filter(user_id)),
            )
            .one_or_none()
        )
