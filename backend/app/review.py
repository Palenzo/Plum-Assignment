"""AI review team — medical-necessity + fraud judgment, advisory only.

An Agno team of two specialist agents reads a claim and returns one structured
assessment. The advisory layer can only make the deterministic engine MORE
cautious: a genuine concern on an otherwise-approved claim is escalated to a
human (MANUAL_REVIEW). The team never approves, never overturns a rejection,
and never changes amounts — so the engine stays the auditable source of truth.
"""
from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .confidence import EvidenceSignals, score
from .llm import llm_available
from .models import ClaimInput, Decision

_NECESSITY = (
    "You assess medical necessity: does the diagnosis reasonably justify the "
    "treatment, procedures and medicines? Judge clinical appropriateness ONLY; "
    "ignore cost, fees and amounts. Set necessity_justified=false ONLY for a "
    "clear, serious mismatch where the treatment plainly does not fit the "
    "diagnosis. Routine and commonly co-prescribed care — supportive vitamins, "
    "standard first-line medicines, and the usual tests for the stated symptoms "
    "— IS justified. When in doubt, necessity_justified=true.")
_FRAUD = (
    "You flag clinical fraud and anomaly patterns: treatment inconsistent with "
    "the diagnosis, impossible combinations, clear signs of fabrication or "
    "misuse. Ignore cost and pricing — amounts and limits are checked elsewhere. "
    "Set fraud_concern=true ONLY for a clear, strong anomaly, NOT for routine "
    "clinical choices or speculative 'might be unnecessary' observations. When "
    "in doubt, fraud_concern=false.")
_LEADER = (
    "Combine the two reviews into one assessment about CLINICAL appropriateness "
    "and fraud only. NEVER flag a claim for cost, fees or amount — deterministic "
    "rules handle those. Rate severity: use 'high' ONLY when the concern is "
    "clear and serious enough that a human MUST review before any payout; minor, "
    "routine or speculative concerns are 'low'. Be conservative — when in doubt, "
    "raise no concern and set severity 'low'. Most ordinary claims have no "
    "concern at all.")

_ESCALATABLE = {"APPROVED", "PARTIAL"}


class ReviewAssessment(BaseModel):
    necessity_justified: bool
    necessity_reason: str = ""
    fraud_concern: bool = False
    fraud_flags: list[str] = Field(default_factory=list)
    # How serious the concern is. Only "high" pulls an otherwise-clean claim into
    # manual review; lower severities are advisory and never escalate — this is
    # what keeps routine claims auto-adjudicating.
    severity: Literal["low", "medium", "high"] = "low"
    overall_confidence: float = 0.8

    @field_validator("fraud_flags", mode="before")
    @classmethod
    def _none_to_list(cls, value):
        return value or []

    @field_validator("severity", mode="before")
    @classmethod
    def _norm_severity(cls, value):
        v = str(value or "low").strip().lower()
        return v if v in {"low", "medium", "high"} else "low"


def apply_review(decision: Decision, assessment: ReviewAssessment) -> Decision:
    """Escalate an approved claim to a human ONLY for a clear, high-severity
    concern. Lower-severity observations are advisory and leave the decision
    untouched, so routine claims keep auto-adjudicating."""
    concern = (not assessment.necessity_justified) or assessment.fraud_concern
    if decision.decision not in _ESCALATABLE or not concern or assessment.severity != "high":
        return decision

    flags = list(decision.flags)
    if not assessment.necessity_justified:
        flags.append("Medical necessity unclear")
    flags.extend(assessment.fraud_flags)
    if assessment.fraud_concern and not assessment.fraud_flags:
        flags.append("Possible fraud pattern")

    notes = decision.notes
    if assessment.necessity_reason:
        notes = f"{notes} AI review: {assessment.necessity_reason}".strip()

    # Confidence reflects the AI's own certainty that review is warranted (folded
    # in here for the first time), always below the manual-review ceiling.
    conf, factors = score(EvidenceSignals(
        decision="MANUAL_REVIEW", ai_confidence=assessment.overall_confidence, ai_concern=True))

    return decision.model_copy(update={
        "decision": "MANUAL_REVIEW",
        "flags": flags,
        "confidence_score": conf,
        "confidence_factors": factors,
        "notes": notes,
        "next_steps": "A claims officer will review the flagged concerns.",
    })


def _summary(claim: ClaimInput) -> str:
    presc = claim.prescription
    parts = [f"Diagnosis: {presc.diagnosis if presc else 'n/a'}"]
    if presc:
        if presc.treatment:
            parts.append(f"Treatment: {presc.treatment}")
        if presc.procedures:
            parts.append("Procedures: " + ", ".join(presc.procedures))
        if presc.medicines_prescribed:
            parts.append("Medicines: " + ", ".join(presc.medicines_prescribed))
        if presc.tests_prescribed:
            parts.append("Tests: " + ", ".join(presc.tests_prescribed))
    # Deliberately omit amounts — clinical judgment only; cost is the engine's job.
    return "\n".join(parts)


def _build_team():
    from agno.agent import Agent
    from agno.team import Team

    from .llm import build_model

    model = build_model(0)
    necessity = Agent(name="NecessityReviewer", model=model, instructions=_NECESSITY)
    fraud = Agent(name="FraudReviewer", model=model, instructions=_FRAUD)
    # The leader delegates to members via tools (text mode); a parser_model
    # then converts its synthesis into the schema. This keeps the structured
    # pass separate from tool use, which some providers (e.g. Groq) require.
    return Team(members=[necessity, fraud], model=model, parser_model=model,
                output_schema=ReviewAssessment, instructions=_LEADER)


def assess(claim: ClaimInput, *, team=None) -> ReviewAssessment:
    team = team or _build_team()
    result = team.run(f"Review this OPD claim:\n\n{_summary(claim)}").content
    if not isinstance(result, ReviewAssessment):
        raise RuntimeError(f"review team did not return structured data: {result!r}")
    return result


def review_if_concerned(claim: ClaimInput, decision: Decision) -> Decision:
    """Run the AI review on an approvable claim. Fail-open: never block a
    decision because the AI is unavailable or disabled."""
    if os.getenv("AI_REVIEW_ENABLED", "true").lower() != "true":
        return decision
    if decision.decision not in _ESCALATABLE or not llm_available():
        return decision
    try:
        return apply_review(decision, assess(claim))
    except Exception:
        return decision
