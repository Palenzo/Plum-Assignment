"""Document ingestion: turn uploaded images/PDFs into raw OCR text.

OCR is the cheap stage (CPU only, no tokens), so it runs after the metadata
gates but before the LLM extraction.
"""
from __future__ import annotations

import io
import os
import shutil

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


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


def ocr_image(data: bytes) -> str:
    return pytesseract.image_to_string(Image.open(io.BytesIO(data)))


def ocr_pdf(data: bytes) -> str:
    pages: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text().strip()
            if not text:  # scanned page with no text layer — rasterise and OCR
                png = page.get_pixmap(dpi=200).tobytes("png")
                text = pytesseract.image_to_string(Image.open(io.BytesIO(png)))
            pages.append(text)
    return "\n".join(pages)


def ocr_document(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return ocr_pdf(data)
    return ocr_image(data)
