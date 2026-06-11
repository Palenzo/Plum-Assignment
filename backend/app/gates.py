"""Cheap pre-extraction gates.

These run on submission metadata BEFORE any OCR or LLM call, so obvious
rejections cost zero tokens. Only checks that are safe without reading the
documents live here — per-claim limits and exclusions depend on extracted
content and stay in the rule engine.
"""
from __future__ import annotations

import hashlib
from datetime import date

from .models import Decision
from .policy import load_policy


def claim_signature(member_id: str, treatment_date: date, claim_amount: float) -> str:
    """Stable fingerprint used to detect duplicate resubmissions."""
    raw = f"{member_id}|{treatment_date}|{claim_amount}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _reject(claim_id: str, reason: str, notes: str) -> Decision:
    return Decision(claim_id=claim_id, decision="REJECTED", rejection_reasons=[reason],
                    notes=notes, confidence_score=1.0)


def pre_extraction_gate(*, member_id: str, treatment_date: date, claim_amount: float,
                        document_types: set[str], seen_signatures=frozenset(),
                        policy: dict | None = None, claim_id: str = "CLM_TEST") -> Decision | None:
    """Return a short-circuit rejection, or None to proceed to extraction."""
    policy = policy or load_policy()
    minimum = policy["claim_requirements"]["minimum_claim_amount"]

    if claim_signature(member_id, treatment_date, claim_amount) in seen_signatures:
        return _reject(claim_id, "DUPLICATE_CLAIM",
                       "A claim with identical details was already submitted.")
    if "prescription" not in document_types:
        return _reject(claim_id, "MISSING_DOCUMENTS",
                       "Prescription from registered doctor is required.")
    if claim_amount < minimum:
        return _reject(claim_id, "BELOW_MIN_AMOUNT",
                       f"Claim is below the minimum claimable amount of ₹{minimum}.")
    return None
