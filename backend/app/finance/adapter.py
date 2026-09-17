"""Engine adapter — bridges user-owned DB data to the untouched financial engine.

The engine (`code/test_engine.py`, `code/data_loader.py`) is imported as-is; nothing in
it knows about FastAPI, SQLAlchemy, or this application. The adapter synthesizes the
exact dict/attribute shapes the engine expects:

  profile:    {user_id, home_currency, current_available_balance, minimum_balance_to_keep,
               payment_methods_user_will_consider, max_installment_months,
               expense_categories_to_protect, expense_categories_user_is_willing_to_reduce,
               expense_categories_user_is_willing_to_stop}
  events:     {event_id, user_id, event_type, description, category, direction, amount,
               currency, event_date, settlement_date, status, linked_event_id,
               flexibility, minimum_allowed_amount}
  requests:   {request_id, user_id, request_date, request_type, requested_amount,
               desired_completion_date, allows_partial_payment, request_text}
  fx:         FXConverter-compatible object (same-currency = identity; engine's real
              FXConverter is reused for cross-currency via the dataset rates).

User income/expenses are emitted as *scheduled* events with a neutral "income" category
(engine treats category "salary" specially — doubling projection — so it is reserved for
engine-internal salary inference). Design decision: users' declared recurring income
IS their projected income; the engine's monthly-salary inference stays dormant.

All monetary values stay Decimal; dates stay `date`. No engine file is modified.
"""
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Engine import — points sys.path at <repo>/code so the untouched engine loads.
# ---------------------------------------------------------------------------
_CODE_DIR = Path(__file__).resolve().parents[3] / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))
REPO_ROOT = _CODE_DIR.parent

# The engine opens 'dataset/sample_requests.csv' relative to the CWD at import
# time only; temporarily chdir to the repo root for the import, then restore.
_prev_cwd = os.getcwd()
os.chdir(REPO_ROOT)
try:
    import data_loader as engine_data_loader  # noqa: E402  (engine modules, unmodified)
    import test_engine  # noqa: E402
finally:
    os.chdir(_prev_cwd)

evaluate_request = test_engine.evaluate_request
FXConverter = engine_data_loader.FXConverter

# We project repeating items slightly beyond the engine's 90-day window so every
# occurrence inside the window is guaranteed to exist.
PROJECTION_HORIZON_DAYS = 120

_VALID_METHODS = ("full_payment", "partial_payment", "installments")


def _d(v: Any) -> Decimal:
    return Decimal(str(v))


def _add_month(d: date, n: int) -> date:
    """Same-day next month; clamps to month end (Jan 31 → Feb 28)."""
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return date(year, month, min(d.day, last.day))


def _next_semi_monthly(d: date) -> date:
    """Next semimonthly occurrence: the 15th, else month end."""
    if d.day < 15:
        return d.replace(day=15)
    return _add_month(d.replace(day=1), 1) - timedelta(days=1)


def _iterate_occurrences(start: date, frequency: str, horizon: date,
                         end_date: Optional[date]) -> Iterable[date]:
    """Yield occurrence dates for a repeating item until horizon."""
    cur = start
    while cur <= horizon:
        if end_date and cur > end_date:
            return
        yield cur
        if frequency == "weekly":
            cur += timedelta(weeks=1)
        elif frequency == "biweekly":
            cur += timedelta(weeks=2)
        elif frequency == "semimonthly":
            cur = _next_semi_monthly(cur)
        else:  # monthly
            cur = _add_month(cur, 1)


