"use client";

import { useEffect, useState } from "react";
import { Check } from "./icons";

const STEPS = [
  "Reading the documents",
  "Extracting the details",
  "Checking coverage",
  "Applying the policy rules",
  "Reaching a decision",
];

export function ProcessingStepper() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setActive((a) => Math.min(a + 1, STEPS.length - 1)), 650);
    return () => clearInterval(id);
  }, []);

  return (
    <ol className="space-y-3.5">
      {STEPS.map((step, i) => {
        const done = i < active;
        const current = i === active;
        return (
          <li key={step} className="flex items-center gap-3">
            <span
              className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border transition-colors ${
                done
                  ? "border-primary bg-primary text-primary-ink"
                  : current
                    ? "border-primary text-primary"
                    : "border-border"
              }`}
            >
              {done ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <span className={`h-1.5 w-1.5 rounded-full ${current ? "animate-pulse bg-primary" : "bg-border-strong"}`} />
              )}
            </span>
            <span className={`text-sm ${done || current ? "text-ink" : "text-ink-faint"}`}>{step}</span>
          </li>
        );
      })}
    </ol>
  );
}
