"""Typed claim input and adjudication decision models."""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .confidence import ConfidenceFactor

Verdict = Literal["APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"]


class Prescription(BaseModel):
    doctor_name: str | None = None
    doctor_reg: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines_prescribed: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    tests_prescribed: list[str] = Field(default_factory=list)


class ClaimInput(BaseModel):
    member_id: str
    member_name: str
    treatment_date: date
    # A claim amount must be a real, positive, finite number. Rejecting
    # Infinity/NaN/negative at the boundary stops a non-finite float from
    # reaching the engine and being serialised back as bare `Infinity` (which
    # is invalid JSON and breaks strict clients / the durable workflow round-trip).
    claim_amount: float = Field(gt=0, allow_inf_nan=False)
    member_join_date: date | None = None
    submission_date: date | None = None
    hospital: str | None = None
    cashless_request: bool = False
    previous_claims_same_day: int = 0
    prescription: Prescription | None = None
    bill: dict[str, Any] = Field(default_factory=dict)

    @field_validator("bill")
    @classmethod
    def _bill_amounts_finite(cls, bill: dict) -> dict:
        # Same hazard as claim_amount: a numeric line item that is Infinity/NaN
        # would flow through the engine and serialise back as bare `Infinity`
        # (invalid JSON). Non-numeric values (e.g. test_names lists) are left
        # alone — the engine ignores them.
        for key, value in bill.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool) \
                    and not math.isfinite(value):
                raise ValueError(f"bill amount '{key}' must be a finite number")
        return bill

    @classmethod
    def from_case(cls, data: dict) -> "ClaimInput":
        """Build a claim from the test-case / API `input_data` shape."""
        docs = data.get("documents", {})
        presc = docs.get("prescription")
        return cls(
            member_id=data["member_id"],
            member_name=data["member_name"],
            treatment_date=data["treatment_date"],
            claim_amount=data["claim_amount"],
            member_join_date=data.get("member_join_date"),
            submission_date=data.get("submission_date"),
            hospital=data.get("hospital"),
            cashless_request=data.get("cashless_request", False),
            previous_claims_same_day=data.get("previous_claims_same_day", 0),
            prescription=Prescription(**presc) if presc else None,
            bill=docs.get("bill", {}),
        )


class AuditEntry(BaseModel):
    """One evaluated rule, in order — the explainability trail (star point B)."""
    step: str
    rule: str
    passed: bool
    detail: str = ""


class Decision(BaseModel):
    claim_id: str
    decision: Verdict
    claim_amount: float = 0.0
    approved_amount: float = 0.0
    rejection_reasons: list[str] = Field(default_factory=list)
    rejected_items: list[str] = Field(default_factory=list)
    deductions: dict[str, float] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
    network_discount: float | None = None
    cashless_approved: bool | None = None
    confidence_score: float = 1.0
    confidence_factors: list[ConfidenceFactor] = Field(default_factory=list)
    notes: str = ""
    next_steps: str = ""
    audit_trail: list[AuditEntry] = Field(default_factory=list)
