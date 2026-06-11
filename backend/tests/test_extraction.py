"""Extraction maps LLM output to the typed claim the engine adjudicates.

The LLM call itself is integration-tested live (needs a key); here we test the
pure mapping and that a mapped claim flows correctly into the engine.
"""
from __future__ import annotations

from datetime import date

from app.engine import adjudicate
from app.extraction import ExtractedDocument, LineItem, to_claim_input


def _fever_doc() -> ExtractedDocument:
    return ExtractedDocument(
        doctor_name="Dr. Sharma", doctor_reg="KA/45678/2015",
        diagnosis="Viral fever", medicines=["Paracetamol 650mg"],
        line_items=[LineItem(name="consultation_fee", amount=1000),
                    LineItem(name="diagnostic_tests", amount=500)])


def test_extracted_document_maps_to_claim_input():
    claim = to_claim_input(_fever_doc(), member_id="EMP001", member_name="Rajesh Kumar",
                           treatment_date=date(2024, 11, 1), claim_amount=1500)
    assert claim.prescription.doctor_reg == "KA/45678/2015"
    assert claim.prescription.diagnosis == "Viral fever"
    assert claim.bill == {"consultation_fee": 1000, "diagnostic_tests": 500}


def test_mapped_claim_adjudicates_through_the_engine():
    claim = to_claim_input(_fever_doc(), member_id="EMP001", member_name="Rajesh Kumar",
                           treatment_date=date(2024, 11, 1), claim_amount=1500)
    decision = adjudicate(claim)
    assert decision.decision == "APPROVED"
    assert decision.approved_amount == 1350
