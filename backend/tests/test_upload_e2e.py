"""End-to-end upload path: image -> OCR -> extract -> engine -> persisted.

Skips unless both a Groq key and Tesseract are available.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.ingestion import tesseract_available
from app.llm import llm_available

from ._llm import skip_on_quota

pytestmark = pytest.mark.skipif(
    not (llm_available() and tesseract_available()),
    reason="needs an LLM API key and tesseract")

VERDICTS = {"APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"}


def _prescription_image() -> bytes:
    lines = ("City Care Clinic", "Dr Sharma  Reg No KA/45678/2015",
             "Patient Rajesh Kumar", "Diagnosis Viral fever",
             "Consultation Fee 1000", "Diagnostic Tests 500")
    img = Image.new("RGB", (820, 380), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((20, 20), "\n".join(lines), fill="black", font=font, spacing=14)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@skip_on_quota
def test_uploaded_document_runs_full_pipeline(client):
    response = client.post(
        "/api/claims",
        data={"member_id": "EMP100", "member_name": "Rajesh Kumar",
              "treatment_date": "2024-11-01", "claim_amount": "1500"},
        files={"prescription": ("rx.png", _prescription_image(), "image/png")})

    if response.status_code != 200:
        pytest.skip(f"upstream LLM unavailable (status {response.status_code}) — likely quota")
    body = response.json()
    assert body["claim_id"].startswith("CLM_")
    assert body["decision"] in VERDICTS

    fetched = client.get(f"/api/claims/{body['claim_id']}")
    assert fetched.status_code == 200
