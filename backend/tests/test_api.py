"""API + persistence: submit a claim, read it back, catch duplicates."""
from __future__ import annotations

TC001 = {
    "member_id": "EMP001", "member_name": "Rajesh Kumar",
    "treatment_date": "2024-11-01", "claim_amount": 1500,
    "prescription": {
        "doctor_name": "Dr. Sharma", "doctor_reg": "KA/45678/2015",
        "diagnosis": "Viral fever", "medicines_prescribed": ["Paracetamol 650mg"],
    },
    "bill": {"consultation_fee": 1000, "diagnostic_tests": 500},
}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_submit_approves_and_persists(client):
    resp = client.post("/api/claims/json", json=TC001)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "APPROVED"
    assert body["approved_amount"] == 1350

    claim_id = body["claim_id"]
    fetched = client.get(f"/api/claims/{claim_id}")
    assert fetched.status_code == 200
    assert fetched.json()["claim_id"] == claim_id

    listing = client.get("/api/claims").json()
    assert listing["total"] >= 1
    assert any(c["claim_id"] == claim_id for c in listing["items"])


def test_duplicate_resubmission_is_flagged(client):
    client.post("/api/claims/json", json=TC001)
    second = client.post("/api/claims/json", json=TC001).json()
    assert second["decision"] == "REJECTED"
    assert "DUPLICATE_CLAIM" in second["rejection_reasons"]


def test_unknown_claim_returns_404(client):
    assert client.get("/api/claims/CLM_UNKNOWN").status_code == 404


def test_non_finite_or_negative_amount_is_rejected_at_boundary(client):
    # Infinity/NaN/negative/zero must fail validation (422) rather than reach the
    # engine and be serialised back as bare `Infinity` (invalid JSON / workflow hang).
    for bad in ("Infinity", "NaN", "-1", "0"):
        body = '{"member_id":"X","member_name":"Y","treatment_date":"2024-11-01",' \
               f'"claim_amount":{bad}}}'
        resp = client.post("/api/claims/json", content=body,
                           headers={"content-type": "application/json"})
        assert resp.status_code == 422, f"{bad} should be rejected, got {resp.status_code}"
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_claims_are_paginated(client):
    for i in range(3):
        payload = {**TC001, "member_id": f"EMP-P{i}", "claim_amount": 1500 + i * 100,
                   "bill": {"consultation_fee": 1000 + i * 100, "diagnostic_tests": 500}}
        assert client.post("/api/claims/json", json=payload).status_code == 200

    first = client.get("/api/claims?limit=2").json()
    assert len(first["items"]) == 2
    assert first["total"] == 3

    second = client.get("/api/claims?limit=2&offset=2").json()
    assert len(second["items"]) == 1
