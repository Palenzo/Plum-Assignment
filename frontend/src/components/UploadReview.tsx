"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import type { ExtractedDocument, ReviewMeta } from "@/lib/types";
import { Check, FileText, Sparkles } from "./icons";

/**
 * Pre-submit review: shows the claim details and the attached documents large,
 * and (on demand) the OCR + LLM extraction so the user can confirm the engine
 * read the documents correctly before anything is submitted.
 */
export function UploadReview({
  meta,
  prescription,
  bill,
  busy,
  onBack,
  onConfirm,
}: {
  meta: ReviewMeta;
  prescription: File;
  bill: File | null;
  busy: boolean;
  onBack: () => void;
  onConfirm: (extracted: ExtractedDocument | null) => void;
}) {
  const [extracted, setExtracted] = useState<ExtractedDocument | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState("");

  const amountNum = Number(meta.amount);
  const fields: [string, string][] = [
    ["Member ID", meta.memberId],
    ["Member name", meta.name || "Member"],
    ["Treatment date", formatDate(meta.date)],
    ["Claim amount", Number.isFinite(amountNum) ? inr(amountNum) : meta.amount],
  ];

  async function verify() {
    setVerifying(true);
    setVerifyError("");
    try {
      const form = new FormData();
      form.append("prescription", prescription);
      if (bill) form.append("bill", bill);
      setExtracted(await api.extractDocuments(form));
    } catch (e) {
      setVerifyError(e instanceof Error ? e.message : "Could not read the documents.");
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-primary-soft">
          <Check className="h-4 w-4 text-primary" />
        </span>
        <h1 className="font-display text-2xl font-medium text-ink">Review before submitting</h1>
      </div>
      <p className="mt-1.5 text-sm text-ink-muted">
        Check the details and documents — nothing is sent until you confirm.
      </p>

      <dl className="mt-6 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-ink-faint">{label}</dt>
            <dd className="mt-0.5 text-sm font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="space-y-4">
          <h2 className="text-sm font-medium text-ink">Documents</h2>
          <FilePreview label="Prescription" file={prescription} />
          {bill && <FilePreview label="Bill" file={bill} />}
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium text-ink">What OCR reads</h2>
            <button
              onClick={verify}
              disabled={verifying || busy}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:border-primary disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4 text-primary" />
              {verifying ? "Reading…" : extracted ? "Re-check" : "Verify with OCR"}
            </button>
          </div>
          <OcrPanel extracted={extracted} verifying={verifying} error={verifyError} />
        </section>
      </div>

      <div className="mt-8 flex justify-end gap-3">
        <button
          onClick={onBack}
          disabled={busy}
          className="rounded-md border border-border px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary disabled:opacity-50"
        >
          Back to edit
        </button>
        <button
          onClick={() => onConfirm(extracted)}
          disabled={busy}
          className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover disabled:opacity-50"
        >
          {busy ? "Adjudicating…" : "Confirm & submit"}
        </button>
      </div>
    </div>
  );
}

function OcrPanel({
  extracted,
  verifying,
  error,
}: {
  extracted: ExtractedDocument | null;
  verifying: boolean;
  error: string;
}) {
  if (verifying) {
    return <div className="h-48 animate-pulse rounded-lg border border-border bg-surface" />;
  }
  if (error) {
    return <p className="rounded-lg bg-bad-bg px-4 py-3 text-sm text-bad">{error}</p>;
  }
  if (!extracted) {
    return (
      <div className="rounded-lg border border-dashed border-border p-6 text-sm text-ink-muted">
        Run the OCR check to see what the engine will read from these documents, and confirm it
        matches what you submitted.
      </div>
    );
  }

  const rows: [string, string][] = [
    ["Doctor", [extracted.doctor_name, extracted.doctor_reg].filter(Boolean).join(" · ") || "—"],
    ["Diagnosis", extracted.diagnosis || "—"],
    ["Treatment", extracted.treatment || "—"],
  ];

  return (
    <div className="space-y-4 rounded-lg border border-border bg-bg p-4">
      <dl className="space-y-2.5">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[7rem_1fr] gap-2">
            <dt className="text-xs text-ink-faint">{label}</dt>
            <dd className="text-sm text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      {extracted.line_items.length > 0 && (
        <div>
          <p className="text-xs text-ink-faint">Bill items</p>
          <ul className="mt-1.5 divide-y divide-border rounded-md border border-border">
            {extracted.line_items.map((li, i) => (
              <li
                key={`${li.name}-${i}`}
                className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
              >
                <span className="text-ink">{li.name}</span>
                <span className="tnum text-ink-muted">{inr(li.amount)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Chips label="Medicines" items={extracted.medicines} />
      <Chips label="Procedures" items={extracted.procedures} />
      <Chips label="Tests" items={extracted.tests} />
    </div>
  );
}

function Chips({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="text-xs text-ink-faint">{label}</p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {items.map((it, i) => (
          <span key={`${it}-${i}`} className="rounded-full bg-surface px-2.5 py-1 text-xs text-ink-muted">
            {it}
          </span>
        ))}
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
          <img src={url} alt={`${label} preview`} className="max-h-[32rem] w-full bg-surface object-contain" />
        ) : (
          <iframe src={url} title={`${label} preview`} className="h-[32rem] w-full bg-surface" />
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
