"""OCR engine selection: Tesseract → LLM vision → clean 503.

These run without Tesseract or a live LLM by stubbing the capability checks, so
they deterministically prove the fallback wiring and the graceful failure mode.
"""
from __future__ import annotations

import fitz  # PyMuPDF
import pytest

from app import ingestion
from app.ingestion import OcrUnavailable, ocr_available, ocr_document


def _text_pdf(text: str) -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_text_pdf_needs_no_ocr_engine(monkeypatch):
    """A PDF with a real text layer is read directly — no OCR engine required."""
    monkeypatch.setattr(ingestion, "tesseract_available", lambda: False)
    monkeypatch.setattr(ingestion, "vision_available", lambda: False)
    out = ocr_document("rx.pdf", _text_pdf("Consultation fee 1000"))
    assert "Consultation fee 1000" in out


def test_image_without_any_engine_raises(monkeypatch):
    monkeypatch.setattr(ingestion, "tesseract_available", lambda: False)
    monkeypatch.setattr(ingestion, "vision_available", lambda: False)
    with pytest.raises(OcrUnavailable):
        ocr_document("rx.png", b"\x89PNG-not-real")


def test_image_falls_back_to_vision(monkeypatch):
    """With no Tesseract but a vision model, images route to the LLM."""
    monkeypatch.setattr(ingestion, "tesseract_available", lambda: False)
    monkeypatch.setattr(ingestion, "vision_available", lambda: True)
    monkeypatch.setattr(ingestion, "vision_ocr",
                        lambda data, mime: "transcribed-by-llm")
    assert ocr_document("rx.jpg", b"fake-bytes") == "transcribed-by-llm"


def test_ocr_available_reflects_engines(monkeypatch):
    monkeypatch.setattr(ingestion, "tesseract_available", lambda: False)
    monkeypatch.setattr(ingestion, "vision_available", lambda: False)
    assert ocr_available() is False
    monkeypatch.setattr(ingestion, "vision_available", lambda: True)
    assert ocr_available() is True


def test_upload_returns_503_when_no_ocr(client, monkeypatch):
    monkeypatch.setattr(ingestion, "tesseract_available", lambda: False)
    monkeypatch.setattr(ingestion, "vision_available", lambda: False)
    resp = client.post(
        "/api/claims",
        data={"member_id": "EMP1", "member_name": "X",
              "treatment_date": "2024-11-01", "claim_amount": "1500"},
        files={"prescription": ("rx.png", b"\x89PNG-not-real", "image/png")})
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "OCR_UNAVAILABLE"
    assert "OCR" in body["error"]
