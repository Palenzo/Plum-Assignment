"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { PolicyDoc } from "@/lib/types";

const CATEGORIES = [
  { key: "consultation_fees", label: "Consultation" },
  { key: "diagnostic_tests", label: "Diagnostic tests" },
  { key: "pharmacy", label: "Pharmacy" },
  { key: "dental", label: "Dental" },
  { key: "vision", label: "Vision" },
  { key: "alternative_medicine", label: "Alternative medicine" },
];

type Status = "idle" | "saving" | "saved" | "error";

export default function AdminPage() {
  const [token, setToken] = useState<string | null>(null);
  const [policy, setPolicy] = useState<PolicyDoc | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");

  // Restore a previously verified session (cleared when the tab closes).
  useEffect(() => {
    const saved = sessionStorage.getItem("admin_token");
    if (saved) setToken(saved);
  }, []);

  // Load the policy only once the password has been verified.
  useEffect(() => {
    if (!token) return;
    api.getPolicy().then(setPolicy).catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [token]);

  if (!token) return <LoginGate onAuthed={(t) => { sessionStorage.setItem("admin_token", t); setToken(t); }} />;

  function update(mutate: (p: PolicyDoc) => void) {
    setPolicy((prev) => {
      if (!prev) return prev;
      const next = structuredClone(prev);
      mutate(next);
      return next;
    });
    setStatus("idle");
  }

  async function save() {
    if (!policy || !token) return;
    setStatus("saving");
    try {
      await api.updatePolicy(policy, token);
      setStatus("saved");
    } catch (e) {
      // A 401 here means the session is no longer valid — send them back to login.
      const message = e instanceof Error ? e.message : "Save failed";
      if (message.toLowerCase().includes("admin password")) {
        sessionStorage.removeItem("admin_token");
        setToken(null);
        return;
      }
      setError(message);
      setStatus("error");
    }
  }

  if (error && !policy) return <p className="rounded-lg bg-bad-bg px-4 py-3 text-sm text-bad">{error}</p>;
  if (!policy) return <div className="h-40 animate-pulse rounded-2xl border border-border bg-surface" />;

  const cov = policy.coverage_details;

  return (
    <div>
      <h1 className="text-3xl">Policy administration</h1>
      <p className="mt-2 text-ink-muted">Edit coverage limits and exclusions. Changes apply immediately to new claims.</p>

      <section className="mt-8 rounded-2xl border border-border p-5 sm:p-6">
        <h2 className="text-lg">Overall limits</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Field label="Annual limit" value={cov.annual_limit} onChange={(v) => update((p) => { p.coverage_details.annual_limit = v; })} />
          <Field label="Per-claim limit" value={cov.per_claim_limit} onChange={(v) => update((p) => { p.coverage_details.per_claim_limit = v; })} />
          <Field label="Family floater" value={cov.family_floater_limit} onChange={(v) => update((p) => { p.coverage_details.family_floater_limit = v; })} />
        </div>
      </section>

      <section className="mt-5 rounded-2xl border border-border p-5 sm:p-6">
        <h2 className="text-lg">Category sub-limits</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {CATEGORIES.map((c) => {
            const cat = cov[c.key] as { sub_limit?: number } | undefined;
            if (!cat || typeof cat.sub_limit !== "number") return null;
            return (
              <Field
                key={c.key}
                label={c.label}
                value={cat.sub_limit}
                onChange={(v) => update((p) => { (p.coverage_details[c.key] as { sub_limit: number }).sub_limit = v; })}
              />
            );
          })}
        </div>
      </section>

      <section className="mt-5 rounded-2xl border border-border p-5 sm:p-6">
        <h2 className="text-lg">Exclusions</h2>
        <p className="mt-1 text-sm text-ink-muted">One per line. These conditions are never covered.</p>
        <textarea
          value={policy.exclusions.join("\n")}
          onChange={(e) => update((p) => { p.exclusions = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean); })}
          rows={8}
          className="mt-3 w-full rounded-md border border-border bg-bg px-3 py-2 font-mono text-sm text-ink focus:border-primary focus-visible:outline-none"
        />
      </section>

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={save}
          disabled={status === "saving"}
          className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover disabled:opacity-50"
        >
          {status === "saving" ? "Saving…" : "Save policy"}
        </button>
        {status === "saved" && <span className="text-sm text-ok">Saved ✓</span>}
        {status === "error" && <span className="text-sm text-bad">{error}</span>}
      </div>
    </div>
  );
}

function LoginGate({ onAuthed }: { onAuthed: (token: string) => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.adminLogin(password);
      onAuthed(password);
    } catch {
      setError("Incorrect password");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <h1 className="text-3xl">Policy administration</h1>
      <p className="mt-2 text-ink-muted">Enter the admin password to manage coverage limits and exclusions.</p>
      <form onSubmit={submit} className="mt-6 space-y-3">
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Admin password"
          className="w-full rounded-md border border-border bg-bg px-3 py-2.5 text-sm text-ink focus:border-primary focus-visible:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !password}
          className="w-full rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover disabled:opacity-50"
        >
          {busy ? "Checking…" : "Unlock"}
        </button>
        {error && <p className="text-sm text-bad">{error}</p>}
      </form>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>
      <div className="flex items-center rounded-md border border-border bg-bg focus-within:border-primary">
        <span className="pl-3 text-sm text-ink-faint">₹</span>
        <input
          type="number"
          min="0"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="tnum w-full bg-transparent px-2 py-2 text-sm text-ink focus-visible:outline-none"
        />
      </div>
    </label>
  );
}
