"""Retrieval over the policy and adjudication rules — the "R" in RAG.

Chunks the policy (and the rules doc when present) into short, labelled clauses
and retrieves the most relevant ones for a query. Retrieval is lexical TF-IDF
cosine: no extra dependencies, fully deterministic, and testable without an LLM.
The interface (`retrieve`) is deliberately small so it can be swapped for dense
vector embeddings later without touching callers.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from .policy import load_policy

_RULES_PATH = Path(__file__).parents[2] / "adjudication_rules.md"
_TOKEN = re.compile(r"[a-z0-9]+")


def _clauses_from_policy(policy: dict) -> list[str]:
    cov = policy["coverage_details"]
    clauses = [
        f"Per-claim limit is rupees {cov['per_claim_limit']}.",
        f"Annual limit is rupees {cov['annual_limit']}.",
        f"Family floater limit is rupees {cov['family_floater_limit']}.",
        f"Minimum claim amount is rupees {policy['claim_requirements']['minimum_claim_amount']}.",
        f"Claims must be submitted within {policy['claim_requirements']['submission_timeline_days']} days.",
    ]
    for name, cat in cov.items():
        if isinstance(cat, dict) and "sub_limit" in cat:
            label = name.replace("_", " ")
            clauses.append(f"{label} is covered with a sub-limit of rupees {cat['sub_limit']}.")
            if cat.get("copay_percentage"):
                clauses.append(f"{label} has a co-payment of {cat['copay_percentage']} percent.")
            if cat.get("covered_tests"):
                clauses.append(f"Covered diagnostic tests: {', '.join(cat['covered_tests'])}.")
            if cat.get("procedures_covered"):
                clauses.append(f"{label} procedures covered: {', '.join(cat['procedures_covered'])}.")
    for exclusion in policy.get("exclusions", []):
        clauses.append(f"Exclusion: {exclusion} are excluded and not covered.")
    for ailment, days in policy["waiting_periods"].get("specific_ailments", {}).items():
        clauses.append(f"{ailment} has a waiting period of {days} days.")
    clauses.append(f"Network hospitals: {', '.join(policy['network_hospitals'])}.")
    return clauses


def _clauses_from_rules() -> list[str]:
    if not _RULES_PATH.exists():
        return []
    text = _RULES_PATH.read_text(encoding="utf-8")
    chunks = re.split(r"\n#{1,6} |\n\n", text)
    cleaned = [re.sub(r"\s+", " ", re.sub(r"[#`>*]", "", c)).strip() for c in chunks]
    return [c for c in cleaned if len(c) > 40]


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class _Retriever:
    def __init__(self, docs: list[str]):
        self.docs = docs
        self._tf = [Counter(_tokens(d)) for d in docs]
        df: Counter[str] = Counter()
        for counts in self._tf:
            df.update(counts.keys())
        n = max(len(docs), 1)
        self._idf = {term: math.log((n + 1) / (freq + 1)) + 1 for term, freq in df.items()}
        self._default_idf = math.log(n + 1) + 1

    def _weighted(self, counts: Counter[str]) -> dict[str, float]:
        return {t: f * self._idf.get(t, self._default_idf) for t, f in counts.items()}

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        q = self._weighted(Counter(_tokens(query)))
        scored = [(_cosine(q, self._weighted(tf)), doc) for doc, tf in zip(self.docs, self._tf)]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for score, doc in scored[:k] if score > 0]


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    shared = a.keys() & b.keys()
    numerator = sum(a[t] * b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return numerator / (norm_a * norm_b) if norm_a and norm_b else 0.0


def retrieve(query: str, k: int = 3) -> list[str]:
    """Return the k most relevant policy/rules clauses for the query."""
    docs = _clauses_from_policy(load_policy()) + _clauses_from_rules()
    return _Retriever(docs).retrieve(query, k)
