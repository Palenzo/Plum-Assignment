"""Cheap pre-extraction gates run on metadata only, before any LLM cost."""
from __future__ import annotations

from datetime import date

from app.gates import claim_signature, pre_extraction_gate

VALID = dict(member_id="EMP001", treatment_date=date(2024, 11, 1), claim_amount=1500)


def test_missing_prescription_is_rejected_before_extraction():
    decision = pre_extraction_gate(**VALID, document_types={"bill"})
    assert decision is not None
    assert decision.decision == "REJECTED"
    assert "MISSING_DOCUMENTS" in decision.rejection_reasons


def test_below_minimum_amount_is_rejected():
    decision = pre_extraction_gate(
        member_id="EMP001", treatment_date=date(2024, 11, 1), claim_amount=300,
        document_types={"prescription", "bill"})
    assert decision is not None
    assert "BELOW_MIN_AMOUNT" in decision.rejection_reasons


def test_duplicate_signature_is_rejected():
    seen = {claim_signature("EMP001", date(2024, 11, 1), 1500)}
    decision = pre_extraction_gate(
        **VALID, document_types={"prescription", "bill"}, seen_signatures=seen)
    assert decision is not None
    assert "DUPLICATE_CLAIM" in decision.rejection_reasons


def test_valid_submission_passes_through_to_extraction():
    decision = pre_extraction_gate(**VALID, document_types={"prescription", "bill"})
    assert decision is None
