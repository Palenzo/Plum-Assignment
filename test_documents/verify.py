"""Verify the generated documents drive the correct adjudication outcome.

Runs the real pipeline: OCR -> LLM extraction -> deterministic engine.
Run from the backend venv:  ../backend/.venv/Scripts/python.exe verify.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.engine import adjudicate              # noqa: E402
from app.extraction import extract, to_claim_input  # noqa: E402
from app.ingestion import ocr_document         # noqa: E402

from datetime import date                       # noqa: E402

# Form metadata the tester would type, per case folder.
META = {
    "01_approved_consultation": dict(amount=1500),
    "02_partial_dental_cosmetic": dict(amount=12000),
    "03_rejected_mri_no_preauth": dict(amount=15000),
    "04_rejected_excluded_weightloss": dict(amount=8000),
    "05_approved_ayurveda": dict(amount=4000),
    "06_approved_network_cashless": dict(amount=4500, hospital="Apollo Hospitals", cashless=True),
}
EXPECT = {
    "01_approved_consultation": "APPROVED",
    "02_partial_dental_cosmetic": "PARTIAL",
    "03_rejected_mri_no_preauth": "REJECTED",
    "04_rejected_excluded_weightloss": "REJECTED",
    "05_approved_ayurveda": "APPROVED",
    "06_approved_network_cashless": "APPROVED",
}


def run() -> None:
    print(f"{'Case':<34}{'Expected':<12}{'Got':<14}{'Amount':>10}")
    print("-" * 72)
    for folder, meta in META.items():
        path = os.path.join(HERE, folder)
        texts = []
        for name in ("prescription.pdf", "bill.pdf"):
            with open(os.path.join(path, name), "rb") as f:
                texts.append(ocr_document(name, f.read()))
        extracted = extract("\n\n".join(texts))
        claim = to_claim_input(
            extracted, member_id="EMP", member_name="Test",
            treatment_date=date(2024, 11, 1), claim_amount=meta["amount"],
            hospital=meta.get("hospital"), cashless_request=meta.get("cashless", False))
        d = adjudicate(claim)
        ok = "OK" if d.decision == EXPECT[folder] else "MISMATCH"
        amt = f"{d.approved_amount:,.0f}" if d.approved_amount else "-"
        print(f"{folder:<34}{EXPECT[folder]:<12}{d.decision:<14}{amt:>10}  {ok}")


if __name__ == "__main__":
    run()
