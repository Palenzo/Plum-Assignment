"""FastAPI surface for claim submission and status."""
from __future__ import annotations

import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from fastapi import Body, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import repository
from .config import settings
from .confidence import Evidence
from .llm import llm_available, model_name
from .db import get_db, init_db
from .errors import install_error_handlers
from .explain import Explanation, explain_decision
from .ingestion import (OcrStats, OcrUnavailable, ocr_available,
                        ocr_document_detailed, tesseract_available)
from .models import ClaimInput, Decision
from .vision import vision_available
from .policy import load_policy, save_policy
from .service import adjudicate_and_store, adjudicate_upload
from .temporal.client import run_workflow
from .temporal.shared import WorkflowInput

TEMPORAL_ENABLED = os.getenv("TEMPORAL_ENABLED", "true").lower() == "true"

# Admin password for policy edits. Defaults to "admin" for local dev — set a real
# value via the ADMIN_TOKEN env var in any deployed environment.
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN") or "admin"


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Reject policy writes unless the correct admin token is presented."""
    if not (x_admin_token and secrets.compare_digest(x_admin_token, ADMIN_TOKEN)):
        raise HTTPException(status_code=401, detail="Invalid admin password")


async def _orchestrate(db: Session, claim: ClaimInput, doc_texts: dict[str, str],
                       needs_extraction: bool, evidence: Evidence | None = None) -> Decision:
    """Run the claim through the durable workflow, falling back in-process."""
    if TEMPORAL_ENABLED:
        try:
            return await run_workflow(WorkflowInput(
                claim=claim, doc_texts=doc_texts, needs_extraction=needs_extraction,
                evidence=evidence))
        except Exception as exc:  # Temporal unreachable — keep the app working
            print(f"[temporal] unavailable, running in-process: {exc}")
    if needs_extraction:
        return adjudicate_upload(
            db, member_id=claim.member_id, member_name=claim.member_name,
            treatment_date=claim.treatment_date, claim_amount=claim.claim_amount,
            doc_texts=doc_texts, member_join_date=claim.member_join_date, hospital=claim.hospital,
            cashless_request=claim.cashless_request,
            previous_claims_same_day=claim.previous_claims_same_day, evidence=evidence)
    return adjudicate_and_store(db, claim)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OPD Claim Adjudication", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)

# --- Logging: level follows the dev/prod toggle (APP_ENV / LOG_LEVEL) ---
_cfg = settings()
logging.basicConfig(
    level=_cfg["log_level"],
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("opd")
log.setLevel(_cfg["log_level"])
log.info("Backend starting — app_env=%s log_level=%s provider=%s",
         _cfg["app_env"], _cfg["log_level"], _cfg["provider"])


@app.middleware("http")
async def _log_requests(request, call_next):
    """Log every request with status + timing. Render's frequent /health pings
    log at DEBUG so they don't flood production logs (visible in development)."""
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    level = logging.DEBUG if request.url.path == "/health" else logging.INFO
    log.log(level, "%s %s -> %d (%.1f ms)",
            request.method, request.url.path, response.status_code, elapsed_ms)
    return response

# Local dev origins plus any explicit ones from CORS_ORIGINS (comma-separated).
# Deployed frontends on Render are matched by regex so the backend needs no
# knowledge of the exact frontend URL.
_DEFAULT_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS + _extra_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/status")
def status() -> dict:
    """Live status — which capabilities are currently available."""
    engine = ("tesseract" if tesseract_available()
              else "llm-vision" if vision_available() else None)
    return {
        "status": "ok",
        "ai_available": llm_available(),
        "ocr_available": ocr_available(),
        "ocr_engine": engine,
        "temporal_enabled": TEMPORAL_ENABLED,
        "provider": settings()["provider"],
        "model": model_name(),
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
    stats_parts: list[OcrStats] = []
    try:
        for label, upload in (("prescription", prescription), ("bill", bill)):
            if upload is not None:
                text, stats = ocr_document_detailed(upload.filename, await upload.read())
                doc_texts[label] = text
                stats_parts.append(stats)
    except OcrUnavailable:
        raise HTTPException(status_code=503, detail={
            "code": "OCR_UNAVAILABLE",
            "message": "Document scanning (OCR) is unavailable on this server. "
                       "Submit the claim as JSON, upload a text-based PDF, or enable "
                       "Tesseract / an LLM vision model.",
        })
    # Document read-quality feeds the confidence model (and may escalate a blurry scan).
    evidence: Evidence | None = None
    if stats_parts:
        combined = OcrStats.combine(stats_parts)
        evidence = Evidence(ocr_quality=combined.mean_conf, ocr_fallback=combined.used_fallback)
    metadata = ClaimInput(
        member_id=member_id, member_name=member_name, treatment_date=treatment_date,
        claim_amount=claim_amount, member_join_date=member_join_date, hospital=hospital,
        cashless_request=cashless_request, previous_claims_same_day=previous_claims_same_day)
    return await _orchestrate(db, metadata, doc_texts, needs_extraction=True, evidence=evidence)


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
                sort: str = "created_at", order: str = "desc",
                db: Session = Depends(get_db)) -> dict:
    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    if sort not in repository.SORT_COLUMNS:
        sort = "created_at"
    order = "asc" if order == "asc" else "desc"
    records = repository.list_all(db, limit=limit, offset=offset, status=status,
                                  sort=sort, order=order)
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


@app.post("/api/admin/login")
def admin_login(_: None = Depends(require_admin)) -> dict:
    """Validate an admin password (used by the admin UI's login gate)."""
    return {"ok": True}


@app.get("/api/policy")
def policy() -> dict:
    return load_policy()


@app.put("/api/policy")
def update_policy(policy: dict = Body(...), _: None = Depends(require_admin)) -> dict:
    if not isinstance(policy, dict) or "coverage_details" not in policy:
        raise HTTPException(status_code=422, detail="invalid policy: missing coverage_details")
    return save_policy(policy)
