"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Decision } from "@/lib/types";

export function ReviewPanel({ claimId, onResolved }: { claimId: string; onResolved: (d: Decision) => void }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function act(action: "approve" | "reject") {
    setBusy(true);
    setError("");
    try {
      onResolved(await api.resolveClaim(claimId, action, note));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save the decision");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <p className="font-display text-lg font-medium">Claims officer review</p>
      <p className="mt-1 text-sm text-ink-muted">
        The AI flagged this for a human decision. Approve to reimburse, or reject.
      </p>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        placeholder="Add a note (optional)"
        className="mt-4 w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-primary focus-visible:outline-none"
      />
      <div className="mt-3 flex gap-3">
        <button
          disabled={busy}
          onClick={() => act("approve")}
          className="flex-1 rounded-md bg-ok px-4 py-2.5 text-sm font-medium text-primary-ink transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          disabled={busy}
          onClick={() => act("reject")}
          className="flex-1 rounded-md border border-bad px-4 py-2.5 text-sm font-medium text-bad transition-colors hover:bg-bad-bg disabled:opacity-50"
        >
          Reject
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-bad">{error}</p>}
    </div>
  );
}
