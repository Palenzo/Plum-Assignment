"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type State = "checking" | "waking" | "ready" | "down";

// Retry through a free-tier cold start (~50s) before giving up.
const MAX_ATTEMPTS = 12;
const RETRY_MS = 5000;

const VIEW: Record<State, { color: string; label: string; pulse: boolean }> = {
  checking: { color: "text-ink-muted", label: "Checking…", pulse: true },
  waking: { color: "text-warn", label: "Waking up…", pulse: true },
  ready: { color: "text-ok", label: "Backend ready", pulse: false },
  down: { color: "text-bad", label: "Backend offline", pulse: false },
};

/**
 * Header badge that pings GET /api/status on mount — this both reports backend
 * readiness and warms a spun-down free-tier instance while the user reads the
 * page, so the first real request doesn't eat the cold start. Retries silently
 * through the cold start, showing "Waking up…", then "Backend ready".
 */
export function BackendStatusBadge() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll(attempt: number) {
      try {
        await api.status();
        if (!cancelled) setState("ready");
      } catch {
        if (cancelled) return;
        if (attempt + 1 >= MAX_ATTEMPTS) {
          setState("down");
          return;
        }
        setState("waking");
        timer = setTimeout(() => poll(attempt + 1), RETRY_MS);
      }
    }

    poll(0);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const v = VIEW[state];
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs ${v.color}`}
      title="Backend service status"
      aria-live="polite"
    >
      <span className={`h-2 w-2 rounded-full bg-current ${v.pulse ? "animate-pulse" : ""}`} />
      <span className="hidden sm:inline">{v.label}</span>
    </span>
  );
}
