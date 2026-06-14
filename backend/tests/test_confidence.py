"""The confidence model is a real measurement: monotonic in each evidence signal,
bounded, and explainable. These are property tests, not fixed-number assertions.
"""
from __future__ import annotations

from app.confidence import (
    LOW_CONFIDENCE_THRESHOLD,
    Evidence,
    EvidenceSignals,
    score,
)


def _approved(**kw) -> EvidenceSignals:
    return EvidenceSignals(decision="APPROVED", **kw)


def test_score_is_bounded_and_returns_factors():
    value, factors = score(_approved())
    assert 0.0 <= value <= 1.0
    assert factors  # always explains itself


def test_clean_approval_stays_in_the_contract_band():
    # No OCR, all fields present, comfortable margin -> high confidence.
    value, _ = score(_approved(amount_margin=0.7))
    assert value >= 0.85


def test_thinner_margin_lowers_confidence():
    wide, _ = score(_approved(amount_margin=0.7))
    thin, _ = score(_approved(amount_margin=0.02))
    assert thin < wide
    assert thin >= 0.85  # margin alone can't breach the clean floor


def test_blurrier_ocr_lowers_confidence_monotonically():
    clear, _ = score(_approved(evidence=Evidence(ocr_quality=0.97)))
    fuzzy, _ = score(_approved(evidence=Evidence(ocr_quality=0.60)))
    awful, _ = score(_approved(evidence=Evidence(ocr_quality=0.30)))
    assert clear > fuzzy > awful


def test_missing_fields_lower_confidence_with_count():
    none, _ = score(_approved(evidence=Evidence(ocr_quality=0.95)))
    one, _ = score(_approved(missing_fields=("diagnosis",), evidence=Evidence(ocr_quality=0.95)))
    two, _ = score(_approved(missing_fields=("diagnosis", "doctor registration"),
                             evidence=Evidence(ocr_quality=0.95)))
    assert none > one > two


def test_vision_fallback_is_flagged_as_unverified():
    value, factors = score(_approved(evidence=Evidence(ocr_fallback=True)))
    assert any("unverified" in f.label.lower() for f in factors)
    assert value < 0.95


def test_very_weak_evidence_drops_below_escalation_threshold():
    value, _ = score(_approved(
        amount_margin=0.05,
        missing_fields=("diagnosis", "doctor registration"),
        evidence=Evidence(ocr_quality=0.25)))
    assert value < LOW_CONFIDENCE_THRESHOLD


def test_hard_rule_rejection_is_near_certain_and_ignores_evidence():
    clean, _ = score(EvidenceSignals(decision="REJECTED", hard_rule=True))
    blurry, _ = score(EvidenceSignals(decision="REJECTED", hard_rule=True,
                                      evidence=Evidence(ocr_quality=0.2)))
    assert clean >= 0.95
    assert blurry == clean  # a categorical reject doesn't care about OCR


def test_manual_review_is_always_below_08():
    plain, _ = score(EvidenceSignals(decision="MANUAL_REVIEW"))
    confident_ai, _ = score(EvidenceSignals(decision="MANUAL_REVIEW", ai_confidence=0.95))
    assert plain < 0.8
    assert confident_ai < 0.8


def test_more_confident_ai_concern_raises_review_certainty():
    low, _ = score(EvidenceSignals(decision="MANUAL_REVIEW", ai_confidence=0.5))
    high, _ = score(EvidenceSignals(decision="MANUAL_REVIEW", ai_confidence=0.9))
    assert high > low
