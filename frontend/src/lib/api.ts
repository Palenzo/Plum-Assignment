import type { ClaimInput, ClaimsPage, Decision, Explanation, PolicyDoc } from "./types";

// Default: call our own origin and let the Next.js proxy (app/api/[...path])
// forward to the backend at runtime — no CORS, no build-time backend URL.
// Set NEXT_PUBLIC_API_URL only if you want the browser to hit the backend
// directly (then the backend must allow that origin via CORS).
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// Friendly fallbacks for failures that aren't our JSON error envelope — e.g. an
// HTML error page from the host (a Render 502 while the backend is asleep) or an
// empty body. Keyed by status so raw markup never reaches the UI.
const STATUS_MESSAGE: Record<number, string> = {
  502: "The server is unavailable right now — it may be waking up. Please try again in a minute.",
  503: "The server is temporarily unavailable. Please try again shortly.",
  504: "The server took too long to respond. Please try again.",
};

function fallbackMessage(status: number, statusText: string): string {
  return (
    STATUS_MESSAGE[status] ??
    `Request failed (${status || "network error"}${statusText ? ` ${statusText}` : ""}).`
  );
}

async function errorMessage(res: Response): Promise<string> {
  const raw = (await res.text().catch(() => "")).trim();
  // Only trust our own {"error","code"} JSON envelope. An HTML page (starts with
  // "<") or a non-JSON body falls through to a clean status message.
  if (raw && !raw.startsWith("<")) {
    try {
      const body = JSON.parse(raw);
      const msg = body.error ?? body.message ?? body.detail;
      if (msg) return String(msg);
    } catch {
      /* not JSON — use the status fallback below */
    }
  }
  return fallbackMessage(res.status, res.statusText);
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(await errorMessage(res));
  }
  try {
    return (await res.json()) as T;
  } catch {
    // A 2xx that isn't JSON (e.g. an HTML page slipped through the proxy).
    throw new Error(fallbackMessage(res.status || 502, res.statusText));
  }
}

export const api = {
  submitJson: (payload: ClaimInput) =>
    fetch(`${BASE}/api/claims/json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((r) => asJson<Decision>(r)),

  submitUpload: (form: FormData) =>
    fetch(`${BASE}/api/claims`, { method: "POST", body: form }).then((r) => asJson<Decision>(r)),

  listClaims: (
    opts: { limit?: number; offset?: number; status?: string; sort?: string; order?: string } = {},
  ) => {
    const params = new URLSearchParams();
    if (opts.limit != null) params.set("limit", String(opts.limit));
    if (opts.offset != null) params.set("offset", String(opts.offset));
    if (opts.status) params.set("status", opts.status);
    if (opts.sort) params.set("sort", opts.sort);
    if (opts.order) params.set("order", opts.order);
    return fetch(`${BASE}/api/claims?${params}`, { cache: "no-store" }).then((r) => asJson<ClaimsPage>(r));
  },

  getClaim: (id: string) =>
    fetch(`${BASE}/api/claims/${id}`, { cache: "no-store" }).then((r) => asJson<Decision>(r)),

  resolveClaim: (id: string, action: "approve" | "reject", note: string) =>
    fetch(`${BASE}/api/claims/${id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, note }),
    }).then((r) => asJson<Decision>(r)),

  explainClaim: (id: string) =>
    fetch(`${BASE}/api/claims/${id}/explain`, { cache: "no-store" }).then((r) => asJson<Explanation>(r)),

  getPolicy: () => fetch(`${BASE}/api/policy`, { cache: "no-store" }).then((r) => asJson<PolicyDoc>(r)),

  // Verify an admin password against the backend. Resolves on success, throws on 401.
  adminLogin: (token: string) =>
    fetch(`${BASE}/api/admin/login`, {
      method: "POST",
      headers: { "X-Admin-Token": token },
    }).then((r) => asJson<{ ok: boolean }>(r)),

  updatePolicy: (policy: PolicyDoc, token: string) =>
    fetch(`${BASE}/api/policy`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Admin-Token": token },
      body: JSON.stringify(policy),
    }).then((r) => asJson<PolicyDoc>(r)),
};
