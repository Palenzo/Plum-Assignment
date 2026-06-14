"use client";

import { useEffect, useState } from "react";
import { pct } from "@/lib/format";
import type { ConfidenceFactor } from "@/lib/types";

export function ConfidenceMeter({
  score,
  factors = [],
}: {
  score: number;
  factors?: ConfidenceFactor[];
}) {
  const [width, setWidth] = useState(0);
  const low = score < 0.8;

  useEffect(() => {
    const id = requestAnimationFrame(() => setWidth(score));
    return () => cancelAnimationFrame(id);
  }, [score]);

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-ink-muted">Confidence</span>
        <span className="tnum text-sm font-medium text-ink">{pct(score)}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-border">
        <div
          className={`h-full rounded-full ${low ? "bg-info" : "bg-primary"}`}
          style={{ width: `${width * 100}%`, transition: "width 0.9s var(--ease-expo)" }}
        />
      </div>
      {low && <p className="mt-2 text-sm text-info">Lower confidence — routed for a human check.</p>}
      {factors.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {factors.slice(0, 4).map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-ink-muted">
              <span
                className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${f.delta < 0 ? "bg-warn" : "bg-ok"}`}
              />
              <span>
                <span className="text-ink">{f.label}</span>
                {f.detail ? ` — ${f.detail}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
