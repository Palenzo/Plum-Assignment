"""FastAPI surface for claim submission and status."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import repository
from .config import settings
from .db import get_db, init_db
from .explain import Explanation, explain_decision
from .ingestion import ocr_document, tesseract_available
from .models import ClaimInput, Decision
from .policy import load_policy, save_policy
from .service import adjudicate_and_store, adjudicate_upload
from .temporal.client import run_workflow
from .temporal.shared import WorkflowInput

TEMPORAL_ENABLED = os.getenv("TEMPORAL_ENABLED", "true").lower() == "true"


async def _orchestrate(db: Session, claim: ClaimInput, doc_texts: dict[str, str],
                       needs_extraction: bool) -> Decision:
    """Run the claim through the durable workflow, falling back in-process."""
    if TEMPORAL_ENABLED:
        try:
            return await run_workflow(
                WorkflowInput(claim=claim, doc_texts=doc_texts, needs_extraction=needs_extraction))
        except Exception as exc:  # Temporal unreachable — keep the app working
            print(f"[temporal] unavailable, running in-process: {exc}")
    if needs_extraction:
        return adjudicate_upload(
            db, member_id=claim.member_id, member_name=claim.member_name,
            treatment_date=claim.treatment_date, claim_amount=claim.claim_amount,
            doc_texts=doc_texts, member_join_date=claim.member_join_date, hospital=claim.hospital,
            cashless_request=claim.cashless_request,
            previous_claims_same_day=claim.previous_claims_same_day)
    return adjudicate_and_store(db, claim)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OPD Claim Adjudication", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict:
    """Live status — which capabilities are currently available."""
    return {
        "status": "ok",
        "ai_available": bool(settings()["groq_api_key"]),
        "ocr_available": tesseract_available(),
        "temporal_enabled": TEMPORAL_ENABLED,
        "model": settings()["groq_model"],
    }


@app.post("/api/claims/json", response_model=Decision)
async def submit_claim(payload: ClaimInput, db: Session = Depends(get_db)) -> Decision:
    return await _orchestrate(db, payload, {}, needs_extraction=False)


@app.post("/api/claims", response_model=Decision)
async def submit_documents(
    member_id: str = Form(...),
    member_name: str = Form(...),
    treatment_date: date = Form(...),
    claim_amount: float = Form(...),
    member_join_date: date | None = Form(None),
    hospital: str | None = Form(None),
    cashless_request: bool = Form(False),
    previous_claims_same_day: int = Form(0),
    prescription: UploadFile | None = File(None),
    bill: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> Decision:
    doc_texts: dict[str, str] = {}
    for label, upload in (("prescription", prescription), ("bill", bill)):
        if upload is not None:
            doc_texts[label] = ocr_document(upload.filename, await upload.read())
    metadata = ClaimInput(
        member_id=member_id, member_name=member_name, treatment_date=treatment_date,
        claim_amount=claim_amount, member_join_date=member_join_date, hospital=hospital,
        cashless_request=cashless_request, previous_claims_same_day=previous_claims_same_day)
    return await _orchestrate(db, metadata, doc_texts, needs_extraction=True)


@app.get("/api/claims/{claim_id}", response_model=Decision)
def get_claim(claim_id: str, db: Session = Depends(get_db)) -> dict:
    record = repository.get(db, claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail="claim not found")
    return record.decision_json


@app.get("/api/claims/{claim_id}/explain", response_model=Explanation)
def explain_claim(claim_id: str, db: Session = Depends(get_db)) -> Explanation:
    record = repository.get(db, claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail="claim not found")
    return explain_decision(Decision(**record.decision_json))


@app.get("/api/claims")
def list_claims(limit: int = 10, offset: int = 0, status: str | None = None,
                db: Session = Depends(get_db)) -> dict:
    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    records = repository.list_all(db, limit=limit, offset=offset, status=status)
    return {
        "items": [
            {"claim_id": r.claim_id, "member_name": r.member_name, "decision": r.decision,
             "claim_amount": r.claim_amount, "approved_amount": r.approved_amount,
             "flags": (r.decision_json or {}).get("flags", [])}
            for r in records
        ],
        "total": repository.count_claims(db, status=status),
    }


class ReviewAction(BaseModel):
    action: Literal["approve", "reject"]
    note: str = ""


@app.post("/api/claims/{claim_id}/review", response_model=Decision)
def resolve_review(claim_id: str, payload: ReviewAction, db: Session = Depends(get_db)) -> dict:
    record = repository.get(db, claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail="claim not found")
    if record.decision != "MANUAL_REVIEW":
        raise HTTPException(status_code=409, detail="claim is not awaiting review")

    data = dict(record.decision_json)
    if payload.action == "approve":
        amount = record.approved_amount or record.claim_amount
        data.update(decision="APPROVED", approved_amount=amount,
                    notes=f"Approved by claims officer. {payload.note}".strip(),
                    next_steps="Reimbursement will be processed.")
    else:
        amount = 0.0
        data.update(decision="REJECTED", approved_amount=0.0,
                    notes=f"Rejected by claims officer. {payload.note}".strip(),
                    next_steps="This claim will not be reimbursed.")
    data["confidence_score"] = 1.0
    data["flags"] = list(data.get("flags", [])) + ["Resolved by claims officer"]

    repository.resolve(db, record, data["decision"], amount, data)
    return data


@app.get("/api/policy")
def policy() -> dict:
    return load_policy()


@app.put("/api/policy")
def update_policy(policy: dict = Body(...)) -> dict:
    if not isinstance(policy, dict) or "coverage_details" not in policy:
        raise HTTPException(status_code=422, detail="invalid policy: missing coverage_details")
    return save_policy(policy)