class EngineFacade:
    """Per-evaluation DataLoader look-alike backed by one user's DB rows."""

    def __init__(self, profile_row, income_rows, expense_rows, commitment_rows, pending_rows):
        self.profile_row = profile_row
        self.income_rows = income_rows
        self.expense_rows = expense_rows
        self.commitment_rows = commitment_rows
        self.pending_rows = pending_rows

    # -- data_loader.DataLoader-compatible surface --------------------------
    @property
    def profiles(self) -> Dict[str, dict]:
        p = self.profile_row
        return {
            p.user_id: {
                "user_id": p.user_id,
                "home_currency": p.currency,
                "current_available_balance": _d(p.current_balance),
                "minimum_balance_to_keep": _d(p.minimum_safe_balance),
                "financial_priorities": [],
                "expense_categories_to_protect": [],
                "expense_categories_user_is_willing_to_reduce": [
                    c for c in (p.reducible_categories or []) if c
                ],
                "expense_categories_user_is_willing_to_stop": [
                    c for c in (p.stoppable_categories or []) if c
                ],
                "payment_methods_user_will_consider": [
                    m for m in (p.payment_methods or []) if m in _VALID_METHODS
                ] or ["full_payment", "partial_payment", "installments"],
                "max_installment_months": p.max_installment_months,
            }
        }

    @property
    def events_by_user(self) -> Dict[str, List[dict]]:
        uid = self.profile_row.user_id
        currency = self.profile_row.currency
        events: List[dict] = []
        today = date.today()
        horizon = today + timedelta(days=PROJECTION_HORIZON_DAYS)

        def add(d: date, amount: Decimal, direction: str, category: str, description: str,
                flexibility: str = "fixed", min_allowed: Optional[Decimal] = None) -> None:
            events.append({
                "event_id": f"db_{len(events) + 1}",
                "user_id": uid,
                "event_type": "recurring" if flexibility != "fixed" else "one_off",
                "description": description,
                "category": category,
                "direction": direction,
                "amount": amount,
                "currency": currency,
                "event_date": d,
                "settlement_date": d,
                "status": "scheduled" if d >= today else "pending",
                "linked_event_id": "",
                "flexibility": flexibility,
                "minimum_allowed_amount": min_allowed,
            })

        # Declared income → scheduled credits (category "income": engine's salary
        # inference is deliberately not triggered; user data is the source of truth).
        for inc in self.income_rows:
            for occ in _iterate_occurrences(inc.next_date, inc.frequency, horizon, inc.end_date):
                add(occ, _d(inc.amount), "credit", "income", inc.name or "Income")

        # Recurring expenses → scheduled debits. If the user marked a category
        # reducible and set a floor, mark reducible so the engine may propose it.
        stoppable = set(self.profile_row.stoppable_categories or [])
        reducible = set(self.profile_row.reducible_categories or [])
        for exp in self.expense_rows:
            flex, min_allowed = "fixed", None
            if exp.category in stoppable:
                flex = "reducible_or_stoppable" if exp.category in reducible else "stoppable"
                min_allowed = Decimal("0")
            elif exp.category in reducible and exp.minimum_allowed_amount is not None:
                flex = "reducible"
                min_allowed = exp.minimum_allowed_amount
            for occ in _iterate_occurrences(exp.next_date, exp.frequency, horizon, None):
                add(occ, _d(exp.amount), "debit", exp.category, exp.name or exp.category,
                    flexibility=flex, min_allowed=min_allowed)

        # One-off commitments → debits on their due date.
        for c in self.commitment_rows:
            if c.due_date <= horizon:
                add(c.due_date, _d(c.amount), "debit", "loan", c.name or "Commitment")

        # Pending payments → pending debits (engine reserves them from the balance).
        for p in self.pending_rows:
            if p.due_date <= horizon:
                add(p.due_date, _d(p.amount), "debit", "pending", p.name or "Pending payment")

        return {uid: events}

    @property
    def events_by_id(self) -> Dict[str, dict]:
        out: Dict[str, dict] = {}
        for evs in self.events_by_user.values():
            for ev in evs:
                out[ev["event_id"]] = ev
        return out

    @property
    def payment_options_by_request(self) -> Dict[str, List[dict]]:
        return {}

    @property
    def messages_by_user(self) -> Dict[str, List[dict]]:
        return {self.profile_row.user_id: []}

    @property
    def messages_by_request(self) -> Dict[str, List[dict]]:
        return {}

    @property
    def images_by_event(self) -> Dict[str, str]:
        return {}

    @property
    def fx(self):
        return FXConverter(REPO_ROOT / "dataset" / "exchange_rates.csv")


def compute_safe_to_spend(profile_row, income_rows, expense_rows, commitment_rows,
                          pending_rows) -> Decimal:
    """Largest amount safely payable today: the minimum projected buffer over the
    engine's 90-day no-purchase forecast, floored at 0. Uses the engine's own
    TimelineBuilder.simulate() — the same primitive evaluate_request relies on."""
    facade = EngineFacade(profile_row, income_rows, expense_rows, commitment_rows, pending_rows)
    uid = profile_row.user_id
    builder = test_engine.TimelineBuilder(uid, "dashboard", date.today(), facade)
    _safe, min_buf, _min_bal = builder.simulate()
    return max(Decimal("0"), min_buf)


def run_affordability(profile_row, income_rows, expense_rows, commitment_rows, pending_rows,
                      request_id: str, amount: Decimal, currency: str,
                      deadline: Optional[date],
                      request_date: Optional[date] = None,
                      allows_partial: Optional[bool] = None) -> dict:
    """Evaluate one purchase request through the untouched engine and return its dict."""
    facade = EngineFacade(profile_row, income_rows, expense_rows, commitment_rows, pending_rows)
    uid = profile_row.user_id
    rdate = request_date or date.today()
    currency = (currency or profile_row.currency).upper()

    req = {
        "request_id": request_id,
        "user_id": uid,
        "request_date": rdate,
        "request_type": "purchase",
        "requested_amount": _d(amount),
        # No user-supplied deadline → due at the end of the 90-day horizon.
        "desired_completion_date": deadline or (rdate + timedelta(days=90)),
        "allows_partial_payment": (
            profile_row.allows_partial_payment if allows_partial is None else allows_partial
        ),
        "request_text": "",
    }
    return evaluate_request(req, facade)
