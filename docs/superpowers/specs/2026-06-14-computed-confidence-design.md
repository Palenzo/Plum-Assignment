# Spec: Real, Computed Confidence Scores

**Date:** 2026-06-14
**Status:** Approved (design) — pending implementation plan
**Addresses:** Evaluation weakness #3 — "confidence scores are faked, not calculated."

## Problem

Today every confidence score is a fixed constant keyed off the verdict:

- `engine._confidence(decision, category)` → hardcoded lookup
  (`MANUAL_REVIEW 0.65`, `REJECTED 0.97`, `PARTIAL 0.92`, `APPROVED 0.89/0.93`).
- `gates.py` → flat `1.0`; `main.py` resolve → flat `1.0`.
- `review.py` → clamps to `0.7` on escalation.
- The AI's own `ReviewAssessment.overall_confidence` is computed but **never used**.

The number does not move with the actual evidence — neither how clearly the
document was read nor how strong the claim's support is. `ASSUMPTIONS.md §9`
documents this honestly, but it half-meets the "confidence scores" bonus: it is
a label, not a measurement.

## Goal

Replace the constants with a single, transparent confidence model that is
**derived from evidence**, **explainable** (it records *why*), and
**actionable** (very weak evidence escalates to a human).

## Non-goals

- No change to the deterministic decision logic for clean inputs — the 10
  provided test cases must keep their decisions, amounts, and confidence bands.
- No recalibration into true probabilities; this is a defensible directional
  score, not a trained classifier.
- No new dependencies.

## The model — `app/confidence.py` (new)

A pure function, no I/O:

```python
score(signals: EvidenceSignals) -> tuple[float, list[ConfidenceFactor]]
```

`ConfidenceFactor` = `{label: str, detail: str, delta: float}` — each adjustment
is named so the UI and audit can show the reasons.

### Signals weighed

| Signal | Source | Effect on score |
|---|---|---|
| Decision decisiveness | which rule decided (categorical vs numeric) | hard rules (missing docs, exclusion, invalid reg, impossible date) → near-certain |
| Threshold margin | `claim_amount` vs per-claim & category sub-limit; treatment date vs waiting-period boundary | a near-miss (e.g. ₹4,900 of ₹5,000) lowers confidence — a small read error could flip the decision |
| Field completeness | the extracted `ClaimInput` | missing diagnosis / doctor reg / bill line items → weaker evidence |
| OCR quality | Tesseract mean word-confidence (newly captured) | a blurry scan lowers confidence; a vision-LLM fallback read is flagged "unverified" |
| AI review | `ReviewAssessment.overall_confidence` + whether a concern was raised | folds the AI's own certainty in (today ignored) |

### Formula shape

Start from a decision-type base, apply **bounded** penalties per weak signal,
clamp to the contract band. Penalties are small and additive-in-log so no single
factor dominates. Contract (asserted by `test_adjudication.py`):

- `MANUAL_REVIEW` → `< 0.8`
- every other decision → `>= 0.85`
- always within `[0, 1]`

Clean structured inputs (the JSON path) carry no OCR penalty and full
completeness, so they land high (≥ 0.85) and the existing suite stays green.

### Consistency invariant (why ≥ 0.85 and < 0.70 don't conflict)

The contract `test_adjudication.py` asserts (`≥ 0.85` non-manual, `< 0.8` manual)
is over **clean structured inputs**, and the model guarantees it for them:
margin penalties alone are bounded so a clean APPROVED/PARTIAL/REJECTED never
crosses 0.85, and clean inputs carry no OCR/completeness penalty. Uploaded
documents *may* legitimately land a non-manual decision in the 0.70–0.85 band —
that is the honest "somewhat uncertain but not escalation-worthy" zone; below
0.70 an approvable claim escalates to `MANUAL_REVIEW`. Rejections are categorical
and are **not** subject to low-confidence escalation.

## Capturing OCR quality — `app/ingestion.py`

- Image OCR switches from `pytesseract.image_to_string` to `image_to_data`
  (`Output.DICT`), averaging the per-word `conf` values into a 0–1 quality.
- Text-layer PDF pages = perfect read (`1.0`); Tesseract = measured; vision-LLM
  fallback = `None` quality + `ocr_fallback=True` (flagged "unverified").
- `ocr_document` returns text as before; a new detailed variant also returns an
  `OcrStats(mean_conf, used_fallback)` so existing callers are unaffected.

## Threading the evidence

- `adjudicate(claim, policy=None, claim_id=..., evidence: Evidence | None = None)`
  gains an optional `Evidence` (OCR quality + fallback flag). **JSON path passes
  `None`** (no OCR uncertainty). **Upload path** builds it in `service.py` from
  the aggregated `ingestion` stats.
- `engine.py` replaces every `_confidence(...)` call with
  `confidence.score(...)`, assembling `EvidenceSignals` from the rule it hit, the
  threshold margins, field completeness, and the passed-in `Evidence`.
- `review.py` folds `overall_confidence` into the escalation score instead of the
  flat `0.7`.
- `gates.py` hard rejections stay categorical (near-certain).

## Actionable escalation (low confidence → manual review)

`adjudication_rules.md` lists **"System confidence < 70% → manual review."** So:
after the engine reaches an **APPROVED/PARTIAL** decision, if computed confidence
is below a `LOW_CONFIDENCE_THRESHOLD` (default `0.70`, env-overridable), the
decision is routed to `MANUAL_REVIEW` with flag `LOW_CONFIDENCE` and a note
naming the weak factors (e.g. "blurry scan", "missing diagnosis"). This only
fires on poor-quality uploads; the clean test cases never trip it. The engine
remains the source of truth — confidence can only make it *more* cautious, never
approve or change an amount (same discipline as the AI review layer).

## Explainability in the UI

- `Decision` gains `confidence_factors: list[ConfidenceFactor] = []`
  (back-compatible default).
- `ConfidenceMeter` renders the top 2–3 factors beneath the bar
  ("Document read clearly · 97%", "Comfortable margin under limit" / or
  "Blurry scan — low OCR confidence", "Amount close to the limit").

## Testing

- New `tests/test_confidence.py` — **property/monotonicity** tests:
  blurrier OCR ⇒ lower, thinner margin ⇒ lower, more missing fields ⇒ lower,
  result always in `[0, 1]`, and the low-confidence escalation fires below
  threshold but not above.
- `test_adjudication.py` bands stay green (clean inputs ≥ 0.85 / manual < 0.8).
- `eval.py` unchanged (scores decision + amount only).
- A short manual check via `eval_ai.py`-style upload to confirm a degraded
  document yields a visibly lower confidence.

## Build order

1. `confidence.py` — model + factors + unit tests (pure, no wiring).
2. `ingestion.py` — capture OCR mean word-confidence (`OcrStats`).
3. `engine.py` — replace `_confidence` with `confidence.score`; thread `Evidence`.
4. `service.py` — build `Evidence` from OCR stats on the upload path.
5. `review.py` / `gates.py` — fold AI confidence; keep gates categorical.
6. Low-confidence → `MANUAL_REVIEW` escalation.
7. `Decision.confidence_factors` + `ConfidenceMeter` UI.
8. Tests across all of it; verify existing suites stay green.
