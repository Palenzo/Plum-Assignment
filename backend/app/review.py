"""AI review team — medical-necessity + fraud judgment, advisory only.

An Agno team of two specialist agents reads a claim and returns one structured
assessment. The advisory layer can only make the deterministic engine MORE
cautious: a genuine concern on an otherwise-approved claim is escalated to a
human (MANUAL_REVIEW). The team never approves, never overturns a rejection,
and never changes amounts — so the engine stays the auditable source of truth.
"""
from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator

from .config import settings
from .models import ClaimInput, Decision

_NECESSITY = (
    "You assess medical necessity: does the diagnosis reasonably justify the "
    "treatment, procedures and medicines? Judge clinical appropriateness ONLY. "
    "Ignore cost, fees and amounts entirely. Flag only clear clinical mismatches.")
_FRAUD = (
    "You flag clinical fraud and anomaly patterns: treatment inconsistent with "
    "the diagnosis, implausible or impossible combinations, signs of misuse. "
    "Ignore cost and pricing — amounts and limits are checked elsewhere. Flag "
    "only clear concerns.")
_LEADER = (
    "Combine the two reviews into one assessment about CLINICAL appropriateness "
    "and fraud only. NEVER flag a claim for cost, fees or amount — those are "
    "checked separately by deterministic rules. Be conservative; when in doubt, "
    "do not flag.")

_ESCALATABLE = {"APPROVED", "PARTIAL"}


class ReviewAssessment(BaseModel):
    necessity_justified: bool
    necessity_reason: str = ""
    fraud_concern: bool = False
    fraud_flags: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.8

    @field_validator("fraud_flags", mode="before")
    @classmethod
    def _none_to_list(cls, value):
        return value or []


def apply_review(decision: Decision, assessment: ReviewAssessment) -> Decision:
    """Escalate an approved claim to a human when the team raises a concern."""
    concern = (not assessment.necessity_justified) or assessment.fraud_concern
    if decision.decision not in _ESCALATABLE or not concern:
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

    return decision.model_copy(update={
        "decision": "MANUAL_REVIEW",
        "flags": flags,
        "confidence_score": min(decision.confidence_score, 0.7),
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
    cfg = settings()
    if not cfg["groq_api_key"]:
        raise RuntimeError("GROQ_API_KEY is not set — add it to backend/.env")
    from agno.agent import Agent
    from agno.models.groq import Groq
    from agno.team import Team

    model = Groq(id=cfg["groq_model"], api_key=cfg["groq_api_key"], temperature=0)
    necessity = Agent(name="NecessityReviewer", model=model, instructions=_NECESSITY)
    fraud = Agent(name="FraudReviewer", model=model, instructions=_FRAUD)
    # The leader delegates to members via tools (text mode); a parser_model
    # then converts its synthesis into the schema — Groq forbids json-mode +
    # tools in a single call, so the structured pass must be separate.
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
    if decision.decision not in _ESCALATABLE or not settings()["groq_api_key"]:
        return decision
    try:
        return apply_review(decision, assess(claim))
    except Exception:
        return decision
