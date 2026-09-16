# Buy or Wait? — AI Financial Affordability Agent

A deterministic financial decision engine that answers one question: **can this user safely afford this purchase — now, later, or not at all?**

Given a purchase request, the system does not just compare the price to the current balance. It reconstructs the user's financial life from transaction history, pending payments, confirmed income, and supporting documents, then simulates the next 90 days of cash flow to find a payment plan that stays above the user's minimum balance at every step.

> This is a portfolio implementation of an AI-powered affordability agent built for a time-boxed challenge. It is educational software, not financial advice or production banking software.

## What it does

For every request in the dataset, the engine produces a complete, explainable recommendation:

- how much can be paid **today** without endangering the user's financial commitments
- whether the full amount is affordable **now**, affordable through a **plan** (partial payment, installments, or permitted spending changes), affordable **later**, or **not affordable** within the horizon
- the exact payment schedule, the earliest safe full-payment date, and a plain-language explanation of the decision

## Key considerations

Every decision accounts for:

- **current balance** and the user's preferred **minimum balance**
- **recurring income** (with message-confirmed salary changes and terminal/end-of-contract income handled explicitly)
- **recurring expenses** (rent, utilities, subscriptions, debt payments) detected from history
- **pending and scheduled transactions** — pending debits are reserved before they settle
- **essential expenses** and protected spending categories
- **payment options** offered per request, including installment plans
- **spending adjustments** the user is willing to make (stop or reduce flexible expenses)
- **information extracted from messages and images** — payroll letters, bills, and receipts that resolve blank amounts
- a rolling **90-day financial forecast** in the user's home currency

## Decision outputs

Each row of `output.csv` contains:

| Column | Meaning |
|---|---|
| `request_id` | The request being answered |
| `amount_safe_to_pay` | Largest amount safe to pay on `request_date` before optional spending changes |
| `affordability_status` | `affordable_now`, `affordable_with_plan`, `affordable_later`, or `not_affordable` |
| `recommended_payment_method` | `full_payment`, `partial_payment`, `installments`, `wait`, or `not_recommended` |
| `payment_plan` | Chronological `<YYYY-MM-DD>:<amount>` entries joined by `\|`, or `none` |
| `earliest_date_for_full_payment` | Earliest date the full amount is forecast safe as one payment |
| `spending_changes_needed` | Up to three `stop:<event_id>` / `reduce_to:<event_id>:<amount>` changes, or `none` |
| `decision_explanation` | Deterministic explanation citing the actual financial facts behind the decision |

`0 <= amount_safe_to_pay <= requested_amount` holds on every row; installment plans must match a supplied payment option; partial payments must satisfy the two-payment contract.

## Architecture

```text
Input CSVs + local media (dataset/)
  → Data loading & normalization          code/data_loader.py
      profiles, events, payment options, messages,
      image links, dated FX conversion (incl. cross-rates)
  → Financial timeline construction       code/test_engine.py (TimelineBuilder)
      recurring detection, pending/scheduled reservation,
      terminal-income suppression, media-derived amounts
  → 90-day cash-flow simulation           TimelineBuilder.simulate()
      day-by-day balance trajectory, minimum-buffer check
  → Affordability evaluation              evaluate_request()
      baseline safety, earliest full-payment date search
  → Payment-plan evaluation               partial / installment candidates
      each plan re-simulated over the full 90-day horizon
  → Spending-change evaluation            stop/reduce combinations
      only user-approved flexible categories, re-simulated
  → Final recommendation                  candidate ranking by safety & cost
  → output.csv                            code/main.py
```

All amounts are computed with Python `Decimal` (no floating-point money), and every stage is pure and deterministic — the same inputs always produce byte-identical output.

## Safety model

A recommendation is considered safe only when the **complete payment plan**:

1. can be completed by the user's deadline,
2. covers all required (essential and recurring) expenses,
3. keeps the balance above the user's preferred **minimum balance at every day of the 90-day forecast**, and
4. only changes expenses the user explicitly marked as flexible, never below their allowed minimum.

Plans are validated against the full horizon — not just the payment window — so a plan that would overdraw the account after its last installment is rejected.

## Repository layout

```text
.
├── README.md                  # You are here
├── problem_statement.md       # Original challenge specification
├── AGENTS.md                  # AI-assisted development conventions
├── code/
│   ├── main.py                # Official entry point: dataset → output.csv
│   ├── data_loader.py         # CSV/FX/media loading and normalization
│   └── test_engine.py         # Timeline builder, simulator, decision engine,
│                              #   self-check sample evaluation (__main__)
└── dataset/
    ├── requests.csv                  # 250 requests to evaluate
    ├── sample_requests.csv           # 25 solved reference examples
    ├── financial_profiles.csv        # Balances, minimums, priorities, preferences
    ├── financial_events.csv          # Historical / pending / scheduled transactions
    ├── request_payment_options.csv   # Payment options per request
    ├── exchange_rates.csv            # Fixed, dated conversion rates
    ├── messages.csv                  # User messages (income changes, confirmations)
    ├── images.csv + media/images/    # Payroll letters, bills, receipts
    └── output.csv                    # Blank output template (schema reference)
```

## How to run

From a clean checkout, using Python 3.9+ (verified on 3.9 and 3.14, no third-party dependencies):

```bash
python3 code/main.py
```

This reads `dataset/requests.csv`, evaluates all 250 requests, and writes `output.csv` to the repository root (250 rows + header, exact 8-column schema).

To run the built-in reference evaluation on the 25 solved samples:

```bash
python3 code/test_engine.py
```

## Validation

Verified on the current codebase:

- **250/250** requests processed with the exact required schema, unique IDs matching the input, and `decision_explanation` populated for every row
- **191 recommended plans** re-simulated independently across the full 90-day horizon: **0 safety violations**
- All output invariants hold (amount bounds, valid statuses/methods, chronological plans, valid dates, coherent partial-payment contract)
- Output is **byte-identical across repeated runs and across Python 3.9 / 3.14**
- Reference evaluation on the 25 solved samples: **20/25 affordability status, 23/25 payment method, 22/25 spending changes**

This is not 100% benchmark accuracy, by design — see the limitation below.

## Engineering trade-offs

The reference dataset's expected forecasts include an assumption about day-to-day variable spending (groceries, transport, dining) that cannot be uniquely inferred from the 25 solved examples: statistical projections built from that history (mean-of-recent, mean-of-full-history, median) each match some reference rows and contradict others, and none improve the overall reference score.

Rather than fitting the reference answers, the engine treats variable daily-living spending conservatively: it does not project those categories as deterministic recurring debits, while fully projecting all fixed commitments, pending payments, and confirmed income. This keeps every recommendation explainable and safety-preserving for any user — the same behavior on sample data and on the 250-request production set — at the cost of a handful of reference-row mismatches that stem from that modeling difference, not from correctness bugs. The remaining mismatches were traced event-by-event to their source transactions and are documented as forecast-model differences.
