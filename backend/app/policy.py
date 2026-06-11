"""Loads (and saves) the insurance policy that the engine adjudicates against."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(os.getenv("POLICY_PATH") or (Path(__file__).parent / "data" / "policy_terms.json"))


@lru_cache(maxsize=4)
def load_policy(path: str | None = None) -> dict:
    src = Path(path) if path else DEFAULT_PATH
    return json.loads(src.read_text(encoding="utf-8"))


def save_policy(data: dict) -> dict:
    """Persist an edited policy and invalidate the cache (used by the admin UI)."""
    DEFAULT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    load_policy.cache_clear()
    return data
