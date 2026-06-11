"""Admin: view and edit the live policy (write access is password-protected)."""
from __future__ import annotations

# Matches the ADMIN_TOKEN default used when the env var is unset (see main.py).
AUTH = {"X-Admin-Token": "admin"}


def test_get_policy_returns_limits(client):
    policy = client.get("/api/policy").json()
    assert policy["coverage_details"]["per_claim_limit"] == 5000


def test_update_policy_persists(client):
    policy = client.get("/api/policy").json()
    policy["coverage_details"]["per_claim_limit"] = 6000
    resp = client.put("/api/policy", json=policy, headers=AUTH)
    assert resp.status_code == 200
    assert client.get("/api/policy").json()["coverage_details"]["per_claim_limit"] == 6000


def test_update_policy_rejects_invalid(client):
    assert client.put("/api/policy", json={"nonsense": True}, headers=AUTH).status_code == 422


def test_update_policy_requires_auth(client):
    policy = client.get("/api/policy").json()
    assert client.put("/api/policy", json=policy).status_code == 401
    assert client.put("/api/policy", json=policy, headers={"X-Admin-Token": "wrong"}).status_code == 401


def test_admin_login(client):
    assert client.post("/api/admin/login", headers=AUTH).status_code == 200
    assert client.post("/api/admin/login", headers={"X-Admin-Token": "wrong"}).status_code == 401
