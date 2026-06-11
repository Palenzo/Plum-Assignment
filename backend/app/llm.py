"""LLM provider selection.

Builds the Agno chat model for the configured provider (OpenAI or Groq) so the
rest of the app — extraction, review, explanation — stays provider-agnostic.
Set LLM_PROVIDER=openai|groq, or just supply the matching API key and it is
auto-detected (OpenAI preferred when both are present).
"""
from __future__ import annotations

from .config import settings


def llm_available() -> bool:
    """True when the configured provider has an API key."""
    cfg = settings()
    key = "openai_api_key" if cfg["provider"] == "openai" else "groq_api_key"
    return bool(cfg[key])


def model_name() -> str:
    cfg = settings()
    return cfg["openai_model"] if cfg["provider"] == "openai" else cfg["groq_model"]


def build_model(temperature: float = 0.0):
    """Return an Agno chat model for the configured provider (at temperature 0
    by default, so extraction and review answer once, deterministically)."""
    cfg = settings()
    if cfg["provider"] == "openai":
        if not cfg["openai_api_key"]:
            raise RuntimeError("OPENAI_API_KEY is not set — add it to backend/.env")
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=cfg["openai_model"], api_key=cfg["openai_api_key"],
                          temperature=temperature)
    if not cfg["groq_api_key"]:
        raise RuntimeError("GROQ_API_KEY is not set — add it to backend/.env")
    from agno.models.groq import Groq
    return Groq(id=cfg["groq_model"], api_key=cfg["groq_api_key"], temperature=temperature)
