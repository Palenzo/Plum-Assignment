"""Admin: view and edit the live policy."""
from __future__ import annotations


def test_get_policy_returns_limits(client):
    policy = client.get("/api/policy").json()
    assert policy["coverage_details"]["per_claim_limit"] == 5000


def test_update_policy_persists(client):
    policy = client.get("/api/policy").json()
    policy["coverage_details"]["per_claim_limit"] = 6000
    resp = client.put("/api/policy", json=policy)
    assert resp.status_code == 200
    assert client.get("/api/policy").json()["coverage_details"]["per_claim_limit"] == 6000


def test_update_policy_rejects_invalid(client):
    assert client.put("/api/policy", json={"nonsense": True}).status_code == 422
