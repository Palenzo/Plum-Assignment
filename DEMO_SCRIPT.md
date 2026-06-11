# Demo Video Script — OPD Claim Adjudication Tool

**Target length:** 7–8 min (assignment allows 5–10). **Format:** screen recording + voiceover.

## Pre-flight checklist (do this before you hit record)
- [ ] Warm the Render app first (open the URL once so the free-tier cold start is over).
- [ ] Have these tabs ready: **the app**, **`/admin`**, **`/review`**, **`/docs`** (FastAPI), and the **Temporal UI** (`localhost:8233`) if showing durability locally.
- [ ] Have your editor open to **`backend/app/engine.py`** and **`backend/app/review.py`** for the 20-second code peek.
- [ ] Run `python eval.py` once in a terminal so the **10/10** output is on screen, ready to show.
- [ ] Close noisy notifications; record at 1080p.

---

## [0:00–0:30] — Hook + the one idea

**SHOW:** The app's submit screen (clean, idle "Your decision will appear here").

**SAY:**
> "This is an AI tool that adjudicates OPD insurance claims — it reads a member's
> bill and prescription and decides whether to approve, reject, partially approve,
> or send it to a human. The core design choice is this: **the AI reads and reasons,
> but a deterministic rule engine makes the money decision, and a human handles
> anything unclear.** That's what makes every decision reproducible and explainable —
> which matters when you have to defend a claim to a regulator."

---

## [0:30–1:45] — Technical approach (architecture)

**SHOW:** Scroll the README architecture diagram (or the decision-flow chart).

**SAY:**
> "Here's the flow. A claim comes in through a Next.js front end to a FastAPI back end.
> Cheap gates run first — missing documents, below-minimum, duplicates — at zero AI cost.
> Then OCR and an LLM extract structured fields. The extracted data goes into a
> five-step policy engine — eligibility, documents, coverage, limits, settlement —
> written in plain Python, so it decides the exact same way every time. Finally an
> AI review team checks medical necessity and fraud; if it's worried, the claim is
> escalated to a human review queue. The LLM can flag and escalate — it can never
> approve a claim or change an amount."

> "It's built on Next.js, FastAPI, open-source Llama 3.3 via Groq and the Agno agent
> framework, Tesseract for OCR, and every claim runs as a durable Temporal workflow."

---

## [1:45–5:00] — Live demo: four claims (the heart of the video)

> Use the one-click **sample buttons** on the submit panel. Each runs in seconds.

### Case 1 — Straightforward approval  [~40s]
**SHOW:** Click **"Consultation"** sample → submit.
**SAY:**
> "First, a simple consultation — Rajesh Kumar, ₹1,500 for a viral fever. It's
> approved for **₹1,350** — the engine applied the 10% co-pay, so ₹150 came off.
> Notice the **confidence meter** and the **decision card** showing the amount, the
> reason, and the deductions."

### Case 2 — Partial approval (the nuance)  [~50s]
**SHOW:** Click **"Dental + cosmetic"** → submit.
**SAY:**
> "Now a dental claim — a ₹12,000 bill with a root canal *and* teeth whitening. The
> system doesn't reject the whole thing — it **partially approves**: ₹8,000 for the
> root canal, and it strips the ₹4,000 whitening as a cosmetic procedure. This
> line-item reasoning is exactly the kind of nuance a claims team does by hand today."

### Case 3 — Rejection with a clear reason + audit trail  [~50s]
**SHOW:** Click **"Over limit"** → submit. Then expand the **audit trail / explain** panel.
**SAY:**
> "Here's a rejection — a ₹7,500 claim that exceeds the ₹5,000 per-claim limit. The
> decision is **rejected** with the reason `PER_CLAIM_EXCEEDED`, plain-English notes,
> and next steps. And critically — open the **audit trail** — you can see *every rule
> the engine checked* to get here. Nothing is a black box; the explanation can even
> cite the specific policy clause."

### Case 4 — Fraud → human-in-the-loop (the star feature)  [~55s]
**SHOW:** Submit the fraud case via JSON (Ravi Menon, `previous_claims_same_day: 3`,
₹4,800 — see note below). Decision = **MANUAL_REVIEW**. Then go to **`/review`**,
open the claim, click **Approve** as the officer.
**SAY:**
> "Last one — a member submitting his fourth claim the same day. The system doesn't
> guess: it flags the pattern and routes it to **MANUAL_REVIEW**. Over in the review
> queue, a claims officer sees the flags and makes the final call — I'll approve it.
> That's the human-in-the-loop: the AI escalates, the human decides, and the whole
> thing is recorded."

> **Note:** the four sample buttons cover approve/partial/reject/network. For the
> manual-review case, paste TC008 into the JSON submit box, or add it as a 5th sample
> first so it's one click. (Optional: also show **"Network cashless"** → approved
> ₹3,600 with a ₹900 network discount if you want a fifth quick win.)

---

## [5:00–6:15] — Under the hood (proof it's solid)

**SHOW:** Split between the terminal (`eval.py` output) and the code.

**SAY:**
> "A few things that make this production-minded. One — **accuracy**: I run an eval
> harness against all ten provided test cases, and it's at **100% on both the decision
> and the rupee amount.** [show the 10/10 terminal output]"

> "Two — the **engine is deterministic** [show engine.py briefly]: ordered rules,
> first match wins, every step recorded. Three — the **AI review is advisory and
> fail-open** [show review.py]: it can only make the engine *more* cautious, and if
> the LLM is down, the claim still gets a decision."

**SHOW:** Quickly open **`/admin`**.
**SAY:**
> "There's also an **admin dashboard** to edit policy limits and exclusions live
> without redeploying, and an upload path where OCR plus the LLM read a real photo of
> a prescription."

*(Optional, ~15s — if showing durability locally):* **SHOW** Temporal UI at `:8233`.
> "And every claim runs as a durable Temporal workflow — retryable and crash-safe.
> Here it is in the Temporal UI."

---

## [6:15–7:30] — Improvements + close

**SAY:**
> "Where I'd take this next: calibrated confidence scores instead of directional ones;
> RAG over the full policy document so explanations cite exact clauses for any rule;
> handling handwritten and regional-language prescriptions; and a proper analytics
> dashboard on approval rates and escalation reasons. For production I'd move from
> SQLite to Postgres and run the Temporal worker against Temporal Cloud."

> "But the foundation is the part I care most about: **the AI reads, deterministic
> rules decide, and a human handles the edge cases** — accurate, reproducible, and
> explainable end to end. Thanks for watching."

---

## Delivery tips
- Speak to the **decision**, not the UI ("it's approved for ₹1,350 after co-pay," not "I click here").
- Keep each claim under a minute — the samples run in seconds, so don't pad.
- If the live Render site is slow, record the demo against `localhost` and only *show* the live URL once.
- Say the numbers out loud (₹1,350, ₹8,000, ₹900 discount) — it proves the money math works.
