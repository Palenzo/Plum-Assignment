"""Accuracy harness — run every provided test case through the engine and score.

Reports decision-match and approved-amount-match accuracy against
test_cases.json. Run: python eval.py
"""
from __future__ import annotations

import json
from pathlib import Path

from app.engine import adjudicate
from app.models import ClaimInput

CASES_PATH = Path(__file__).parents[1] / "test_cases.json"
if not CASES_PATH.exists():
    raise SystemExit(
        f"test_cases.json not found at {CASES_PATH}. It ships in the repo root; "
        "run this from a full checkout.")
CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))["test_cases"]


def run() -> int:
    decision_hits = 0
    amount_hits = 0
    amount_total = 0
    rows: list[tuple[str, str, str, bool, str]] = []

    for case in CASES:
        claim = ClaimInput.from_case(case["input_data"])
        result = adjudicate(claim, claim_id=case["case_id"])
        expected = case["expected_output"]

        decision_ok = result.decision == expected["decision"]
        decision_hits += decision_ok

        amount_mark = "-"
        if "approved_amount" in expected:
            amount_total += 1
            amount_ok = result.approved_amount == expected["approved_amount"]
            amount_hits += amount_ok
            amount_mark = "ok" if amount_ok else "MISS"

        rows.append((case["case_id"], expected["decision"], result.decision,
                     decision_ok, amount_mark))

    print(f"{'Case':7}{'Expected':16}{'Got':16}{'Decision':10}{'Amount'}")
    print("-" * 55)
    for cid, exp, got, decision_ok, amount_mark in rows:
        print(f"{cid:7}{exp:16}{got:16}{'ok' if decision_ok else 'MISS':10}{amount_mark}")

    n = len(CASES)
    print("-" * 55)
    print(f"Decision accuracy: {decision_hits}/{n} ({round(100 * decision_hits / n)}%)")
    if amount_total:
        print(f"Amount accuracy:   {amount_hits}/{amount_total} "
              f"({round(100 * amount_hits / amount_total)}%)")

    return 0 if decision_hits == n else 1


if __name__ == "__main__":
    raise SystemExit(run())
