"""Document ingestion: turn uploaded images/PDFs into raw OCR text.

OCR is the cheap stage (CPU only, no tokens), so it runs after the metadata
gates but before the LLM extraction. Tesseract is the primary engine; when it
isn't installed, a vision-capable LLM transcribes the image instead. Text-based
PDFs need neither — their text layer is read directly. If a document genuinely
needs OCR and no engine is available, `OcrUnavailable` is raised so the API can
return a clean 503 rather than a 500.
"""
from __future__ import annotations

import io
import os
import shutil

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from .vision import vision_available, vision_ocr


class OcrUnavailable(RuntimeError):
    """Raised when a document needs OCR but no OCR engine is available."""


def _tesseract_cmd() -> str | None:
    cmd = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    if cmd:
        return cmd
    for path in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(path):
            return path
    return None


_CMD = _tesseract_cmd()
if _CMD:
    pytesseract.pytesseract.tesseract_cmd = _CMD


def tesseract_available() -> bool:
    return _CMD is not None


def ocr_available() -> bool:
    """True when *some* OCR engine — Tesseract or an LLM vision model — is usable."""
    return tesseract_available() or vision_available()


def _ocr_image_bytes(data: bytes, mime: str = "image/png") -> str:
    """OCR raw image bytes via Tesseract, falling back to an LLM vision model."""
    if tesseract_available():
        return pytesseract.image_to_string(Image.open(io.BytesIO(data)))
    if vision_available():
        return vision_ocr(data, mime)
    raise OcrUnavailable(
        "No OCR engine available: install Tesseract or configure an LLM vision model.")


def _mime_for(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")


def ocr_image(data: bytes, filename: str = "image.png") -> str:
    return _ocr_image_bytes(data, _mime_for(filename))


def ocr_pdf(data: bytes) -> str:
    pages: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text().strip()
            if not text:  # scanned page with no text layer — rasterise and OCR
                png = page.get_pixmap(dpi=200).tobytes("png")
                text = _ocr_image_bytes(png, "image/png")
            pages.append(text)
    return "\n".join(pages)


def ocr_document(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return ocr_pdf(data)
    return ocr_image(data, filename)
