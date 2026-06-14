import type { Verdict } from "./types";

export const VERDICT: Record<Verdict, { label: string; tone: Tone; blurb: string }> = {
  APPROVED: { label: "Approved", tone: "ok", blurb: "This claim is covered and will be reimbursed." },
  PARTIAL: { label: "Partially approved", tone: "warn", blurb: "Part of this claim is covered; the rest isn't." },
  REJECTED: { label: "Not approved", tone: "bad", blurb: "This claim can't be reimbursed under the policy." },
  MANUAL_REVIEW: { label: "Manual review", tone: "info", blurb: "A claims officer will take a closer look." },
};

export type Tone = "ok" | "warn" | "bad" | "info";

// Safe accessor: never returns undefined, so an unexpected decision string from
// the API degrades to a readable label instead of crashing the page.
export const verdictMeta = (v: Verdict) =>
  VERDICT[v] ?? { label: String(v).replace(/_/g, " "), tone: "info" as Tone, blurb: "" };

// Literal class strings so Tailwind's scanner includes them.
export const TONE_CLASS: Record<Tone, { text: string; bg: string; fill: string }> = {
  ok: { text: "text-ok", bg: "bg-ok-bg", fill: "bg-ok" },
  warn: { text: "text-warn", bg: "bg-warn-bg", fill: "bg-warn" },
  bad: { text: "text-bad", bg: "bg-bad-bg", fill: "bg-bad" },
  info: { text: "text-info", bg: "bg-info-bg", fill: "bg-info" },
};

// Human labels for the engine's rejection codes.
export const REASON_LABEL: Record<string, string> = {
  WAITING_PERIOD: "Within the waiting period",
  MISSING_DOCUMENTS: "Required documents missing",
  DOCTOR_REG_INVALID: "Doctor registration invalid",
  SERVICE_NOT_COVERED: "Service not covered",
  EXCLUDED_CONDITION: "Excluded condition",
  PRE_AUTH_MISSING: "Pre-authorisation missing",
  PER_CLAIM_EXCEEDED: "Exceeds per-claim limit",
  SUB_LIMIT_EXCEEDED: "Exceeds category sub-limit",
  ANNUAL_LIMIT_EXCEEDED: "Annual limit reached",
  BELOW_MIN_AMOUNT: "Below minimum claim amount",
  DUPLICATE_CLAIM: "Duplicate of an earlier claim",
  NOT_MEDICALLY_NECESSARY: "Not medically necessary",
};

export const reasonLabel = (code: string) =>
  REASON_LABEL[code] ?? code.replace(/_/g, " ").toLowerCase();
