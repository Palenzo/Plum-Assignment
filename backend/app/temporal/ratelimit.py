"""Thread-safe token-bucket rate limiter for LLM calls.

Activities run in a worker thread pool; this caps how fast extraction calls
hit the provider, so a burst of claims can't blow the budget or trip 429s.
Combined with the worker's max_concurrent_activities, it gives real
backpressure: excess work waits instead of stampeding the API.
"""
from __future__ import annotations

import threading
import time


class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._rate)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                wait = (1 - self._tokens) / self._rate
            time.sleep(wait)


# Sustain ~2 extractions/sec with a burst of 5.
LLM_LIMITER = TokenBucket(rate=2.0, capacity=5.0)
