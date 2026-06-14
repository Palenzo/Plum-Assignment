"""Environment-backed settings: LLM provider + keys/models, loaded from backend/.env."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")


@lru_cache(maxsize=1)
def settings() -> dict:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider:
        # Auto-detect: prefer OpenAI when its key is present, otherwise Groq.
        provider = "openai" if os.getenv("OPENAI_API_KEY") else "groq"
    app_env = os.getenv("APP_ENV", "production").strip().lower()
    log_level = (os.getenv("LOG_LEVEL", "").strip().upper()
                 or ("DEBUG" if app_env == "development" else "INFO"))
    return {
        "provider": provider,
        # Dev/prod toggle + resolved log level (LOG_LEVEL overrides the default).
        "app_env": app_env,
        "log_level": log_level,
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        # Vision-capable models for the OCR fallback (used when Tesseract is
        # absent). OpenAI's gpt-4o family can read images, so it defaults to the
        # main model; Groq's default Llama is text-only, so it falls back to a
        # Llama vision model. Override with OPENAI_VISION_MODEL / GROQ_VISION_MODEL.
        "openai_vision_model": os.getenv("OPENAI_VISION_MODEL")
        or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "groq_vision_model": os.getenv(
            "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
    }
