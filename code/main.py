"""Official entry point: evaluate every request and write root output.csv.

Usage (from the repository root):
    python3 code/main.py
"""
import csv
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from test_engine import evaluate_request

OUTPUT_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation",
]

# Repository root = parent of the code/ directory containing this file.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def format_output_value(value) -> str:
    """Render engine values as spec-compliant CSV strings (no Python reprs)."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def main() -> None:
    loader = DataLoader()
    requests = loader.load_requests("requests.csv")

    output_path = os.path.join(REPO_ROOT, "output.csv")
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for req in requests:
            result = evaluate_request(req, loader)
            row = {col: format_output_value(result.get(col, "")) for col in OUTPUT_COLUMNS}
            row["request_id"] = req["request_id"]
            writer.writerow(row)

    print(f"Wrote {len(requests)} predictions to {output_path}")


if __name__ == "__main__":
    main()
