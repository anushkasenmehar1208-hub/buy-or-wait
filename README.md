# Buy or Wait? — AI Financial Affordability Agent

A personal financial decision assistant. Instead of only checking your current balance, it
builds a **90-day cash-flow forecast** from your income, recurring expenses, commitments,
and pending payments — then tells you whether a purchase is safe **now**, achievable **with
a plan**, worth **waiting** for, or **not affordable**.

This repository contains two layers:

| Layer | Path | Description |
|---|---|---|
| **Web application** | `backend/`, `frontend/` | FastAPI + PostgreSQL + React product wrapping the engine |
| **Financial engine** | `code/` | The original deterministic decision engine (untouched, standalone) |

> **Disclaimer:** educational/portfolio project. Not financial advice, not production
> banking software.

---

## What it does

Ask one question — *"Can I afford this?"* — and get a decision backed by numbers:

- **Buy now** — paying today keeps your balance above your minimum for the next 90 days.
- **Affordable with plan** — partial payment / installments / temporary spending changes
  make it safe today.
- **Wait** — a specific future date on which the full payment becomes safe.
- **Not affordable** — no safe path within the forecast horizon.

Every decision ships with `amount_safe_to_pay`, a concrete payment plan, the earliest safe
full-payment date, spending changes (if any), and a plain-language explanation.

## Architecture

```
React (Vite + TS + Tailwind)
   │  fetch /api/*
   ▼
FastAPI (backend/app)
   ├── api/routes        HTTP endpoints (auth, profile, affordability)
   ├── schemas           Pydantic request/response contracts
   ├── services          business workflows (auth, profile, affordability)
   ├── repositories      SQLAlchemy data access, ownership-scoped
   ├── models            ORM entities (users → profiles → children → decisions)
   ├── auth              JWT bearer authentication
   └── finance/adapter   DB rows → engine-shaped dicts  ← the only bridge
   ▼
Financial engine (code/, imported unmodified)
   data_loader.py · test_engine.py
   TimelineBuilder → 90-day simulation → evaluate_request
   ▼
PostgreSQL (users, profiles, income, expenses, commitments, pending, requests, decisions)
```

**The engine is isolated.** `code/` has zero knowledge of FastAPI, SQLAlchemy, HTTP, or
auth. `backend/app/finance/adapter.py` is the single translation layer: it converts a
user's database profile into the exact `DataLoader`-compatible shapes the engine expects,
calls `evaluate_request()`, and maps the result back. The engine runs unchanged inside the
web app — verified by regression tests (below).

## Key engineering decisions

- **Deterministic core.** All money math uses Python `Decimal`; no LLM involvement in any
  calculation. AI features can be layered on later without touching decision logic.
- **Safety model.** A plan is recommended only if the *entire* payment schedule — across
  the full 90-day horizon, with the user's minimum balance enforced — stays safe. Spending
  changes and installment plans are simulated with the same strict horizon.
- **Ownership everywhere.** Every child record (income, expense, commitment, pending,
  request, decision) is queried through its owner's user id; cross-user access returns 404.
- **Migrations, not startup DDL.** Alembic owns the schema; the app never creates tables.
- **Secrets via environment.** `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS` — nothing
  hardcoded (see `.env.example`).

## Database design

```
users ──1:1── financial_profiles ──1:N── income_sources
                          │       ├─────1:N── recurring_expenses
                          │       ├─────1:N── financial_commitments
                          │       └─────1:N── pending_payments
                          └──1:N── purchase_requests ──1:1── affordability_decisions
```

All children cascade from their owner; money columns are `NUMERIC(18,2)`.

## How the engine works (high level)

1. **Load** the user's profile, income sources, recurring expenses, commitments, and
   pending payments (in the web app: from PostgreSQL via the adapter; standalone: from CSV).
2. **Build a daily timeline** for the next 90 days: scheduled credits/debits, pending
   reservations, one-off commitments.
3. **Simulate** every candidate: pay-in-full today, partial + later remainder, installment
   schedules, and (when the user opts in) stopping/reducing flexible expenses.
4. **Validate** each candidate across the full horizon — balance must never dip below the
   user's minimum.
5. **Rank** survivors (fewest changes, lowest cost, earliest completion) and explain.

## Running locally

Prerequisites: Python 3.9+, Node 18+, PostgreSQL 13+.

```bash
# 1. Database
createdb buyorwait
# (or: psql -c "CREATE DATABASE buyorwait;")

# 2. Backend
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env                      # then edit DATABASE_URL + SECRET_KEY
cd backend && ../.venv/bin/alembic upgrade head && cd ..
.venv/bin/python -m uvicorn app.main:app --reload --app-dir backend
# → http://localhost:8000  (docs at /docs)

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev
# → http://localhost:5173  (Vite dev server proxies nothing; set VITE_API_BASE_URL)
```

### Environment variables (`.env`, see `.env.example`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg2://user:pass@localhost/buyorwait` |
| `SECRET_KEY` | JWT signing key — generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Comma-separated allowed origins for the frontend |
| `VITE_API_BASE_URL` | Frontend → backend base URL (default `http://localhost:8000`) |

## Testing

```bash
# Backend (auth, authorization, ownership isolation, profile CRUD,
#          affordability flow, persistence, engine regression)
cd backend && ../.venv/bin/python -m pytest -v        # 37 tests

# Engine standalone (original CLI: 25-sample reference evaluation)
python3 code/test_engine.py
# → Status 20/25 · Method 23/25 · Changes 22/25
```

The regression suite (`backend/tests/test_engine_regression.py`) runs the engine's own
25-sample evaluation inside the backend venv and asserts the exact counts above, so any
accidental engine change or adapter breakage fails CI.

## Project structure

```
backend/
  alembic/            migrations (0001_initial: all 8 tables)
  app/
    api/routes/       auth · profile · affordability endpoints
    auth/             JWT dependency
    core/             config (env) · security (bcrypt+JWT) · errors
    db/               engine/session
    finance/          engine adapter (the only engine bridge)
    models/           SQLAlchemy entities
    repositories/     ownership-scoped queries
    schemas/          Pydantic contracts
    services/         auth · profile · affordability workflows
    tests/            37 pytest cases
    main.py           app factory, CORS, error handlers
frontend/
  src/
    app/              router · protected layout
    components/ui/    buttons, inputs, cards, badges, toasts, dialogs
    features/
      auth/           sign in/up, session context
      dashboard/      overview cards, recent decisions
      affordability/  "Can I afford it?" flow + forecast timeline
      financial-profile/  balance + income/expense/commitment/pending CRUD
      history/        decision list + detail
    services/         typed API client
    types/            API mirrors
code/                 untouched financial engine (+ dataset for its standalone CLI)
```

## Limitations

- Financial data is **user-entered** — there is no bank synchronization, payment
  processing, or credit scoring, and none is implied.
- The engine forecasts from declared recurring items; irregular spending is deliberately
  not projected as deterministic debits (documented engine decision).
- The reference-sample ceiling (20/25 status) reflects forecast behavior that cannot be
  uniquely inferred from the available examples; the implementation favors generic,
  explainable, safety-preserving logic over fitting those rows.
- Cross-currency requests use the engine's dataset FX table when available.

---

Built as a portfolio project: a verified deterministic financial engine, wrapped in a
production-shaped product — real auth, real database, real tests, clean separation.
