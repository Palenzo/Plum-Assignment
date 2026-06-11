"""Plain-English, citation-backed explanation of a decision (RAG generation).

Retrieves the relevant policy clauses, then asks the LLM to explain the decision
grounded ONLY in those clauses, so it cites real policy text instead of guessing.
Fail-open: when the LLM is unavailable (no key, disabled, or rate-limited) it
returns the decision's own notes plus the retrieved clauses — still useful, and
still grounded in the actual policy.
"""
from __future__ import annotations

import os

from pydantic import BaseModel, Field, field_validator

from .config import settings
from .knowledge import retrieve
from .models import Decision

_INSTRUCTIONS = (
    "You explain an OPD insurance claim decision to the member in 2-3 plain, kind "
    "sentences. Ground every statement ONLY in the provided policy clauses — never "
    "invent a rule. Return the clauses you relied on as citations.")


class Explanation(BaseModel):
    summary: str
    citations: list[str] = Field(default_factory=list)

    @field_validator("citations", mode="before")
    @classmethod
    def _none_to_list(cls, value):
        return value or []


def _query(decision: Decision) -> str:
    parts = [decision.notes, " ".join(decision.rejection_reasons),
             " ".join(decision.flags), " ".join(decision.rejected_items)]
    return " ".join(p for p in parts if p) or decision.decision


def _fallback(decision: Decision, clauses: list[str]) -> Explanation:
    return Explanation(summary=decision.notes or "See the decision details above.", citations=clauses)


def explain_decision(decision: Decision, *, agent=None) -> Explanation:
    clauses = retrieve(_query(decision), k=4)
    if os.getenv("AI_EXPLAIN_ENABLED", "true").lower() != "true" or not settings()["groq_api_key"]:
        return _fallback(decision, clauses)
    try:
        agent = agent or _build_agent()
        prompt = (
            f"Decision: {decision.decision}. Notes: {decision.notes}\n"
            f"Reason codes: {', '.join(decision.rejection_reasons) or 'none'}\n\n"
            "Relevant policy clauses:\n" + "\n".join(f"- {c}" for c in clauses))
        result = agent.run(prompt).content
        if not isinstance(result, Explanation):
            return _fallback(decision, clauses)
        if not result.citations:
            result.citations = clauses
        return result
    except Exception:
        return _fallback(decision, clauses)


def _build_agent():
    cfg = settings()
    from agno.agent import Agent
    from agno.models.groq import Groq
    return Agent(model=Groq(id=cfg["groq_model"], api_key=cfg["groq_api_key"], temperature=0),
                 output_schema=Explanation, instructions=_INSTRUCTIONS)
