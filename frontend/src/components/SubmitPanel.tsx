"use client";

import { useState } from "react";
import type { ClaimInput, ReviewPayload } from "@/lib/types";
import { SAMPLES } from "@/lib/samples";
import { FileText, Sparkles, Upload } from "./icons";

type Mode = "sample" | "upload";

const inputClass =
  "w-full rounded-md border border-border bg-bg px-3 py-2 text-sm text-ink placeholder:text-ink-faint transition-colors focus:border-primary focus-visible:outline-none";
const labelClass = "mb-1.5 block text-sm font-medium text-ink";

export function SubmitPanel({
  busy,
  onJson,
  onReview,
}: {
  busy: boolean;
  onJson: (claim: ClaimInput) => void;
  onReview: (payload: ReviewPayload) => void;
}) {
  const [mode, setMode] = useState<Mode>("sample");
  const [memberId, setMemberId] = useState("EMP001");
  const [name, setName] = useState("");
  const [date, setDate] = useState("2024-11-01");
  const [amount, setAmount] = useState("1500");
  const [rx, setRx] = useState<File | null>(null);
  const [bill, setBill] = useState<File | null>(null);

  // Uploading is a two-step flow: submitting the form hands the entered data and
  // files up to the page, which shows a full-width review before anything is sent.
  function submitUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!rx) return;
    onReview({ meta: { memberId, name, date, amount }, prescription: rx, bill });
  }

  return (
    <div className="rounded-2xl border border-border bg-bg p-5 sm:p-6">
      <div className="grid grid-cols-2 gap-1 rounded-lg bg-surface p-1">
        {([["sample", "Run a sample", Sparkles], ["upload", "Upload documents", Upload]] as const).map(
          ([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                mode === id ? "bg-bg text-ink shadow-sm" : "text-ink-muted hover:text-ink"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ),
        )}
      </div>

      {mode === "sample" ? (
        <div className="mt-5">
          <p className="text-sm text-ink-muted">Pick a scenario to adjudicate instantly.</p>
          <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
            {SAMPLES.map((s) => (
              <button
                key={s.label}
                disabled={busy}
                onClick={() => onJson(s.claim)}
                className="rounded-lg border border-border p-3 text-left transition-colors hover:border-primary hover:bg-primary-soft disabled:opacity-50"
              >
                <span className="block text-sm font-medium text-ink">{s.label}</span>
                <span className="mt-0.5 block text-xs text-ink-muted">{s.hint}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <form onSubmit={submitUpload} className="mt-5 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>Member ID</label>
              <input className={inputClass} value={memberId} onChange={(e) => setMemberId(e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>Member name</label>
              <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" />
            </div>
            <div>
              <label className={labelClass}>Treatment date</label>
              <input type="date" className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>Claim amount (₹)</label>
              <input type="number" min="0" className={inputClass} value={amount} onChange={(e) => setAmount(e.target.value)} required />
            </div>
          </div>
          <FileField label="Prescription" file={rx} onPick={setRx} />
          <FileField label="Bill (optional)" file={bill} onPick={setBill} />
          <button
            type="submit"
            disabled={busy || !rx}
            className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover disabled:opacity-50"
          >
            {busy ? "Adjudicating…" : "Review claim"}
          </button>
        </form>
      )}
    </div>
  );
}

function FileField({ label, file, onPick }: { label: string; file: File | null; onPick: (f: File) => void }) {
  const [drag, setDrag] = useState(false);
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <label
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) onPick(f); }}
        className={`flex cursor-pointer items-center gap-3 rounded-lg border border-dashed px-4 py-3 transition-colors ${
          drag ? "border-primary bg-primary-soft" : "border-border-strong hover:border-primary"
        }`}
      >
        <FileText className="h-5 w-5 shrink-0 text-ink-muted" />
        <span className="truncate text-sm text-ink-muted">{file ? file.name : "Drag a file here, or click to choose"}</span>
        <input
          type="file"
          accept="image/*,.pdf"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onPick(f); }}
        />
      </label>
    </div>
  );
}
