"""Helper for live LLM tests: treat provider rate-limits/quota as a skip,
not a failure. An external API being throttled is an environment condition."""
from __future__ import annotations

import functools

import pytest


def skip_on_quota(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - inspect message, re-raise if unrelated
            msg = str(exc).lower()
            if any(k in msg for k in ("rate_limit", "rate limit", "429", "quota")):
                pytest.skip("LLM provider rate limit / quota reached")
            raise
    return wrapper
