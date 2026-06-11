"use client";

import { useEffect, useState } from "react";
import { pct } from "@/lib/format";

export function ConfidenceMeter({ score }: { score: number }) {
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
    </div>
  );
}
