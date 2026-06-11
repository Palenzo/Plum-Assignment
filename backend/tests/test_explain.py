"""Citation-backed explanation. With AI_EXPLAIN_ENABLED=false (tests), it uses
the deterministic fallback — but RAG retrieval still grounds the citations."""
from __future__ import annotations

from app.explain import explain_decision
from app.models import Decision


def test_explanation_cites_real_policy_clauses():
    decision = Decision(
        claim_id="C1", decision="REJECTED", rejection_reasons=["SERVICE_NOT_COVERED"],
        notes="Weight loss treatments are excluded from coverage.")
    result = explain_decision(decision)
    assert result.summary
    assert result.citations
    assert any("weight loss" in c.lower() or "exclu" in c.lower() for c in result.citations)


def test_explanation_handles_an_approval():
    decision = Decision(claim_id="C2", decision="APPROVED", approved_amount=1350,
                        notes="Claim approved within policy limits.")
    result = explain_decision(decision)
    assert result.summary
