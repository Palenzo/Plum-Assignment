"""Loads the insurance policy that the engine adjudicates against."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "data" / "policy_terms.json"


@lru_cache(maxsize=4)
def load_policy(path: str | None = None) -> dict:
    src = Path(path) if path else DEFAULT_PATH
    return json.loads(src.read_text(encoding="utf-8"))
