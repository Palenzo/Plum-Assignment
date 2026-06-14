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
from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from .vision import vision_available, vision_ocr


class OcrUnavailable(RuntimeError):
    """Raised when a document needs OCR but no OCR engine is available."""


@dataclass
class OcrStats:
    """How confidently the text was read — feeds the confidence model."""
    mean_conf: float | None = None   # 0..1 mean Tesseract word-confidence
    used_fallback: bool = False      # a vision LLM transcribed it (unverified)

    @staticmethod
    def combine(parts: list["OcrStats"]) -> "OcrStats":
        confs = [p.mean_conf for p in parts if p.mean_conf is not None]
        return OcrStats(mean_conf=sum(confs) / len(confs) if confs else None,
                        used_fallback=any(p.used_fallback for p in parts))


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


def _ocr_image_bytes(data: bytes, mime: str = "image/png") -> tuple[str, OcrStats]:
    """OCR raw image bytes via Tesseract (with word-confidence), falling back to
    an LLM vision model (whose read is unverifiable, so flagged)."""
    if tesseract_available():
        img = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(img)
        info = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confs = [float(c) for word, c in zip(info["text"], info["conf"])
                 if word.strip() and float(c) >= 0]
        mean = sum(confs) / len(confs) / 100.0 if confs else None
        return text, OcrStats(mean_conf=mean)
    if vision_available():
        return vision_ocr(data, mime), OcrStats(used_fallback=True)
    raise OcrUnavailable(
        "No OCR engine available: install Tesseract or configure an LLM vision model.")


def _mime_for(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")


def ocr_image_detailed(data: bytes, filename: str = "image.png") -> tuple[str, OcrStats]:
    return _ocr_image_bytes(data, _mime_for(filename))


def ocr_image(data: bytes, filename: str = "image.png") -> str:
    return ocr_image_detailed(data, filename)[0]


def ocr_pdf_detailed(data: bytes) -> tuple[str, OcrStats]:
    pages: list[str] = []
    parts: list[OcrStats] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text().strip()
            if text:  # native text layer — a perfect read, no OCR uncertainty
                parts.append(OcrStats(mean_conf=1.0))
            else:  # scanned page with no text layer — rasterise and OCR
                png = page.get_pixmap(dpi=200).tobytes("png")
                text, stats = _ocr_image_bytes(png, "image/png")
                parts.append(stats)
            pages.append(text)
    return "\n".join(pages), OcrStats.combine(parts)


def ocr_pdf(data: bytes) -> str:
    return ocr_pdf_detailed(data)[0]


def ocr_document_detailed(filename: str, data: bytes) -> tuple[str, OcrStats]:
    if filename.lower().endswith(".pdf"):
        return ocr_pdf_detailed(data)
    return ocr_image_detailed(data, filename)


def ocr_document(filename: str, data: bytes) -> str:
    return ocr_document_detailed(filename, data)[0]
