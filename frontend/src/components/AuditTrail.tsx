"use client";

import { useState } from "react";
import type { AuditEntry } from "@/lib/types";
import { Check, Chevron, Cross } from "./icons";

export function AuditTrail({ entries }: { entries: AuditEntry[] }) {
  const [open, setOpen] = useState(false);
  if (!entries?.length) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-surface"
      >
        <span className="text-sm font-medium text-ink">
          How this was decided <span className="text-ink-faint">· {entries.length} checks</span>
        </span>
        <Chevron className={`h-4 w-4 text-ink-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ol className="border-t border-border">
          {entries.map((entry, i) => (
            <li key={i} className="flex items-center gap-3 border-b border-border px-4 py-2.5 last:border-b-0">
              {entry.passed ? (
                <Check className="h-4 w-4 shrink-0 text-ok" />
              ) : (
                <Cross className="h-4 w-4 shrink-0 text-bad" />
              )}
              <span className="text-sm capitalize text-ink">{entry.step}</span>
              <span className="text-sm text-ink-faint">· {entry.rule.replace(/_/g, " ")}</span>
              {entry.detail && <span className="tnum ml-auto text-xs text-ink-faint">{entry.detail}</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
