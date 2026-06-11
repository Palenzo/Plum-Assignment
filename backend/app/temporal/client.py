"""Client helper the API uses to run a claim through the durable workflow."""
from __future__ import annotations

import os
import uuid

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from ..models import Decision
from .shared import TASK_QUEUE, WorkflowInput
from .workflow import AdjudicateClaimWorkflow

TEMPORAL_TARGET = os.getenv("TEMPORAL_TARGET", "localhost:7233")

_client: Client | None = None


async def _get_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(TEMPORAL_TARGET, data_converter=pydantic_data_converter)
    return _client


async def run_workflow(payload: WorkflowInput) -> Decision:
    client = await _get_client()
    return await client.execute_workflow(
        AdjudicateClaimWorkflow.run,
        payload,
        id=f"claim-{uuid.uuid4().hex[:12]}",
        task_queue=TASK_QUEUE,
    )
