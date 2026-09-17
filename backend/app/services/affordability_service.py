"""Affordability service — runs the untouched engine over the user's DB profile and
persists request + decision. Engine behavior is 100% preserved via the adapter."""
from datetime import date, timezone
from datetime import datetime as dt
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import NotFoundAppError
from app.finance.adapter import run_affordability
from app.models import AffordabilityDecision, PurchaseRequest
from app.repositories.decision_repository import DecisionRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas import AffordabilityRequest

_STATUS_TO_UI = {
    "affordable_now": "buy_now",
    "affordable_with_plan": "affordable_with_plan",
    "affordable_later": "wait",
    "not_affordable": "not_affordable",
}


def _parse_plan(plan: Optional[str]) -> list:
    """Engine plan strings are 'YYYY-MM-DD:amount|...' (home currency)."""
    if not plan or plan == "none":
        return []
    out = []
    for part in plan.split("|"):
        if ":" not in part:
            continue
        d_str, amt_str = part.split(":", 1)
        try:
            out.append({"date": d_str, "amount": Decimal(amt_str)})
        except Exception:
            continue
    return out


def _parse_changes(changes: Optional[str]) -> list:
    """Engine change strings are 'stop:<eid>' / 'reduce_to:<eid>:<amount>'."""
    if not changes or changes == "none":
        return []
    out = []
    for part in changes.split("|"):
        if part.startswith("stop:"):
            out.append({"action": "stop", "event_id": part[5:]})
        elif part.startswith("reduce_to:"):
            _, eid, amt = part.split(":", 2)
            try:
                out.append({"action": "reduce_to", "event_id": eid, "amount": Decimal(amt)})
            except Exception:
                continue
    return out


class AffordabilityService:
    def __init__(self, db: Session):
        self.db = db
        self.profiles = ProfileRepository(db)
        self.decisions = DecisionRepository(db)

    def evaluate_and_save(self, user_id: str, payload: AffordabilityRequest) -> PurchaseRequest:
        profile = self.profiles.get_for_user(user_id)
        if not profile:
            raise NotFoundAppError("Create your financial profile first")
        snap = self.profiles.snapshot(profile)
        currency = (payload.currency or profile.currency).upper()

        req = PurchaseRequest(
            profile_id=profile.id,
            item_name=payload.item_name,
            amount=payload.amount,
            currency=currency,
            deadline=payload.deadline,
        )
        self.db.add(req)
        self.db.flush()

        result = run_affordability(
            profile_row=profile,
            income_rows=snap["income"],
            expense_rows=snap["expenses"],
            commitment_rows=snap["commitments"],
            pending_rows=snap["pending"],
            request_id=req.id,
            amount=payload.amount,
            currency=currency,
            deadline=payload.deadline,
        )

        decision = AffordabilityDecision(
            request_id=req.id,
            user_id=user_id,
            affordability_status=_STATUS_TO_UI.get(
                result["affordability_status"], result["affordability_status"]
            ),
            amount_safe_to_pay=result["amount_safe_to_pay"],
            recommended_payment_method=result["recommended_payment_method"],
            payment_plan=result["payment_plan"],
            earliest_date_for_full_payment=(
                date.fromisoformat(result["earliest_date_for_full_payment"])
                if result["earliest_date_for_full_payment"] else None
            ),
            spending_changes_needed=result["spending_changes_needed"],
            decision_explanation=result["decision_explanation"] or "",
        )
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(req)
        return req

    def list_for_user(self, user_id: str, limit: int = 100, offset: int = 0):
        return self.decisions.list_requests_for_user(user_id, limit, offset), \
            self.decisions.count_requests_for_user(user_id)

    def get_request(self, user_id: str, request_id: str) -> Optional[PurchaseRequest]:
        return self.decisions.get_request_for_user(user_id, request_id)

    def delete_request(self, user_id: str, request_id: str) -> None:
        req = self.decisions.get_request_for_user(user_id, request_id)
        if not req:
            raise NotFoundAppError("Decision not found")
        self.db.delete(req)
        self.db.commit()
