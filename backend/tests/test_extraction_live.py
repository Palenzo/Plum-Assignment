"""Live integration test for the Agno/Groq extraction agent.

Skips automatically when no GROQ_API_KEY is configured, so CI stays green
without a key. Run locally with backend/.env populated.
"""
from __future__ import annotations

import pytest

from app.extraction import extract
from app.llm import llm_available

from ._llm import skip_on_quota

pytestmark = pytest.mark.skipif(not llm_available(), reason="no LLM API key set")

MESSY_DOCUMENT = """
City Care Clinic, Bengaluru
Dr. Sharma, MBBS    Reg. No: KA/45678/2015
Date: 01/11/2024
Patient: Rajesh Kumar, 34 / M
Diagnosis: Viral fever
Rx:  Tab. Paracetamol 650mg  1-0-1 x 5 days
Investigations advised: CBC, Dengue test

------------- BILL -------------
Consultation Fee .......... 1000
Diagnostic Tests .......... 500
TOTAL ..................... 1500
"""


@skip_on_quota
def test_agent_extracts_structured_fields_from_messy_text():
    doc = extract(MESSY_DOCUMENT)

    assert doc.doctor_reg == "KA/45678/2015"
    assert "fever" in (doc.diagnosis or "").lower()
    amounts = {item.amount for item in doc.line_items}
    assert {1000.0, 500.0}.issubset(amounts)
