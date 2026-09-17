"""Engine regression — proves the untouched engine still produces its verified output.

Run the engine's own 25-sample reference evaluation via its public module surface and
assert the accepted metrics (status 20/25, method 23/25, changes 22/25). If the engine
files are modified or the adapter broke imports, these tests fail.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "code"))

import test_engine  # noqa: E402


@pytest.fixture(scope="module")
def engine_results():
    results = {}
    for req in test_engine.samples:
        results[req["request_id"]] = test_engine.evaluate_request(req, test_engine.loader)
    return results


def test_engine_sample_status_count(engine_results):
    expected = test_engine.expected
    matches = sum(
        1 for rid, res in engine_results.items()
        if res["affordability_status"] == expected[rid]["affordability_status"]
    )
    assert matches == 20, f"status matches regressed: {matches}/20"


def test_engine_sample_method_count(engine_results):
    expected = test_engine.expected
    matches = sum(
        1 for rid, res in engine_results.items()
        if res["recommended_payment_method"] == expected[rid]["recommended_payment_method"]
    )
    assert matches == 23, f"method matches regressed: {matches}/23"


def test_engine_sample_changes_count(engine_results):
    expected = test_engine.expected
    matches = sum(
        1 for rid, res in engine_results.items()
        if res["spending_changes_needed"] == expected[rid]["spending_changes_needed"]
    )
    assert matches == 22, f"changes matches regressed: {matches}/22"


def test_engine_result_shape(engine_results):
    for rid, res in engine_results.items():
        assert set(res.keys()) == {
            "amount_safe_to_pay", "affordability_status", "recommended_payment_method",
            "payment_plan", "earliest_date_for_full_payment", "spending_changes_needed",
            "decision_explanation",
        }
        assert res["decision_explanation"], rid
