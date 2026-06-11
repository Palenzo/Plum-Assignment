"""Document extraction: OCR text -> structured fields via an Agno/Groq agent.

The agent only *reads*. It returns typed data; the rule engine alone decides.
Extraction runs at temperature 0 with a strict output schema so the model
answers once, correctly — no costly retries.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from .models import ClaimInput, Prescription

_INSTRUCTIONS = (
    "You read Indian OPD medical prescriptions and bills and return structured "
    "data. Never guess or invent values — use null when a field is absent. Put "
    "every billed charge into line_items with its name and numeric amount."
)


class LineItem(BaseModel):
    name: str
    amount: float


class ExtractedDocument(BaseModel):
    doctor_name: str | None = None
    doctor_reg: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)

    @field_validator("medicines", "procedures", "tests", "line_items", mode="before")
    @classmethod
    def _null_to_empty(cls, value):
        # Llama sometimes emits null instead of [] for absent lists.
        return value or []


def to_claim_input(doc: ExtractedDocument, *, member_id: str, member_name: str,
                   treatment_date: date, claim_amount: float,
                   member_join_date: date | None = None, hospital: str | None = None,
                   cashless_request: bool = False,
                   previous_claims_same_day: int = 0) -> ClaimInput:
    """Combine extracted document fields with submission metadata."""
    prescription = Prescription(
        doctor_name=doc.doctor_name, doctor_reg=doc.doctor_reg,
        diagnosis=doc.diagnosis, treatment=doc.treatment,
        medicines_prescribed=doc.medicines, procedures=doc.procedures,
        tests_prescribed=doc.tests)
    return ClaimInput(
        member_id=member_id, member_name=member_name, treatment_date=treatment_date,
        claim_amount=claim_amount, member_join_date=member_join_date, hospital=hospital,
        cashless_request=cashless_request, previous_claims_same_day=previous_claims_same_day,
        prescription=prescription, bill={item.name: item.amount for item in doc.line_items})


def _build_agent():
    from agno.agent import Agent
    from .llm import build_model
    return Agent(model=build_model(0), output_schema=ExtractedDocument,
                 instructions=_INSTRUCTIONS)


def extract(ocr_text: str, *, agent=None) -> ExtractedDocument:
    """Extract structured fields from a document's OCR text."""
    agent = agent or _build_agent()
    result = agent.run(f"Extract the fields from this document:\n\n{ocr_text}").content
    if not isinstance(result, ExtractedDocument):
        raise RuntimeError(f"extraction did not return structured data: {result!r}")
    return result
