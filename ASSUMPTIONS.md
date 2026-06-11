# Assumptions & Interpretation Notes

The provided `adjudication_rules.md`, `policy_terms.json` and `test_cases.json`
are internally inconsistent in a few places. Rather than silently pick a
reading, every non-obvious call the engine makes is recorded here, with the
evidence from the sample cases that forced it.

## 1. The per-claim limit contradicts itself across cases

- **TC003** rejects ₹7,500 outright with `PER_CLAIM_EXCEEDED` (limit is ₹5,000).
- **TC002** *approves* ₹8,000 (also above ₹5,000) as a `PARTIAL`.

These cannot both follow a single "claim_amount > 5000 → reject" rule.

**Interpretation:** the per-claim limit is a *hard reject only for a clean,
fully-covered claim*. When the claim contains an excluded line item (e.g. a
cosmetic procedure), it instead routes to the partial-approval path and is
capped by the relevant **category sub-limit**, not the per-claim limit.
TC002 → capped by the dental sub-limit (₹10,000) → ₹8,000 approved.
TC003 → no excluded items → pure over-limit → rejected.

## 2. Co-pay base (TC001)

Expected deduction is ₹150 on a ₹1,500 claim — i.e. **10% of the whole claim**,
not 10% of the consultation line alone. The engine applies the consultation
co-pay percentage to the full claim amount.

## 3. Network discount replaces co-pay (TC010)

Expected: ₹900 discount on ₹4,500 (20%) with **no co-pay stacked on top**.
The engine applies the network discount *instead of* the co-pay for claims at
a network hospital — the two are never combined.

## 4. Co-pay applies to consultation claims only

TC006 (alternative medicine) and TC002 (dental) are approved with **no co-pay**,
despite both containing a consultation fee. The 10% co-pay is therefore treated
as specific to general consultation claims; specialised categories settle at
their own sub-limit with no co-pay.

## 5. Diagnosis-level vs. line-item exclusions

- A condition that is itself excluded (TC009 — weight-loss/obesity) rejects the
  **whole** claim with `SERVICE_NOT_COVERED`.
- A covered condition with one cosmetic line item (TC002 — whitening) yields a
  **partial** approval, stripping only that item.

## 6. Doctor registration format

The canonical format is `State/Number/Year`, but TC006 uses the council-prefixed
alternative-medicine form `AYUR/KL/2345/2019`. The validator accepts any
`/`-separated registration ending in a 4-digit year, so both pass.

## 7. Pre-authorisation

MRI and CT scans always require pre-authorisation (TC007). As the claim payload
carries no pre-auth token, any MRI/CT claim is rejected with `PRE_AUTH_MISSING`.
This check runs in the coverage step, *before* limit checks, so the reason code
matches the sample even though the amount also breaches limits.

## 8. Fraud / manual review

`previous_claims_same_day >= 2`, or any claim above ₹25,000, routes to
`MANUAL_REVIEW` before approval — the "safety first" priority rule. TC008
(3 prior same-day claims) is the trigger in the sample set.

## 9. Confidence scores are computed, not reproduced

The sample confidence values (0.95, 0.89, …) are author-chosen illustrations; a
deterministic engine cannot reproduce arbitrary numbers. The engine emits
confidence **directionally** — high for clear deterministic outcomes, low (0.65)
for manual review. Tests assert decisions and amounts exactly, and confidence by
direction.

## 10. Not modelled (out of scope for this dataset)

Annual-limit accumulation (no year-to-date data is provided per claim),
duplicate detection across submissions, and OCR legibility scoring are designed
for but not exercised by these ten cases. They are layered in separately.
