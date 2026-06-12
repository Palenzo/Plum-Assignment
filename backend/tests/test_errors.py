"""Every API error returns the same clean envelope: {"error", "code"}."""
from __future__ import annotations


def test_not_found_uses_error_envelope(client):
    resp = client.get("/api/claims/CLM_NOPE")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert body["error"] and isinstance(body["error"], str)
    assert "detail" not in body  # old raw-FastAPI shape is gone


def test_unauthorized_uses_error_envelope(client):
    resp = client.put("/api/policy", json={"coverage_details": {}})  # no admin token
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_validation_error_is_human_readable(client):
    resp = client.post("/api/claims/json", json={"member_id": "EMP1"})  # missing fields
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "validation failed" in body["error"].lower()
