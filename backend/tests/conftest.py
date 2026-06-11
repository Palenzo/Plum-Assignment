"""Test fixtures: an isolated SQLite DB and a FastAPI test client."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

_BACKEND = Path(__file__).parent.parent
os.environ["DATABASE_URL"] = "sqlite:///./test_claims.db"  # set before app import
os.environ["TEMPORAL_ENABLED"] = "false"  # tests use the in-process path
os.environ["AI_REVIEW_ENABLED"] = "false"  # deterministic engine only in tests
os.environ["POLICY_PATH"] = str(_BACKEND / "test_policy.json")  # never touch the real policy

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.policy import DEFAULT_PATH, load_policy

_SOURCE_POLICY = _BACKEND / "app" / "data" / "policy_terms.json"


@pytest.fixture(autouse=True)
def fresh_policy():
    shutil.copy(_SOURCE_POLICY, DEFAULT_PATH)
    load_policy.cache_clear()
    yield


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
