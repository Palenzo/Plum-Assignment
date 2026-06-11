"""AI accuracy harness — measures how well OCR + LLM extraction reads documents.

`eval.py` scores the deterministic engine on structured JSON. This scores the
*AI*: for every test document it runs the real OCR -> LLM extraction, compares
each adjudication-relevant field against ground truth, and runs the extracted
claim through the engine to check the end-to-end decision.

Reports:
  - field-level extraction accuracy (doctor reg, diagnosis, bill line items)
  - decision accuracy through the AI path (extraction -> engine)

Needs an LLM key (OpenAI or Groq) in backend/.env.
Run:  python eval_ai.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.engine import adjudicate
from app.extraction import extract, to_claim_input
from app.ingestion import ocr_document
from app.llm import llm_available, model_name
from app.config import settings

DOCS = Path(__file__).parents[1] / "test_documents"

# Ground truth (what a correct extraction must yield) + the form metadata a
# tester would enter, per document. Line items are (name-keyword, amount).
GROUND_TRUTH = [
    {"dir": "01_approved_consultation", "reg": "KA/45678/2015",
     "diagnosis_kw": "viral fever",
     "items": [("consultation", 1000), ("diagnostic", 500)],
     "meta": {"claim_amount": 1500}, "decision": "APPROVED"},
    {"dir": "02_partial_dental_cosmetic", "reg": "MH/23456/2018",
     "diagnosis_kw": "tooth decay",
     "items": [("root canal", 8000), ("whitening", 4000)],
     "meta": {"claim_amount": 12000}, "decision": "PARTIAL"},
    {"dir": "03_rejected_mri_no_preauth", "reg": "AP/67890/2017",
     "diagnosis_kw": "lumbar",
     "items": [("mri", 15000)],
     "meta": {"claim_amount": 15000}, "decision": "REJECTED"},
    {"dir": "04_rejected_excluded_weightloss", "reg": "WB/34567/2015",
     "diagnosis_kw": "obesity",
     "items": [("bariatric", 3000), ("diet", 5000)],
     "meta": {"claim_amount": 8000}, "decision": "REJECTED"},
    {"dir": "05_approved_ayurveda", "reg": "AYUR/KL/2345/2019",
     "diagnosis_kw": "joint pain",
     "items": [("consultation", 1000), ("panchakarma", 3000)],
     "meta": {"claim_amount": 4000}, "decision": "APPROVED"},
    {"dir": "06_approved_network_cashless", "reg": "TN/56789/2013",
     "diagnosis_kw": "bronchitis",
     "items": [("consultation", 1500), ("medicines", 3000)],
     "meta": {"claim_amount": 4500, "hospital": "Apollo Hospitals",
              "cashless_request": True}, "decision": "APPROVED"},
]


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().split())


def _reg_ok(extracted, truth: str) -> bool:
    got = _norm(extracted.doctor_reg).replace(" ", "")
    return got == truth.lower().replace(" ", "")


def _diagnosis_ok(extracted, kw: str) -> bool:
    blob = _norm(f"{extracted.diagnosis} {extracted.treatment}")
    return kw.lower() in blob


def _item_ok(extracted, kw: str, amount: float) -> bool:
    for li in extracted.line_items:
        if kw in _norm(li.name) and abs(li.amount - amount) < 0.5:
            return True
    return False


def run() -> int:
    if not llm_available():
        print("No LLM API key set (OPENAI_API_KEY or GROQ_API_KEY). "
              "Add one to backend/.env and re-run.")
        return 2

    print(f"AI extraction accuracy  ·  provider={settings()['provider']}  model={model_name()}\n")
    print(f"{'Case':<34}{'Reg':<5}{'Diag':<6}{'Items':<8}{'Decision':<12}")
    print("-" * 70)

    reg_hits = diag_hits = item_hits = item_total = 0
    decision_hits = decision_total = 0
    errored = 0

    for gt in GROUND_TRUTH:
        path = DOCS / gt["dir"]
        try:
            text = ""
            for name in ("prescription.pdf", "bill.pdf"):
                text += ocr_document(name, (path / name).read_bytes()) + "\n\n"
            extracted = extract(text)
        except Exception as exc:  # noqa: BLE001 — quota / API issue is environmental
            msg = str(exc).lower()
            note = "quota/rate-limit" if any(k in msg for k in ("quota", "rate", "429")) else "error"
            print(f"{gt['dir']:<34}{'-':<5}{'-':<6}{'-':<8}{note}")
            errored += 1
            continue

        reg_ok = _reg_ok(extracted, gt["reg"])
        diag_ok = _diagnosis_ok(extracted, gt["diagnosis_kw"])
        items_ok = sum(_item_ok(extracted, kw, amt) for kw, amt in gt["items"])
        n_items = len(gt["items"])

        claim = to_claim_input(extracted, member_id="EVAL", member_name="Eval",
                               treatment_date=date(2024, 11, 1), **gt["meta"])
        got = adjudicate(claim).decision
        decision_ok = got == gt["decision"]

        reg_hits += reg_ok
        diag_hits += diag_ok
        item_hits += items_ok
        item_total += n_items
        decision_hits += decision_ok
        decision_total += 1

        print(f"{gt['dir']:<34}"
              f"{'ok' if reg_ok else 'MISS':<5}"
              f"{'ok' if diag_ok else 'MISS':<6}"
              f"{f'{items_ok}/{n_items}':<8}"
              f"{got:<10}{'ok' if decision_ok else 'MISS'}")

    scored = decision_total
    if not scored:
        print("\nNo documents scored (all calls failed — likely quota). Try again later.")
        return 1

    field_hits = reg_hits + diag_hits + item_hits
    field_total = scored * 2 + item_total  # reg + diagnosis + items per doc
    print("-" * 70)
    print(f"Field extraction accuracy: {field_hits}/{field_total} "
          f"({round(100 * field_hits / field_total)}%)")
    print(f"  doctor_reg : {reg_hits}/{scored}")
    print(f"  diagnosis  : {diag_hits}/{scored}")
    print(f"  line items : {item_hits}/{item_total}")
    print(f"Decision accuracy (AI path): {decision_hits}/{scored} "
          f"({round(100 * decision_hits / scored)}%)")
    if errored:
        print(f"\nNote: {errored} document(s) skipped (provider quota/rate-limit).")
    return 0 if decision_hits == scored else 1


if __name__ == "__main__":
    raise SystemExit(run())
