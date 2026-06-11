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
    return {
        "provider": provider,
        "groq_api_key": os.getenv("GROQ_API_KEY", ""),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }
