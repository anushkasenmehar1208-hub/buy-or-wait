"""Affordability routes — run the engine, list decision history, dashboard summary."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.errors import NotFoundAppError
from app.models import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas import (
    AffordabilityRequest, DecisionListResponse, PurchaseRequestResponse,
    to_request_response,
)
from app.services.affordability_service import AffordabilityService
from app.api.deps import db_session

router = APIRouter(prefix="/api/affordability", tags=["affordability"])

# Monthly-equivalent factors so the dashboard reflects every payer cadence,
# not just monthly ones (weekly ≈ 4.33 weeks/month).
_FREQUENCY_TO_MONTHLY = {
    "weekly": Decimal("52") / Decimal("12"),
    "biweekly": Decimal("26") / Decimal("12"),
    "semimonthly": Decimal("2"),
    "monthly": Decimal("1"),
}


@router.post("/check", response_model=PurchaseRequestResponse, status_code=201)
def check(payload: AffordabilityRequest, user: User = Depends(get_current_user),
          db: Session = Depends(db_session)):
    req = AffordabilityService(db).evaluate_and_save(str(user.id), payload)
    return to_request_response(req)


@router.get("/decisions", response_model=DecisionListResponse)
def decisions(user: User = Depends(get_current_user), db: Session = Depends(db_session),
              limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    service = AffordabilityService(db)
    items, total = service.list_for_user(str(user.id), limit, offset)
    return DecisionListResponse(
        items=[to_request_response(r) for r in items],
        total=total,
    )


@router.get("/decisions/{request_id}", response_model=PurchaseRequestResponse)
def decision_detail(request_id: str, user: User = Depends(get_current_user),
                    db: Session = Depends(db_session)):
    req = AffordabilityService(db).get_request(str(user.id), request_id)
    if not req:
        raise NotFoundAppError("Decision not found")
    return to_request_response(req)


@router.delete("/decisions/{request_id}", status_code=204)
def delete_decision(request_id: str, user: User = Depends(get_current_user),
                    db: Session = Depends(db_session)):
    AffordabilityService(db).delete_request(str(user.id), request_id)
    return None


@router.get("/summary")
def dashboard_summary(user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    """Dashboard facts — engine-derived, no invented scores."""
    profile = ProfileRepository(db).get_for_user(str(user.id))
    if not profile:
        return {"profile_exists": False}
    snap = ProfileRepository(db).snapshot(profile)

    # Safe-to-spend: the engine's own 90-day minimum buffer, floored at 0 —
    # the largest amount the user could pay today while staying above their minimum.
    from app.finance.adapter import compute_safe_to_spend

    safe_to_spend = compute_safe_to_spend(
        profile, snap["income"], snap["expenses"], snap["commitments"], snap["pending"]
    )

    service = AffordabilityService(db)
    recent, total = service.list_for_user(str(user.id), 5, 0)

    return {
        "profile_exists": True,
        "currency": profile.currency,
        "current_balance": profile.current_balance,
        "minimum_safe_balance": profile.minimum_safe_balance,
        "amount_safe_to_pay": safe_to_spend,
        "monthly_income": sum(
            (i.amount * _FREQUENCY_TO_MONTHLY.get(i.frequency, Decimal("1"))
             for i in snap["income"]),
            Decimal("0"),
        ).quantize(Decimal("0.01")),
        "upcoming_commitments": [
            {"id": c.id, "name": c.name, "amount": c.amount, "due_date": c.due_date}
            for c in snap["commitments"] if c.due_date >= date.today()
        ][:5],
        "upcoming_pending": [
            {"id": p.id, "name": p.name, "amount": p.amount, "due_date": p.due_date}
            for p in snap["pending"] if p.due_date >= date.today()
        ][:5],
        "recent_decisions": [to_request_response(r) for r in recent],
        "total_decisions": total,
    }
