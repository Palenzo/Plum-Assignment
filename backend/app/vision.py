"""LLM vision fallback for OCR.

When Tesseract isn't installed (e.g. a non-Docker deploy), document images are
transcribed by a vision-capable LLM instead — OpenAI's gpt-4o family, or a Groq
Llama vision model. Both providers expose the same OpenAI-style chat API with an
``image_url`` content part, so one code path serves both. This only reads text;
the structured extraction and the rule engine are unchanged.
"""
from __future__ import annotations

import base64

from .config import settings

_PROMPT = (
    "Transcribe ALL text from this medical document — an Indian OPD prescription "
    "or bill — exactly as written, preserving line breaks and numbers. Return "
    "only the transcribed text, with no commentary or formatting."
)


def vision_available() -> bool:
    """True when the configured provider has both a key and a vision model."""
    cfg = settings()
    if cfg["provider"] == "openai":
        return bool(cfg["openai_api_key"] and cfg["openai_vision_model"])
    return bool(cfg["groq_api_key"] and cfg["groq_vision_model"])


def _data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def vision_ocr(data: bytes, mime: str = "image/png") -> str:
    """Transcribe an image's text with the configured provider's vision model."""
    cfg = settings()
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": _PROMPT},
            {"type": "image_url", "image_url": {"url": _data_url(data, mime)}},
        ],
    }]
    if cfg["provider"] == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=cfg["openai_api_key"])
        model = cfg["openai_vision_model"]
    else:
        from groq import Groq
        client = Groq(api_key=cfg["groq_api_key"])
        model = cfg["groq_vision_model"]
    resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
    return (resp.choices[0].message.content or "").strip()
