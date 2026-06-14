"use client";

import { useEffect, useState } from "react";
import { inr } from "@/lib/format";
import { Check, FileText } from "./icons";

export type ReviewData = {
  memberId: string;
  name: string;
  date: string;
  amount: string;
};

/**
 * Pre-submit review: shows the claim details and the attached documents so the
 * user can verify everything before anything is sent to the backend. Purely
 * presentational — it builds nothing and calls onConfirm/onBack.
 */
export function UploadReview({
  data,
  prescription,
  bill,
  busy,
  onBack,
  onConfirm,
}: {
  data: ReviewData;
  prescription: File;
  bill: File | null;
  busy: boolean;
  onBack: () => void;
  onConfirm: () => void;
}) {
  const amountNum = Number(data.amount);
  const fields: [string, string][] = [
    ["Member ID", data.memberId],
    ["Member name", data.name || "Member"],
    ["Treatment date", formatDate(data.date)],
    ["Claim amount", Number.isFinite(amountNum) ? inr(amountNum) : data.amount],
  ];

  return (
    <div className="rounded-2xl border border-border bg-bg p-5 sm:p-6">
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-primary-soft">
          <Check className="h-4 w-4 text-primary" />
        </span>
        <h2 className="font-display text-lg font-medium text-ink">Review before submitting</h2>
      </div>
      <p className="mt-1.5 text-sm text-ink-muted">
        Check the details and documents below — nothing is sent until you confirm.
      </p>

      <dl className="mt-5 grid grid-cols-2 gap-x-4 gap-y-3">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-ink-faint">{label}</dt>
            <dd className="mt-0.5 text-sm font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-5 space-y-3">
        <FilePreview label="Prescription" file={prescription} />
        {bill && <FilePreview label="Bill" file={bill} />}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={onBack}
          disabled={busy}
          className="flex-1 rounded-md border border-border px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary disabled:opacity-50"
        >
          Back to edit
        </button>
        <button
          onClick={onConfirm}
          disabled={busy}
          className="flex-1 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover disabled:opacity-50"
        >
          {busy ? "Adjudicating…" : "Confirm & submit"}
        </button>
      </div>
    </div>
  );
}

function FilePreview({ label, file }: { label: string; file: File }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    // Object URLs are revoked on unmount / file change so blobs aren't leaked.
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  const isImage = file.type.startsWith("image/");

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="flex items-center gap-2 border-b border-border bg-surface px-3 py-2">
        <FileText className="h-4 w-4 shrink-0 text-ink-muted" />
        <span className="shrink-0 text-sm font-medium text-ink">{label}</span>
        <span className="truncate text-xs text-ink-faint">{file.name}</span>
      </div>
      {url &&
        (isImage ? (
          // Blob preview from an object URL — next/image can't optimise these.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={`${label} preview`} className="max-h-80 w-full bg-surface object-contain" />
        ) : (
          <iframe src={url} title={`${label} preview`} className="h-80 w-full bg-surface" />
        ))}
    </div>
  );
}

function formatDate(iso: string): string {
  // iso is yyyy-mm-dd from <input type="date">. Parse by hand (no Date()) to
  // avoid the timezone shift that would move the date by a day.
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const [, y, mo, d] = m;
  return `${Number(d)} ${months[Number(mo) - 1]} ${y}`;
}
