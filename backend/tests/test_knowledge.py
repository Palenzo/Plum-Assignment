"""Retrieval over policy clauses (the R in RAG). Deterministic — no LLM."""
from __future__ import annotations

from app.knowledge import retrieve


def test_retrieves_exclusion_for_weight_loss():
    hits = retrieve("obesity weight loss bariatric diet plan", k=4)
    assert any("weight loss" in h.lower() for h in hits)


def test_retrieves_waiting_period_for_diabetes():
    hits = retrieve("type 2 diabetes metformin", k=4)
    assert any("diabetes" in h.lower() for h in hits)


def test_retrieves_per_claim_limit_for_amount_query():
    hits = retrieve("per claim limit maximum amount", k=4)
    assert any("per-claim" in h.lower() or "per claim" in h.lower() for h in hits)
