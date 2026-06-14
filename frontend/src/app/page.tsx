"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { ClaimInput, Decision, ExtractedDocument, ReviewMeta, ReviewPayload } from "@/lib/types";
import { DecisionCard } from "@/components/DecisionCard";
import { ProcessingStepper } from "@/components/ProcessingStepper";
import { SubmitPanel } from "@/components/SubmitPanel";
import { UploadReview } from "@/components/UploadReview";
import { Shield } from "@/components/icons";

type Status = "idle" | "processing" | "done" | "error";
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function toForm(r: ReviewPayload): FormData {
  const form = new FormData();
  form.append("member_id", r.meta.memberId);
  form.append("member_name", r.meta.name || "Member");
  form.append("treatment_date", r.meta.date);
  form.append("claim_amount", r.meta.amount);
  form.append("prescription", r.prescription);
  if (r.bill) form.append("bill", r.bill);
  return form;
}

// Map the verified extraction + entered metadata to the engine's JSON input, so
// a verified claim can submit without a second OCR/LLM call (mirrors the
// backend's to_claim_input).
function toClaimInput(meta: ReviewMeta, doc: ExtractedDocument): ClaimInput {
  return {
    member_id: meta.memberId,
    member_name: meta.name || "Member",
    treatment_date: meta.date,
    claim_amount: Number(meta.amount),
    prescription: {
      doctor_name: doc.doctor_name ?? undefined,
      doctor_reg: doc.doctor_reg ?? undefined,
      diagnosis: doc.diagnosis ?? undefined,
      treatment: doc.treatment ?? undefined,
      medicines_prescribed: doc.medicines,
      procedures: doc.procedures,
      tests_prescribed: doc.tests,
    },
    bill: Object.fromEntries(doc.line_items.map((li) => [li.name, li.amount])),
  };
}

export default function Home() {
  const [status, setStatus] = useState<Status>("idle");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState("");
  const [review, setReview] = useState<ReviewPayload | null>(null);

  async function run(work: () => Promise<Decision>) {
    setStatus("processing");
    setError("");
    setDecision(null);
    try {
      const [result] = await Promise.all([work(), delay(1200)]);
      setDecision(result);
      setStatus("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setStatus("error");
    }
  }

  // If the user verified with OCR we already have the extracted data, so submit
  // it as JSON (no second LLM call); otherwise upload the raw documents.
  function confirmReview(extracted: ExtractedDocument | null) {
    if (!review) return;
    const r = review;
    const work = extracted
      ? () => api.submitJson(toClaimInput(r.meta, extracted))
      : () => api.submitUpload(toForm(r));
    setReview(null);
    run(work);
  }

  if (review) {
    return (
      <UploadReview
        meta={review.meta}
        prescription={review.prescription}
        bill={review.bill}
        busy={status === "processing"}
        onBack={() => setReview(null)}
        onConfirm={confirmReview}
      />
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(340px,400px)_minmax(0,1fr)] lg:gap-10">
      <section>
        <h1 className="text-3xl sm:text-4xl">Submit an OPD claim</h1>
        <p className="mt-3 max-w-prose text-ink-muted">
          Upload your bill and prescription, or run a sample. You&apos;ll get a clear decision — with the
          reason and the amount — in seconds.
        </p>
        <div className="mt-6">
          <SubmitPanel
            busy={status === "processing"}
            onJson={(claim: ClaimInput) => run(() => api.submitJson(claim))}
            onReview={(payload) => setReview(payload)}
          />
        </div>
      </section>

      <section aria-live="polite" className="flex rounded-2xl border border-border bg-surface p-5 sm:p-8 lg:min-h-[36rem]">
        <div className="m-auto w-full max-w-xl">
          {status === "idle" && <EmptyState />}
          {status === "processing" && (
            <div className="rounded-2xl border border-border bg-bg p-6 shadow-sm sm:p-8">
              <p className="font-display text-lg font-medium">Working through your claim</p>
              <div className="mt-5">
                <ProcessingStepper />
              </div>
            </div>
          )}
          {status === "done" && decision && <DecisionCard decision={decision} />}
          {status === "error" && <ErrorState message={error} />}
        </div>
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center px-4 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-primary-soft">
        <Shield className="h-6 w-6 text-primary" />
      </span>
      <p className="mt-4 font-display text-lg font-medium">Your decision will appear here</p>
      <p className="mt-1.5 max-w-xs text-sm text-ink-muted">
        The AI reads your documents; a deterministic policy engine makes the call — and shows its working.
      </p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-bad-bg bg-bad-bg p-6 sm:p-8">
      <p className="font-display text-lg font-medium text-bad">We couldn&apos;t process that</p>
      <p className="mt-2 text-sm text-ink-muted">{message}</p>
      <p className="mt-3 text-sm text-ink-faint">Check that the backend is running on its configured port, then try again.</p>
    </div>
  );
}
