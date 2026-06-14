"""Orchestrates a claim: cheap gates -> rule engine -> persistence."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from . import repository
from .confidence import Evidence
from .engine import adjudicate
from .extraction import extract, to_claim_input
from .gates import claim_signature, pre_extraction_gate
from .models import ClaimInput, Decision
from .review import review_if_concerned


def _context(member_id: str, treatment_date: date, claim_amount: float) -> tuple[str, str]:
    claim_id = "CLM_" + uuid.uuid4().hex[:8].upper()
    return claim_id, claim_signature(member_id, treatment_date, claim_amount)


def adjudicate_and_store(db: Session, claim: ClaimInput) -> Decision:
    """JSON path: gate -> engine, on an already-structured claim."""
    claim_id, signature = _context(claim.member_id, claim.treatment_date, claim.claim_amount)

    document_types: set[str] = set()
    if claim.prescription is not None:
        document_types.add("prescription")
    if claim.bill:
        document_types.add("bill")

    decision = pre_extraction_gate(
        member_id=claim.member_id, treatment_date=claim.treatment_date,
        claim_amount=claim.claim_amount, document_types=document_types,
        seen_signatures=repository.signatures(db), claim_id=claim_id,
    ) or adjudicate(claim, claim_id=claim_id)

    decision = review_if_concerned(claim, decision)
    decision.claim_amount = claim.claim_amount
    repository.save(db, claim, decision, signature)
    return decision


def adjudicate_upload(db: Session, *, member_id: str, member_name: str,
                      treatment_date: date, claim_amount: float, doc_texts: dict[str, str],
                      member_join_date: date | None = None, hospital: str | None = None,
                      cashless_request: bool = False,
                      previous_claims_same_day: int = 0,
                      evidence: Evidence | None = None) -> Decision:
    """Upload path: gate on metadata (before OCR cost), then OCR -> extract -> engine."""
    claim_id, signature = _context(member_id, treatment_date, claim_amount)

    gate = pre_extraction_gate(
        member_id=member_id, treatment_date=treatment_date, claim_amount=claim_amount,
        document_types=set(doc_texts), seen_signatures=repository.signatures(db),
        claim_id=claim_id)
    if gate is not None:
        gate.claim_amount = claim_amount
        stub = ClaimInput(member_id=member_id, member_name=member_name,
                          treatment_date=treatment_date, claim_amount=claim_amount)
        repository.save(db, stub, gate, signature)
        return gate

    extracted = extract("\n\n".join(doc_texts.values()))
    claim = to_claim_input(
        extracted, member_id=member_id, member_name=member_name,
        treatment_date=treatment_date, claim_amount=claim_amount,
        member_join_date=member_join_date, hospital=hospital,
        cashless_request=cashless_request, previous_claims_same_day=previous_claims_same_day)
    decision = adjudicate(claim, claim_id=claim_id, evidence=evidence)
    decision = review_if_concerned(claim, decision)
    decision.claim_amount = claim_amount
    repository.save(db, claim, decision, signature)
    return decision
