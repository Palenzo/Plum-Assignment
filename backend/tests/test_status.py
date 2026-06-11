"""Live status endpoint — reports which capabilities are available."""
from __future__ import annotations


def test_status_reports_capabilities(client):
    body = client.get("/api/status").json()
    assert body["status"] == "ok"
    assert isinstance(body["ai_available"], bool)
    assert isinstance(body["ocr_available"], bool)
    assert isinstance(body["temporal_enabled"], bool)
    assert "model" in body
