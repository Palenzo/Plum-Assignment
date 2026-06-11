# Product

## Register

product

## Users

Two audiences share one system, with the submission experience leading:

- **Claimants** — employees at Plum-covered companies submitting an OPD reimbursement after a doctor visit. Context: at home or on mobile, often anxious about whether a medical bill will be covered. They want a fast, clear yes/no, the money figure, and a reason they can actually understand. Low patience for insurance jargon.
- **Claims officers** at Plum who review only the edge cases the system routes to them (fraud flags, high-value, low-confidence). Context: working a queue; they need the system's reasoning and audit trail at a glance to confirm or override.

Job to be done: turn a pile of medical documents into a trustworthy approve/reject decision — with the money and the *why* — in seconds instead of days.

## Product Purpose

Automate OPD insurance claim adjudication. A claimant submits bills and prescriptions (images, PDFs, or structured data); the system extracts the facts, checks them against policy rules, and returns a decision — approved / partial / rejected / manual review — with the approved amount, the reasoning, and a confidence score. Success = a decision a human trusts without redoing the work, and a claimant who understands the outcome without calling support.

## Brand Personality

Human and reassuring healthtech. Calm, plain-spoken, and competent — the voice of someone who handles your medical claim with care and tells you straight. Three words: **reassuring, clear, trustworthy**. The interface should lower anxiety: no jargon walls, no bureaucratic dread, no false cheer. Warmth comes from language, space, and pacing — never from cuteness.

## Anti-references

Explicitly NOT any of these:

- **Generic AI SaaS dashboard** — cream/sand backgrounds, identical icon-heading-text card grids, gradient-text headings, tiny uppercase tracked eyebrows. The default AI tell.
- **Legacy insurance / government portal** — dense gray tables, bureaucratic clutter, no hierarchy. The dread we are replacing.
- **Playful consumer app** — bright, emoji-heavy, over-rounded, casual. Medical claims and money are not a game.
- **Crypto / dark-neon dashboard** — black backgrounds, neon glows, terminal cosplay. Style over substance.

Warmth without cuteness; seriousness without coldness. That narrow band is the brief.

## Design Principles

1. **The decision is the product.** Verdict, amount, and reason are the hero on every claim — never buried under chrome. One glance answers "what happened and why".
2. **Explain, don't assert.** Every decision shows its reasoning and confidence. Trust is earned by showing the work (the audit trail), not by a badge.
3. **Lower the anxiety.** Plain language over policy-speak. A rejection states the human reason and the next step, not just a code.
4. **Calm under data.** Dense information — amounts, deductions, rules — presented with hierarchy and restraint, so it reads as clarity, not clutter.
5. **Honest about uncertainty.** When the system is unsure, it says so and routes to a human — visibly, not silently.

## Accessibility & Inclusion

WCAG 2.1 AA. Body text ≥4.5:1 contrast (no light-gray-on-tint). Full keyboard operability for the submission form and dashboard. Every status communicated by text and icon, not color alone — critical for the verdict states, and color-blind safe. Respect `prefers-reduced-motion` with crossfade/instant fallbacks for all motion.
