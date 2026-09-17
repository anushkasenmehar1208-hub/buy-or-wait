"""SQLAlchemy ORM models — users own everything below them."""
from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from typing import Optional

from sqlalchemy import (
    JSON, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[Optional["FinancialProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    minimum_safe_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    allows_partial_payment: Mapped[bool] = mapped_column(nullable=False, default=True)
    max_installment_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Payment methods the engine may recommend: full_payment | partial_payment | installments
    payment_methods: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: ["full_payment", "partial_payment", "installments"]
    )
    # Categories the user agrees to stop / reduce (engine spending-change candidates).
    stoppable_categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reducible_categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    user: Mapped[User] = relationship(back_populates="profile")
    income_sources: Mapped[list["IncomeSource"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="IncomeSource.created_at"
    )
    recurring_expenses: Mapped[list["RecurringExpense"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="RecurringExpense.created_at"
    )
    commitments: Mapped[list["FinancialCommitment"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="FinancialCommitment.due_date"
    )
    pending_payments: Mapped[list["PendingPayment"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="PendingPayment.due_date"
    )
    requests: Mapped[list["PurchaseRequest"]] = relationship(back_populates="profile")

    __table_args__ = (
        Index("ix_profiles_user", "user_id"),
    )


class IncomeSource(Base):
    """Salary / gig income. frequency: weekly | biweekly | semimonthly | monthly.

    next_date anchors the pay schedule; end_date marks fixed-term income.
    """
    __tablename__ = "income_sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(
        SAEnum("weekly", "biweekly", "semimonthly", "monthly", name="income_frequency"),
        nullable=False,
    )
    next_date: Mapped["date"] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional["date"]] = mapped_column(Date, nullable=True)  # fixed-term income
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[FinancialProfile] = relationship(back_populates="income_sources")


class RecurringExpense(Base):
    """Recurring expense (rent, utilities, subscriptions...)."""
    __tablename__ = "recurring_expenses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(
        SAEnum("rent", "utilities", "insurance", "loan", "subscription", "groceries", "other",
               name="expense_category"),
        nullable=False, default="other",
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(
        SAEnum("weekly", "biweekly", "semimonthly", "monthly", name="expense_frequency"),
        nullable=False,
    )
    next_date: Mapped["date"] = mapped_column(Date, nullable=False)
    minimum_allowed_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    essential: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[FinancialProfile] = relationship(back_populates="recurring_expenses")


class FinancialCommitment(Base):
    """A one-off future obligation: installment, loan payoff, planned purchase."""
    __tablename__ = "financial_commitments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    due_date: Mapped["date"] = mapped_column(Date, nullable=False)
    is_installment: Mapped[bool] = mapped_column(nullable=False, default=False)
    installment_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[FinancialProfile] = relationship(back_populates="commitments")


class PendingPayment(Base):
    """Committed-but-unpaid amount that must be reserved from the balance."""
    __tablename__ = "pending_payments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    due_date: Mapped["date"] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[FinancialProfile] = relationship(back_populates="pending_payments")


class PurchaseRequest(Base):
    """A "can I afford this?" check the user ran."""
    __tablename__ = "purchase_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("financial_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    deadline: Mapped[Optional["date"]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped[FinancialProfile] = relationship(back_populates="requests")
    decision: Mapped[Optional["AffordabilityDecision"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )


class AffordabilityDecision(Base):
    """The engine's verdict for a purchase request."""
    __tablename__ = "affordability_decisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    affordability_status: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_safe_to_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    recommended_payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    earliest_date_for_full_payment: Mapped[Optional["date"]] = mapped_column(Date, nullable=True)
    spending_changes_needed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    request: Mapped[PurchaseRequest] = relationship(back_populates="decision")
