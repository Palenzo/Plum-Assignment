"""OCR ingestion: a generated image with known text must read back."""
from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.ingestion import ocr_image, tesseract_available

pytestmark = pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")


def _text_image(text: str) -> bytes:
    img = Image.new("RGB", (760, 240), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except OSError:
        font = ImageFont.load_default()
    draw.multiline_text((20, 20), text, fill="black", font=font, spacing=12)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_ocr_reads_known_text_from_image():
    text = ocr_image(_text_image("Reg No KA 45678 2015\nConsultation Fee 1000"))
    assert "45678" in text
    assert "1000" in text
