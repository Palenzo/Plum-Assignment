"""The human side of HITL: a reviewer resolves a MANUAL_REVIEW claim."""
from __future__ import annotations

# Fraud anomaly -> deterministic MANUAL_REVIEW (no LLM needed).
PENDING = {
    "member_id": "EMP008", "member_name": "Ravi Menon",
    "treatment_date": "2024-10-30", "claim_amount": 4800, "previous_claims_same_day": 3,
    "prescription": {"doctor_reg": "UP/45678/2016", "diagnosis": "Migraine",
                     "medicines_prescribed": ["Sumatriptan"]},
    "bill": {"consultation_fee": 2000, "medicines": 2800},
}
APPROVED = {
    "member_id": "EMP001", "member_name": "Rajesh", "treatment_date": "2024-11-01",
    "claim_amount": 1500, "prescription": {"doctor_reg": "KA/45678/2015", "diagnosis": "Viral fever"},
    "bill": {"consultation_fee": 1000, "diagnostic_tests": 500},
}


def _pending(client) -> str:
    resp = client.post("/api/claims/json", json=PENDING).json()
    assert resp["decision"] == "MANUAL_REVIEW"
    return resp["claim_id"]


def test_reviewer_can_approve(client):
    claim_id = _pending(client)
    resp = client.post(f"/api/claims/{claim_id}/review", json={"action": "approve", "note": "Verified"})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "APPROVED"
    assert client.get(f"/api/claims/{claim_id}").json()["decision"] == "APPROVED"


def test_reviewer_can_reject(client):
    claim_id = _pending(client)
    resp = client.post(f"/api/claims/{claim_id}/review", json={"action": "reject", "note": "Not genuine"})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "REJECTED"
    assert resp.json()["approved_amount"] == 0


def test_resolving_unknown_claim_is_404(client):
    assert client.post("/api/claims/CLM_NOPE/review", json={"action": "approve"}).status_code == 404


def test_resolving_a_settled_claim_is_409(client):
    claim_id = client.post("/api/claims/json", json=APPROVED).json()["claim_id"]
    resp = client.post(f"/api/claims/{claim_id}/review", json={"action": "approve"})
    assert resp.status_code == 409
