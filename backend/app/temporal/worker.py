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
from .shared import TASK_QUEUE
from .workflow import AdjudicateClaimWorkflow

TEMPORAL_TARGET = os.getenv("TEMPORAL_TARGET", "localhost:7233")


async def main() -> None:
    client = await Client.connect(TEMPORAL_TARGET, data_converter=pydantic_data_converter)
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
