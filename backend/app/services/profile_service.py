"""Profile service — business rules for the user's financial profile."""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import ConflictAppError, NotFoundAppError, ValidationAppError
from app.models import FinancialProfile
from app.repositories.profile_repository import ProfileRepository
from app.schemas import (
    CommitmentUpsert, ExpenseUpsert, IncomeUpsert, PendingUpsert, ProfileUpsert,
)


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProfileRepository(db)

    # ------------------------------------------------------------ profile
    def get(self, user_id: str) -> Optional[FinancialProfile]:
        return self.repo.get_for_user(user_id)

    def create(self, user_id: str, data: ProfileUpsert) -> FinancialProfile:
        if self.repo.get_for_user(user_id):
            raise ConflictAppError("Financial profile already exists")
        return self.repo.create(user_id, data.model_dump())

    def update(self, user_id: str, data: ProfileUpsert) -> FinancialProfile:
        profile = self._require(user_id)
        return self.repo.update(profile, data.model_dump())

    def upsert(self, user_id: str, data: ProfileUpsert) -> FinancialProfile:
        existing = self.repo.get_for_user(user_id)
        if existing:
            return self.repo.update(existing, data.model_dump())
        return self.repo.create(user_id, data.model_dump())

    def delete(self, user_id: str) -> None:
        profile = self._require(user_id)
        self.repo.delete_profile(profile)

    # ------------------------------------------------------------ income
    def add_income(self, user_id: str, data: IncomeUpsert):
        profile = self._require(user_id)
        return self.repo.add_income(profile.id, data.model_dump())

    def update_income(self, user_id: str, income_id: str, data: IncomeUpsert):
        income = self.repo.get_income(user_id, income_id)
        if not income:
            raise NotFoundAppError("Income source not found")
        return self.repo.update_income(income, data.model_dump())

    def delete_income(self, user_id: str, income_id: str) -> None:
        income = self.repo.get_income(user_id, income_id)
        if not income:
            raise NotFoundAppError("Income source not found")
        self.repo.delete_income(income)

    # ------------------------------------------------------------ expenses
    def add_expense(self, user_id: str, data: ExpenseUpsert):
        profile = self._require(user_id)
        return self.repo.add_expense(profile.id, data.model_dump())

    def update_expense(self, user_id: str, expense_id: str, data: ExpenseUpsert):
        expense = self.repo.get_expense(user_id, expense_id)
        if not expense:
            raise NotFoundAppError("Expense not found")
        return self.repo.update_expense(expense, data.model_dump())

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        expense = self.repo.get_expense(user_id, expense_id)
        if not expense:
            raise NotFoundAppError("Expense not found")
        self.repo.delete_expense(expense)

    # ------------------------------------------------------------ commitments
    def add_commitment(self, user_id: str, data: CommitmentUpsert):
        profile = self._require(user_id)
        return self.repo.add_commitment(profile.id, data.model_dump())

    def update_commitment(self, user_id: str, commitment_id: str, data: CommitmentUpsert):
        commitment = self.repo.get_commitment(user_id, commitment_id)
        if not commitment:
            raise NotFoundAppError("Commitment not found")
        return self.repo.update_commitment(commitment, data.model_dump())

    def delete_commitment(self, user_id: str, commitment_id: str) -> None:
        commitment = self.repo.get_commitment(user_id, commitment_id)
        if not commitment:
            raise NotFoundAppError("Commitment not found")
        self.repo.delete_commitment(commitment)

    # ------------------------------------------------------------ pending
    def add_pending(self, user_id: str, data: PendingUpsert):
        profile = self._require(user_id)
        return self.repo.add_pending(profile.id, data.model_dump())

    def update_pending(self, user_id: str, pending_id: str, data: PendingUpsert):
        pending = self.repo.get_pending(user_id, pending_id)
        if not pending:
            raise NotFoundAppError("Pending payment not found")
        return self.repo.update_pending(pending, data.model_dump())

    def delete_pending(self, user_id: str, pending_id: str) -> None:
        pending = self.repo.get_pending(user_id, pending_id)
        if not pending:
            raise NotFoundAppError("Pending payment not found")
        self.repo.delete_pending(pending)

    # ------------------------------------------------------------ helpers
    def _require(self, user_id: str) -> FinancialProfile:
        profile = self.repo.get_for_user(user_id)
        if not profile:
            raise NotFoundAppError("Create your financial profile first")
        return profile
