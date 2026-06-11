"""Runs the Temporal worker: hosts the workflow and activities.

Start with: python -m app.temporal.worker  (needs a Temporal server reachable).
max_concurrent_activities caps in-flight work — the queue backpressure that,
together with the token-bucket limiter, prevents LLM overuse.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import os

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from . import activities
from ..db import init_db
from .shared import TASK_QUEUE
from .workflow import AdjudicateClaimWorkflow

TEMPORAL_TARGET = os.getenv("TEMPORAL_TARGET", "localhost:7233")


async def _connect() -> Client:
    """Wait for the Temporal server to be ready (it boots after this process)."""
    last_error: Exception | None = None
    for attempt in range(30):
        try:
            return await Client.connect(TEMPORAL_TARGET, data_converter=pydantic_data_converter)
        except RuntimeError as exc:
            last_error = exc
            print(f"Temporal not ready (attempt {attempt + 1}/30); retrying in 2s…")
            await asyncio.sleep(2)
    raise RuntimeError(f"could not reach Temporal at {TEMPORAL_TARGET}: {last_error}")


async def main() -> None:
    init_db()  # ensure the claims tables exist (the worker persists decisions)
    client = await _connect()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[AdjudicateClaimWorkflow],
            activities=[
                activities.gate_activity,
                activities.extract_activity,
                activities.adjudicate_activity,
                activities.review_activity,
                activities.persist_activity,
            ],
            activity_executor=executor,
            max_concurrent_activities=4,
        )
        print(f"Worker listening on task queue '{TASK_QUEUE}' ({TEMPORAL_TARGET})")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
