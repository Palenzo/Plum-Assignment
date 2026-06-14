"""Computed confidence — a real signal derived from evidence, not a constant.

The score answers: *how sure are we this decision is correct, given how clearly
the documents were read and how close the claim sits to a decisive threshold?*

Every adjustment is recorded as a named `ConfidenceFactor`, so the score is
explainable rather than a magic number. The model can only ever lower confidence
from a decision-type base; on the upload path, very weak evidence pushes an
otherwise-approvable claim below `LOW_CONFIDENCE_THRESHOLD`, which the engine
turns into a human review (per `adjudication_rules.md`: "<70% -> manual review").

Pure: no I/O, no policy, no LLM. The engine and review layer feed it signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

# adjudication_rules.md: "System confidence <70% -> manual review".
LOW_CONFIDENCE_THRESHOLD = 0.70

# Decision-type bases. Categorical rejections are near-certain; an approval is
# high but exposed to evidence penalties; a fraud/manual routing is low by design
# (it exists precisely because the system is unsure).
_BASE = {
    "APPROVED": 0.95,
    "PARTIAL": 0.93,
    "REJECTED": 0.97,
    "MANUAL_REVIEW": 0.62,
}

# Comfortable headroom under a binding limit. Above this, no margin penalty.
_MARGIN_COMFORT = 0.20
_MARGIN_MAX_PENALTY = 0.06   # bounded so a clean approval/partial stays >= 0.85
_MISSING_PER_FIELD = 0.03
_MISSING_MAX_PENALTY = 0.12
_FALLBACK_PENALTY = 0.08
_OCR_GOOD = 0.90            # OCR confidence at/above this is "clear"
_OCR_SLOPE = 0.30          # how hard low OCR confidence bites


class ConfidenceFactor(BaseModel):
    """One named reason the score is what it is (shown in the UI / audit)."""
    label: str
    detail: str = ""
    delta: float = 0.0   # signed contribution; negative lowered the score


class Evidence(BaseModel):
    """How well a claim's documents were read. None on the structured JSON path.

    A pydantic model so it serialises losslessly across the Temporal boundary.
    """
    ocr_quality: float | None = None   # 0..1 mean OCR word-confidence
    ocr_fallback: bool = False         # vision-LLM transcribed it (unverified)


@dataclass
class EvidenceSignals:
    decision: str
    hard_rule: bool = False                  # a categorical rule decided it
    amount_margin: float | None = None       # 0..1 relative headroom to the limit
    missing_fields: tuple[str, ...] = ()
    evidence: Evidence | None = None
    ai_confidence: float | None = None
    ai_concern: bool = False


def _margin_factor(margin: float | None, factors: list[ConfidenceFactor]) -> float:
    if margin is None:
        return 0.0
    m = max(0.0, min(1.0, margin))
    if m >= _MARGIN_COMFORT:
        factors.append(ConfidenceFactor(
            label="Comfortable margin",
            detail=f"{round(m * 100)}% headroom under the limit"))
        return 0.0
    penalty = -_MARGIN_MAX_PENALTY * (1 - m / _MARGIN_COMFORT)
    factors.append(ConfidenceFactor(
        label="Close to the limit",
        detail=f"only {round(m * 100)}% headroom under the limit",
        delta=round(penalty, 3)))
    return penalty


def _completeness_factor(missing: tuple[str, ...],
                         factors: list[ConfidenceFactor]) -> float:
    if not missing:
        factors.append(ConfidenceFactor(
            label="All key fields present",
            detail="diagnosis, doctor registration and bill all read"))
        return 0.0
    penalty = -min(_MISSING_MAX_PENALTY, _MISSING_PER_FIELD * len(missing))
    factors.append(ConfidenceFactor(
        label="Missing details",
        detail="not found: " + ", ".join(missing),
        delta=round(penalty, 3)))
    return penalty


def _ocr_factor(evidence: Evidence | None, factors: list[ConfidenceFactor]) -> float:
    if evidence is None:
        return 0.0  # structured input — nothing was OCR'd, so nothing to doubt
    if evidence.ocr_fallback:
        factors.append(ConfidenceFactor(
            label="Unverified read",
            detail="image transcribed by a vision model, not OCR",
            delta=-_FALLBACK_PENALTY))
        return -_FALLBACK_PENALTY
    if evidence.ocr_quality is None:
        return 0.0
    q = max(0.0, min(1.0, evidence.ocr_quality))
    if q >= _OCR_GOOD:
        factors.append(ConfidenceFactor(
            label="Document read clearly", detail=f"OCR confidence {round(q * 100)}%"))
        return 0.0
    penalty = -_OCR_SLOPE * (_OCR_GOOD - q)
    factors.append(ConfidenceFactor(
        label="Low-quality scan",
        detail=f"OCR confidence {round(q * 100)}%",
        delta=round(penalty, 3)))
    return penalty


def score(signals: EvidenceSignals) -> tuple[float, list[ConfidenceFactor]]:
    """Compute a confidence in [0, 1] plus the factors that produced it."""
    factors: list[ConfidenceFactor] = []
    value = _BASE.get(signals.decision, 0.90)

    if signals.decision == "MANUAL_REVIEW":
        # A more-confident AI concern is a stronger signal that review is the
        # right call — but a manual-review verdict is always < 0.8 by contract.
        if signals.ai_confidence is not None:
            value = min(0.78, 0.50 + 0.30 * max(0.0, min(1.0, signals.ai_confidence)))
            factors.append(ConfidenceFactor(
                label="Flagged for human review",
                detail=f"reviewer confidence {round(signals.ai_confidence * 100)}%"))
        else:
            factors.append(ConfidenceFactor(
                label="Routed to a human", detail="unusual pattern or weak evidence"))
        return round(max(0.0, min(0.79, value)), 2), factors

    # Categorical decisions (missing docs, exclusion, invalid reg, over-limit,
    # waiting period, pre-auth) are near-certain — no evidence penalties apply.
    if not signals.hard_rule and signals.decision in ("APPROVED", "PARTIAL"):
        value += _margin_factor(signals.amount_margin, factors)
        value += _completeness_factor(signals.missing_fields, factors)
        value += _ocr_factor(signals.evidence, factors)
    elif signals.hard_rule:
        factors.append(ConfidenceFactor(
            label="Clear-cut rule", detail="decided by a definite policy rule"))

    return round(max(0.0, min(1.0, value)), 2), factors
