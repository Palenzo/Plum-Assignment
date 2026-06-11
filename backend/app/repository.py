"""Data access for claim records — keeps SQLAlchemy out of the service layer."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .db import ClaimRecord
from .models import ClaimInput, Decision


def save(db: Session, claim: ClaimInput, decision: Decision, signature: str) -> ClaimRecord:
    record = ClaimRecord(
        claim_id=decision.claim_id, member_id=claim.member_id,
        member_name=claim.member_name, treatment_date=claim.treatment_date,
        claim_amount=claim.claim_amount, signature=signature,
        decision=decision.decision, approved_amount=decision.approved_amount,
        decision_json=decision.model_dump(mode="json"))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get(db: Session, claim_id: str) -> ClaimRecord | None:
    return db.query(ClaimRecord).filter(ClaimRecord.claim_id == claim_id).first()


def list_all(db: Session, *, limit: int = 10, offset: int = 0,
             status: str | None = None) -> list[ClaimRecord]:
    query = db.query(ClaimRecord)
    if status:
        query = query.filter(ClaimRecord.decision == status)
    return query.order_by(ClaimRecord.created_at.desc()).offset(offset).limit(limit).all()


def count_claims(db: Session, *, status: str | None = None) -> int:
    query = db.query(ClaimRecord)
    if status:
        query = query.filter(ClaimRecord.decision == status)
    return query.count()


def signatures(db: Session) -> set[str]:
    return {sig for (sig,) in db.query(ClaimRecord.signature).all()}


def resolve(db: Session, record: ClaimRecord, decision: str, approved_amount: float,
            decision_json: dict) -> ClaimRecord:
    """Record a reviewer's resolution of a MANUAL_REVIEW claim."""
    record.decision = decision
    record.approved_amount = approved_amount
    record.decision_json = decision_json
    db.commit()
    db.refresh(record)
    return record
