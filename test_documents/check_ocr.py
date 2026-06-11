"""Deterministic check (no LLM): confirm OCR reads the fields each outcome needs.

Run:  ../backend/.venv/Scripts/python.exe check_ocr.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))

from app.ingestion import ocr_document  # noqa: E402

# Substrings that MUST appear in the OCR text for the engine to reach the outcome.
REQUIRED = {
    "01_approved_consultation": ["KA/45678/2015", "Viral fever", "Consultation Fee", "1,000", "500"],
    "02_partial_dental_cosmetic": ["MH/23456/2018", "root canal", "Teeth Whitening", "8,000", "4,000"],
    "03_rejected_mri_no_preauth": ["AP/67890/2017", "MRI", "15,000"],
    "04_rejected_excluded_weightloss": ["WB/34567/2015", "Obesity", "Weight Loss", "5,000"],
    "05_approved_ayurveda": ["AYUR/KL/2345/2019", "Panchakarma", "3,000"],
    "06_approved_network_cashless": ["TN/56789/2013", "bronchitis", "1,500", "3,000"],
}


def run() -> int:
    failures = 0
    for folder, needles in REQUIRED.items():
        path = os.path.join(HERE, folder)
        text = ""
        for name in ("prescription.pdf", "bill.pdf"):
            with open(os.path.join(path, name), "rb") as f:
                text += ocr_document(name, f.read()) + "\n"
        low = text.lower()
        missing = [n for n in needles if n.lower() not in low]
        status = "OK" if not missing else f"MISSING {missing}"
        if missing:
            failures += 1
        print(f"{folder:<34}{status}")
    print("-" * 60)
    print("All fields readable." if not failures else f"{failures} case(s) with missing text.")
    return failures


if __name__ == "__main__":
    raise SystemExit(run())
