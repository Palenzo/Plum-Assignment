"""Test fixtures: an isolated SQLite DB and a FastAPI test client."""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_claims.db"  # set before app import

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


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
