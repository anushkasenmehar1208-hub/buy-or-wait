"""Financial profile repository — DB access for profiles and children."""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    FinancialCommitment, FinancialProfile, IncomeSource, PendingPayment, RecurringExpense,
)


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------ profile
    def get_for_user(self, user_id: str) -> Optional[FinancialProfile]:
        return (
            self.db.query(FinancialProfile)
            .filter(FinancialProfile.user_id == user_id)
            .one_or_none()
        )

    def create(self, user_id: str, data: dict) -> FinancialProfile:
        profile = FinancialProfile(user_id=user_id, **data)
        self.db.add(profile)
        self.db.flush()
        return profile

    def update(self, profile: FinancialProfile, data: dict) -> FinancialProfile:
        for key, value in data.items():
            setattr(profile, key, value)
        self.db.flush()
        return profile

    # ------------------------------------------------------------ income
    def add_income(self, profile_id: str, data: dict) -> IncomeSource:
        income = IncomeSource(profile_id=profile_id, **data)
        self.db.add(income)
        self.db.flush()
        return income

    def get_income(self, user_id: str, income_id: str) -> Optional[IncomeSource]:
        return (
            self.db.query(IncomeSource)
            .join(FinancialProfile, IncomeSource.profile_id == FinancialProfile.id)
            .filter(IncomeSource.id == income_id, FinancialProfile.user_id == user_id)
            .one_or_none()
        )

    def update_income(self, income: IncomeSource, data: dict) -> IncomeSource:
        for key, value in data.items():
            setattr(income, key, value)
        self.db.flush()
        return income

    def delete_income(self, income: IncomeSource) -> None:
        self.db.delete(income)

    # ------------------------------------------------------------ expenses
    def add_expense(self, profile_id: str, data: dict) -> RecurringExpense:
        expense = RecurringExpense(profile_id=profile_id, **data)
        self.db.add(expense)
        self.db.flush()
        return expense

    def get_expense(self, user_id: str, expense_id: str) -> Optional[RecurringExpense]:
        return (
            self.db.query(RecurringExpense)
            .join(FinancialProfile, RecurringExpense.profile_id == FinancialProfile.id)
            .filter(RecurringExpense.id == expense_id, FinancialProfile.user_id == user_id)
            .one_or_none()
        )

    def update_expense(self, expense: RecurringExpense, data: dict) -> RecurringExpense:
        for key, value in data.items():
            setattr(expense, key, value)
        self.db.flush()
        return expense

    def delete_expense(self, expense: RecurringExpense) -> None:
        self.db.delete(expense)

    # ------------------------------------------------------------ commitments
    def add_commitment(self, profile_id: str, data: dict) -> FinancialCommitment:
        commitment = FinancialCommitment(profile_id=profile_id, **data)
        self.db.add(commitment)
        self.db.flush()
        return commitment

    def get_commitment(self, user_id: str, commitment_id: str) -> Optional[FinancialCommitment]:
        return (
            self.db.query(FinancialCommitment)
            .join(FinancialProfile, FinancialCommitment.profile_id == FinancialProfile.id)
            .filter(FinancialCommitment.id == commitment_id, FinancialProfile.user_id == user_id)
            .one_or_none()
        )

    def update_commitment(self, commitment: FinancialCommitment, data: dict) -> FinancialCommitment:
        for key, value in data.items():
            setattr(commitment, key, value)
        self.db.flush()
        return commitment

    def delete_commitment(self, commitment: FinancialCommitment) -> None:
        self.db.delete(commitment)

    # ------------------------------------------------------------ pending
    def add_pending(self, profile_id: str, data: dict) -> PendingPayment:
        pending = PendingPayment(profile_id=profile_id, **data)
        self.db.add(pending)
        self.db.flush()
        return pending

    def get_pending(self, user_id: str, pending_id: str) -> Optional[PendingPayment]:
        return (
            self.db.query(PendingPayment)
            .join(FinancialProfile, PendingPayment.profile_id == FinancialProfile.id)
            .filter(PendingPayment.id == pending_id, FinancialProfile.user_id == user_id)
            .one_or_none()
        )

    def update_pending(self, pending: PendingPayment, data: dict) -> PendingPayment:
        for key, value in data.items():
            setattr(pending, key, value)
        self.db.flush()
        return pending

    def delete_pending(self, pending: PendingPayment) -> None:
        self.db.delete(pending)

    # ------------------------------------------------------------ aggregate
    def snapshot(self, profile: FinancialProfile) -> dict:
        """Full profile payload for the API / engine adapter."""
        return {
            "profile": profile,
            "income": list(profile.income_sources),
            "expenses": list(profile.recurring_expenses),
            "commitments": list(profile.commitments),
            "pending": list(profile.pending_payments),
        }
