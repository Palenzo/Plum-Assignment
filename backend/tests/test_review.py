"""The AI review layer is advisory: it can only make the engine MORE cautious.

A concern on an approved claim escalates to a human (MANUAL_REVIEW). It never
approves, never overturns a rejection, never changes amounts.
"""
from __future__ import annotations

from app.models import Decision
from app.review import ReviewAssessment, apply_review


def _approved() -> Decision:
    return Decision(claim_id="C1", decision="APPROVED", claim_amount=1500,
                    approved_amount=1350, confidence_score=0.93)


def test_high_severity_necessity_concern_escalates_to_manual_review():
    assessment = ReviewAssessment(necessity_justified=False,
                                  necessity_reason="Treatment unrelated to the diagnosis",
                                  severity="high")
    result = apply_review(_approved(), assessment)
    assert result.decision == "MANUAL_REVIEW"
    assert any("necessity" in f.lower() for f in result.flags)


def test_high_severity_fraud_concern_escalates_and_surfaces_flags():
    assessment = ReviewAssessment(necessity_justified=True, fraud_concern=True,
                                  fraud_flags=["Diagnosis does not match patient age"],
                                  severity="high")
    result = apply_review(_approved(), assessment)
    assert result.decision == "MANUAL_REVIEW"
    assert "Diagnosis does not match patient age" in result.flags


def test_low_severity_concern_does_not_escalate():
    # A speculative / routine concern is advisory only — the claim still approves.
    assessment = ReviewAssessment(necessity_justified=False, fraud_concern=True,
                                  fraud_flags=["Vitamin C may be unnecessary"],
                                  severity="low")
    result = apply_review(_approved(), assessment)
    assert result.decision == "APPROVED"
    assert result.approved_amount == 1350


def test_no_concern_leaves_the_decision_unchanged():
    assessment = ReviewAssessment(necessity_justified=True, fraud_concern=False)
    result = apply_review(_approved(), assessment)
    assert result.decision == "APPROVED"
    assert result.approved_amount == 1350


def test_ai_never_overturns_a_rejection():
    rejected = Decision(claim_id="C2", decision="REJECTED",
                        rejection_reasons=["PER_CLAIM_EXCEEDED"], confidence_score=0.98)
    assessment = ReviewAssessment(necessity_justified=False, fraud_concern=True,
                                  fraud_flags=["anything"], severity="high")
    result = apply_review(rejected, assessment)
    assert result.decision == "REJECTED"
