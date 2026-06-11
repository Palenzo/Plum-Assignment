import type { ClaimInput, ClaimsPage, Decision, Explanation, PolicyDoc } from "./types";

// Default: call our own origin and let the Next.js proxy (app/api/[...path])
// forward to the backend at runtime — no CORS, no build-time backend URL.
// Set NEXT_PUBLIC_API_URL only if you want the browser to hit the backend
// directly (then the backend must allow that origin via CORS).
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.json() as Promise<T>;
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

  listClaims: (opts: { limit?: number; offset?: number; status?: string } = {}) => {
    const params = new URLSearchParams();
    if (opts.limit != null) params.set("limit", String(opts.limit));
    if (opts.offset != null) params.set("offset", String(opts.offset));
    if (opts.status) params.set("status", opts.status);
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
