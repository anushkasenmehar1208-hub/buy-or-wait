"""Profile routes — financial profile + income/expenses/commitments/pending, all
ownership-scoped via the authenticated user id."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.models import User
from app.schemas import (
    CommitmentResponse, CommitmentUpsert, ExpenseResponse, ExpenseUpsert, IncomeResponse,
    IncomeUpsert, PendingResponse, PendingUpsert, ProfileResponse, ProfileUpsert,
)
from app.services.profile_service import ProfileService
from app.api.deps import db_session

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _service(db: Session) -> ProfileService:
    return ProfileService(db)


@router.get("", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    profile = _service(db).get(str(user.id))
    if not profile:
        return Response(status_code=204)
    return ProfileResponse.from_profile(profile)


@router.post("", response_model=ProfileResponse, status_code=201)
def create_profile(payload: ProfileUpsert, user: User = Depends(get_current_user),
                   db: Session = Depends(db_session)):
    profile = _service(db).create(str(user.id), payload)
    db.commit()
    return ProfileResponse.from_profile(profile)


@router.put("", response_model=ProfileResponse)
def update_profile(payload: ProfileUpsert, user: User = Depends(get_current_user),
                   db: Session = Depends(db_session)):
    profile = _service(db).update(str(user.id), payload)
    db.commit()
    return ProfileResponse.from_profile(profile)


@router.delete("", status_code=204)
def delete_profile(user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    _service(db).delete(str(user.id))
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- income
@router.post("/income", response_model=IncomeResponse, status_code=201)
def add_income(payload: IncomeUpsert, user: User = Depends(get_current_user),
               db: Session = Depends(db_session)):
    income = _service(db).add_income(str(user.id), payload)
    db.commit()
    return income


@router.put("/income/{income_id}", response_model=IncomeResponse)
def update_income(income_id: str, payload: IncomeUpsert,
                  user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    income = _service(db).update_income(str(user.id), income_id, payload)
    db.commit()
    return income


@router.delete("/income/{income_id}", status_code=204)
def delete_income(income_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(db_session)):
    _service(db).delete_income(str(user.id), income_id)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- expenses
@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
def add_expense(payload: ExpenseUpsert, user: User = Depends(get_current_user),
                db: Session = Depends(db_session)):
    expense = _service(db).add_expense(str(user.id), payload)
    db.commit()
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: str, payload: ExpenseUpsert,
                   user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    expense = _service(db).update_expense(str(user.id), expense_id, payload)
    db.commit()
    return expense


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(db_session)):
    _service(db).delete_expense(str(user.id), expense_id)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- commitments
@router.post("/commitments", response_model=CommitmentResponse, status_code=201)
def add_commitment(payload: CommitmentUpsert, user: User = Depends(get_current_user),
                   db: Session = Depends(db_session)):
    commitment = _service(db).add_commitment(str(user.id), payload)
    db.commit()
    return commitment


@router.put("/commitments/{commitment_id}", response_model=CommitmentResponse)
def update_commitment(commitment_id: str, payload: CommitmentUpsert,
                      user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    commitment = _service(db).update_commitment(str(user.id), commitment_id, payload)
    db.commit()
    return commitment


@router.delete("/commitments/{commitment_id}", status_code=204)
def delete_commitment(commitment_id: str, user: User = Depends(get_current_user),
                      db: Session = Depends(db_session)):
    _service(db).delete_commitment(str(user.id), commitment_id)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- pending payments
@router.post("/pending", response_model=PendingResponse, status_code=201)
def add_pending(payload: PendingUpsert, user: User = Depends(get_current_user),
                db: Session = Depends(db_session)):
    pending = _service(db).add_pending(str(user.id), payload)
    db.commit()
    return pending


@router.put("/pending/{pending_id}", response_model=PendingResponse)
def update_pending(pending_id: str, payload: PendingUpsert,
                   user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    pending = _service(db).update_pending(str(user.id), pending_id, payload)
    db.commit()
    return pending


@router.delete("/pending/{pending_id}", status_code=204)
def delete_pending(pending_id: str, user: User = Depends(get_current_user),
                   db: Session = Depends(db_session)):
    _service(db).delete_pending(str(user.id), pending_id)
    db.commit()
    return Response(status_code=204)
