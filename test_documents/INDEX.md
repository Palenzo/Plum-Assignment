# Manual test documents

Realistic OPD **prescription + bill** documents for testing the upload → OCR →
LLM extraction → adjudication flow end to end. Each folder is one claim and is
designed to produce a specific decision.

- **Format:** text-layer **PDFs** (read cleanly, no OCR errors). Folder `01` also
  has a `prescription.png` to exercise the image-OCR (Tesseract) path.
- **What the documents carry:** doctor + registration number, diagnosis/treatment,
  and the itemised bill. **What you type in the form:** the metadata below
  (amount, hospital, cashless, etc.) — that is not on the documents by design.

> Image/PDF upload needs **Tesseract** installed and a **Groq API key** (the LLM
> reads the extracted text). Without them, use the one-click JSON samples in the UI
> instead. Note the Groq **free tier has a daily token cap** — if extraction pauses,
> the quota is spent (see README).

## How to run each case

1. Open the app, go to **Submit a claim**.
2. Choose **Upload documents**, attach the folder's `prescription.pdf` and `bill.pdf`.
3. Enter the **form inputs** from the table.
4. Submit and compare against **Expected outcome**.

| # | Folder | Upload | Form inputs | Expected outcome |
|---|--------|--------|-------------|------------------|
| 1 | `01_approved_consultation` | prescription.pdf + bill.pdf | amount **1500** | **APPROVED** ≈ ₹1,350 (10% co-pay ₹150) |
| 2 | `02_partial_dental_cosmetic` | prescription.pdf + bill.pdf | amount **12000** | **PARTIAL** ≈ ₹8,000 (teeth whitening stripped as cosmetic) |
| 3 | `03_rejected_mri_no_preauth` | prescription.pdf + bill.pdf | amount **15000** | **REJECTED** · `PRE_AUTH_MISSING` (MRI/CT need pre-auth) |
| 4 | `04_rejected_excluded_weightloss` | prescription.pdf + bill.pdf | amount **8000** | **REJECTED** · `SERVICE_NOT_COVERED` (weight-loss excluded) |
| 5 | `05_approved_ayurveda` | prescription.pdf + bill.pdf | amount **4000** | **APPROVED** ≈ ₹4,000 (alternative medicine within sub-limit) |
| 6 | `06_approved_network_cashless` | prescription.pdf + bill.pdf | amount **4500**, hospital **Apollo Hospitals**, cashless **ON** | **APPROVED** ≈ ₹3,600 (₹900 network discount, cashless) |

### Edge cases that need no document (use the JSON box or form metadata)
- **Missing documents → REJECTED** (`MISSING_DOCUMENTS`): submit any case with only the bill, no prescription.
- **Waiting period → REJECTED** (`WAITING_PERIOD`): a diabetes/hypertension diagnosis with `member_join_date` < 90 days before treatment.
- **Fraud → MANUAL_REVIEW**: set **previous_claims_same_day = 3** on any case — routes to the `/review` queue (your human-in-the-loop demo).

## Regenerate / re-verify

```powershell
cd test_documents
..\backend\.venv\Scripts\python.exe generate.py     # rebuild the PDFs + PNG
..\backend\.venv\Scripts\python.exe check_ocr.py    # deterministic: every field is OCR-readable
..\backend\.venv\Scripts\python.exe verify.py       # full pipeline (needs Groq quota): decision per case
```

`check_ocr.py` confirms the documents are machine-readable (all 6 pass); `verify.py`
runs the real OCR + LLM + engine and prints the decision for each case.
