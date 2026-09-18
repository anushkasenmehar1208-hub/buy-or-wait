"""Typed API contract — request/response models. Never expose ORM objects directly."""
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import AffordabilityDecision, FinancialProfile, PurchaseRequest

Currency = str  # ISO-4217 3-letter code


def _norm_currency(v: str) -> str:
    v = v.strip().upper()
    if len(v) != 3 or not v.isalpha():
        raise ValueError("currency must be a 3-letter ISO code")
    return v


# ---------------------------------------------------------------- auth
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("password must contain a digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("password must contain a letter")
        return v


class SigninRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    # Client appends ?v=<avatar_updated_at> to cache-bust; null → show initials.
    avatar_url: Optional[str] = None
    avatar_updated_at: Optional[datetime] = None


class UpdateProfileRequest(BaseModel):
    """Account settings: display name. Email is intentionally immutable here."""
    full_name: str = Field(min_length=1, max_length=120)

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v


# ---------------------------------------------------------------- profile
class ProfileUpsert(BaseModel):
    currency: Currency
    current_balance: Decimal = Field(ge=0, decimal_places=2)
    minimum_safe_balance: Decimal = Field(ge=0, decimal_places=2)
    allows_partial_payment: bool = True
    max_installment_months: Optional[int] = Field(default=None, ge=1, le=60)

    _norm_currency = field_validator("currency")(_norm_currency)

    @model_validator(mode="after")
    def min_le_balance(self):
        if self.minimum_safe_balance > self.current_balance:
            raise ValueError("minimum_safe_balance cannot exceed current_balance")
        return self


class IncomeUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, decimal_places=2)
    frequency: str  # weekly | biweekly | semimonthly | monthly
    next_date: date_type
    end_date: Optional[date_type] = None

    @field_validator("frequency")
    @classmethod
    def valid_frequency(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("weekly", "biweekly", "semimonthly", "monthly"):
            raise ValueError("frequency must be one of: weekly, biweekly, semimonthly, monthly")
        return v

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.end_date and self.end_date < self.next_date:
            raise ValueError("end_date must be on or after next_date")
        return self


class IncomeResponse(IncomeUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: str


class ExpenseUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = "other"  # rent|utilities|insurance|loan|subscription|groceries|other
    amount: Decimal = Field(gt=0, decimal_places=2)
    frequency: str
    next_date: date_type
    minimum_allowed_amount: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    essential: bool = True

    @field_validator("frequency")
    @classmethod
    def valid_frequency(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("weekly", "biweekly", "semimonthly", "monthly"):
            raise ValueError("frequency must be one of: weekly, biweekly, semimonthly, monthly")
        return v

    @field_validator("category")
    @classmethod
    def valid_category(cls, v: str) -> str:
        v = v.strip().lower()
        allowed = {"rent", "utilities", "insurance", "loan", "subscription", "groceries", "other"}
        if v not in allowed:
            raise ValueError(f"category must be one of: {', '.join(sorted(allowed))}")
        return v

    @model_validator(mode="after")
    def minimum_le_amount(self):
        if self.minimum_allowed_amount is not None and self.minimum_allowed_amount > self.amount:
            raise ValueError("minimum_allowed_amount cannot exceed amount")
        return self


class ExpenseResponse(ExpenseUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: str


class CommitmentUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, decimal_places=2)
    due_date: date_type
    is_installment: bool = False
    installment_total: int = Field(default=1, ge=1, le=120)

    @model_validator(mode="after")
    def installment_fields(self):
        if not self.is_installment and self.installment_total != 1:
            raise ValueError("installment_total only applies when is_installment is true")
        return self


class CommitmentResponse(CommitmentUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: str


class PendingUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, decimal_places=2)
    due_date: date_type


class PendingResponse(PendingUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: str


class ProfileResponse(ProfileUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    has_income: bool = False
    has_expenses: bool = False
    income: List[IncomeResponse] = Field(default_factory=list)
    expenses: List[ExpenseResponse] = Field(default_factory=list)
    commitments: List[CommitmentResponse] = Field(default_factory=list)
    pending: List[PendingResponse] = Field(default_factory=list)

    @classmethod
    def from_profile(cls, profile: FinancialProfile) -> "ProfileResponse":
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            currency=profile.currency,
            current_balance=profile.current_balance,
            minimum_safe_balance=profile.minimum_safe_balance,
            allows_partial_payment=profile.allows_partial_payment,
            max_installment_months=profile.max_installment_months,
            has_income=bool(profile.income_sources),
            has_expenses=bool(profile.recurring_expenses or profile.commitments),
            income=[IncomeResponse.model_validate(i) for i in profile.income_sources],
            expenses=[ExpenseResponse.model_validate(e) for e in profile.recurring_expenses],
            commitments=[CommitmentResponse.model_validate(c) for c in profile.commitments],
            pending=[PendingResponse.model_validate(p) for p in profile.pending_payments],
        )


# ---------------------------------------------------------------- affordability
class AffordabilityRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: Optional[Currency] = None  # defaults to profile currency
    deadline: Optional[date_type] = None

    _norm_currency = field_validator("currency")(_norm_currency)


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    affordability_status: str
    amount_safe_to_pay: Decimal
    recommended_payment_method: str
    payment_plan: Optional[str]
    earliest_date_for_full_payment: Optional[date_type]
    spending_changes_needed: Optional[str]
    decision_explanation: str
    created_at: datetime


class PurchaseRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_name: str
    amount: Decimal
    currency: str
    deadline: Optional[date_type]
    created_at: datetime
    decision: Optional[DecisionResponse] = None


class DecisionListResponse(BaseModel):
    items: List[PurchaseRequestResponse]
    total: int


def to_decision_response(decision: AffordabilityDecision) -> DecisionResponse:
    return DecisionResponse.model_validate(decision)


def to_request_response(req: PurchaseRequest) -> PurchaseRequestResponse:
    return PurchaseRequestResponse(
        id=req.id,
        item_name=req.item_name,
        amount=req.amount,
        currency=req.currency,
        deadline=req.deadline,
        created_at=req.created_at,
        decision=DecisionResponse.model_validate(req.decision) if req.decision else None,
    )
