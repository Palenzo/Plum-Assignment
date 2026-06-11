"""Temporal activities — the only place I/O happens (DB, OCR-derived text, LLM).

Activities are sync `def`, so the worker runs them in a thread pool; that makes
blocking calls (SQLAlchemy, the Groq SDK) safe without touching the event loop.
Each returns a typed value the workflow passes straight to the next step.
"""
from __future__ import annotations

from temporalio import activity

from .. import repository
from ..db import SessionLocal
from ..engine import adjudicate
from ..extraction import extract, to_claim_input
from ..gates import claim_signature, pre_extraction_gate
from ..models import ClaimInput, Decision
from ..review import review_if_concerned
from .ratelimit import LLM_LIMITER


@activity.defn
def gate_activity(claim: ClaimInput, doc_types: list[str], claim_id: str) -> Decision | None:
    db = SessionLocal()
    try:
        seen = repository.signatures(db)
    finally:
        db.close()
    return pre_extraction_gate(
        member_id=claim.member_id, treatment_date=claim.treatment_date,
        claim_amount=claim.claim_amount, document_types=set(doc_types),
        seen_signatures=seen, claim_id=claim_id)


@activity.defn
def extract_activity(doc_texts: dict[str, str], metadata: ClaimInput) -> ClaimInput:
    LLM_LIMITER.acquire()  # rate-limit the LLM call
    extracted = extract("\n\n".join(doc_texts.values()))
    return to_claim_input(
        extracted, member_id=metadata.member_id, member_name=metadata.member_name,
        treatment_date=metadata.treatment_date, claim_amount=metadata.claim_amount,
        member_join_date=metadata.member_join_date, hospital=metadata.hospital,
        cashless_request=metadata.cashless_request,
        previous_claims_same_day=metadata.previous_claims_same_day)


@activity.defn
def adjudicate_activity(claim: ClaimInput, claim_id: str) -> Decision:
    return adjudicate(claim, claim_id=claim_id)


@activity.defn
def review_activity(claim: ClaimInput, decision: Decision) -> Decision:
    if decision.decision in ("APPROVED", "PARTIAL"):
        LLM_LIMITER.acquire()  # rate-limit the AI review team
    return review_if_concerned(claim, decision)


@activity.defn
def persist_activity(claim: ClaimInput, decision: Decision) -> None:
    db = SessionLocal()
    try:
        signature = claim_signature(claim.member_id, claim.treatment_date, claim.claim_amount)
        repository.save(db, claim, decision, signature)
    finally:
        db.close()
