"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { ClaimInput, Decision } from "@/lib/types";
import { DecisionCard } from "@/components/DecisionCard";
import { ProcessingStepper } from "@/components/ProcessingStepper";
import { SubmitPanel } from "@/components/SubmitPanel";
import { Shield } from "@/components/icons";

type Status = "idle" | "processing" | "done" | "error";
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Home() {
  const [status, setStatus] = useState<Status>("idle");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState("");

  async function run(work: () => Promise<Decision>) {
    setStatus("processing");
    setError("");
    setDecision(null);
    try {
      const [result] = await Promise.all([work(), delay(1700)]);
      setDecision(result);
      setStatus("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setStatus("error");
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">
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
            onUpload={(form) => run(() => api.submitUpload(form))}
          />
        </div>
      </section>

      <section aria-live="polite" className="lg:pt-1">
        {status === "idle" && <EmptyState />}
        {status === "processing" && (
          <div className="rounded-2xl border border-border p-6 sm:p-8">
            <p className="font-display text-lg font-medium">Working through your claim</p>
            <div className="mt-5">
              <ProcessingStepper />
            </div>
          </div>
        )}
        {status === "done" && decision && <DecisionCard decision={decision} />}
        {status === "error" && <ErrorState message={error} />}
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full min-h-72 flex-col items-start justify-center rounded-2xl border border-dashed border-border p-8">
      <Shield className="h-7 w-7 text-primary" />
      <p className="mt-4 font-display text-lg font-medium">Your decision will appear here</p>
      <p className="mt-1.5 max-w-xs text-sm text-ink-muted">
        The AI reads your documents; a deterministic policy engine makes the call — and shows its working.
      </p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-border bg-bad-bg p-6 sm:p-8">
      <p className="font-display text-lg font-medium text-bad">We couldn&apos;t process that</p>
      <p className="mt-2 text-sm text-ink-muted">{message}</p>
      <p className="mt-3 text-sm text-ink-faint">Check that the backend is running on its configured port, then try again.</p>
    </div>
  );
}
