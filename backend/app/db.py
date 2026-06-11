"""SQLite persistence (SQLAlchemy). Swap DATABASE_URL for Postgres in prod."""
from __future__ import annotations

import os
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./claims.db")
# SQLite is shared between the API and the Temporal worker (separate processes);
# a busy timeout lets a writer wait for a lock instead of failing immediately.
_connect_args = {"check_same_thread": False, "timeout": 30} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ClaimRecord(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    member_name: Mapped[str] = mapped_column(String)
    treatment_date: Mapped[date] = mapped_column(Date)
    claim_amount: Mapped[float] = mapped_column(Float)
    signature: Mapped[str] = mapped_column(String, index=True)
    decision: Mapped[str] = mapped_column(String)
    approved_amount: Mapped[float] = mapped_column(Float, default=0.0)
    decision_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
