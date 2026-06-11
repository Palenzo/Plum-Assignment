"""The durable adjudication workflow.

Orchestration only — every side effect lives in an activity, each with its own
retry policy, so an LLM hiccup or a transient DB error retries that step alone
instead of reprocessing the whole claim. The workflow itself is deterministic
(claim id via workflow.uuid4()).
"""
from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ..models import Decision
    from . import activities
    from .shared import WorkflowInput

_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))
_SHORT = {"start_to_close_timeout": timedelta(seconds=20), "retry_policy": _RETRY}


@workflow.defn
class AdjudicateClaimWorkflow:
    @workflow.run
    async def run(self, inp: WorkflowInput) -> Decision:
        claim_id = "CLM_" + workflow.uuid4().hex[:8].upper()

        if inp.needs_extraction:
            doc_types = list(inp.doc_texts.keys())
        else:
            doc_types = []
            if inp.claim.prescription is not None:
                doc_types.append("prescription")
            if inp.claim.bill:
                doc_types.append("bill")

        gate = await workflow.execute_activity(
            activities.gate_activity, args=[inp.claim, doc_types, claim_id], **_SHORT)
        if gate is not None:
            gate.claim_amount = inp.claim.claim_amount
            await workflow.execute_activity(
                activities.persist_activity, args=[inp.claim, gate], **_SHORT)
            return gate

        claim = inp.claim
        if inp.needs_extraction:
            claim = await workflow.execute_activity(
                activities.extract_activity, args=[inp.doc_texts, inp.claim],
                start_to_close_timeout=timedelta(seconds=90), retry_policy=_RETRY)

        decision = await workflow.execute_activity(
            activities.adjudicate_activity, args=[claim, claim_id], **_SHORT)
        decision.claim_amount = claim.claim_amount

        # AI review team — may escalate an approvable claim to a human.
        decision = await workflow.execute_activity(
            activities.review_activity, args=[claim, decision],
            start_to_close_timeout=timedelta(seconds=60), retry_policy=_RETRY)

        await workflow.execute_activity(
            activities.persist_activity, args=[claim, decision], **_SHORT)
        return decision
