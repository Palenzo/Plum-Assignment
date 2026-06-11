"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Explanation } from "@/lib/types";
import { Sparkles } from "./icons";

export function ExplainPanel({ claimId }: { claimId: string }) {
  const [data, setData] = useState<Explanation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setBusy(true);
    setError("");
    try {
      setData(await api.explainClaim(claimId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load");
    } finally {
      setBusy(false);
    }
  }

  if (!data) {
    return (
      <button
        onClick={load}
        disabled={busy}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-ink-muted transition-colors hover:border-primary hover:text-ink disabled:opacity-50"
      >
        <Sparkles className="h-4 w-4 text-primary" />
        {busy ? "Explaining…" : "Explain in plain English"}
        {error && <span className="text-bad">· {error}</span>}
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="flex items-center gap-1.5 text-sm font-medium text-ink">
        <Sparkles className="h-4 w-4 text-primary" /> In plain English
      </p>
      <p className="mt-2 text-sm text-ink-muted">{data.summary}</p>
      {data.citations.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-ink-faint">Based on these policy clauses</p>
          <ul className="mt-1.5 space-y-1">
            {data.citations.map((c, i) => (
              <li key={i} className="flex gap-2 text-xs text-ink-muted">
                <span className="text-primary">§</span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
