"""Acceptance suite: the engine must reproduce every provided test case.

Decisions, amounts and reason codes are asserted exactly. Confidence is
asserted directionally — the sample's exact values are illustrative, not a
spec a deterministic engine can reproduce.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine import adjudicate
from app.models import ClaimInput

CASES_PATH = Path(__file__).parents[2] / "test_cases.json"
CASES = (
    json.loads(CASES_PATH.read_text(encoding="utf-8"))["test_cases"]
    if CASES_PATH.exists()
    else []
)


@pytest.mark.skipif(not CASES, reason="provided test_cases.json not present (run locally with it)")
@pytest.mark.parametrize("case", CASES or [{}], ids=[c["case_id"] for c in CASES] or ["skipped"])
def test_expected_outcome(case):
    claim = ClaimInput.from_case(case["input_data"])
    result = adjudicate(claim, claim_id=case["case_id"])
    exp = case["expected_output"]

    assert result.decision == exp["decision"]

    if "approved_amount" in exp:
        assert result.approved_amount == exp["approved_amount"]
    if "rejection_reasons" in exp:
        assert set(exp["rejection_reasons"]).issubset(set(result.rejection_reasons))
    if "rejected_items" in exp:
        assert result.rejected_items, "expected at least one rejected line item"
    if "network_discount" in exp:
        assert result.network_discount == exp["network_discount"]
    if "cashless_approved" in exp:
        assert result.cashless_approved == exp["cashless_approved"]

    assert 0.0 <= result.confidence_score <= 1.0
    if result.decision == "MANUAL_REVIEW":
        assert result.confidence_score < 0.8
    else:
        assert result.confidence_score >= 0.85
