"""Typed inputs shared between the Temporal client, workflow, and activities.

Using a Pydantic model here (with the pydantic data converter on both ends)
guarantees the claim payload serialises losslessly across every boundary —
dates, nested prescription, bill line items and all.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import ClaimInput

TASK_QUEUE = "opd-adjudication"


class WorkflowInput(BaseModel):
    claim: ClaimInput                       # metadata always; full claim on the JSON path
    doc_texts: dict[str, str] = Field(default_factory=dict)  # OCR text per document (upload path)
    needs_extraction: bool = False          # True => run the LLM extraction step
