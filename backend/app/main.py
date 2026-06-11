"""FastAPI surface for claim submission and status."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from . import repository
from .db import get_db, init_db
from .ingestion import ocr_document
from .models import ClaimInput, Decision
from .policy import load_policy
from .service import adjudicate_and_store, adjudicate_upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OPD Claim Adjudication", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/claims/json", response_model=Decision)
def submit_claim(payload: ClaimInput, db: Session = Depends(get_db)) -> Decision:
    return adjudicate_and_store(db, payload)


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
    return adjudicate_upload(
        db, member_id=member_id, member_name=member_name, treatment_date=treatment_date,
        claim_amount=claim_amount, doc_texts=doc_texts, member_join_date=member_join_date,
        hospital=hospital, cashless_request=cashless_request,
        previous_claims_same_day=previous_claims_same_day)


@app.get("/api/claims/{claim_id}", response_model=Decision)
def get_claim(claim_id: str, db: Session = Depends(get_db)) -> dict:
    record = repository.get(db, claim_id)
    if record is None:
        raise HTTPException(status_code=404, detail="claim not found")
    return record.decision_json


@app.get("/api/claims")
def list_claims(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"claim_id": r.claim_id, "member_name": r.member_name, "decision": r.decision,
         "claim_amount": r.claim_amount, "approved_amount": r.approved_amount}
        for r in repository.list_all(db)
    ]


@app.get("/api/policy")
def policy() -> dict:
    return load_policy()
