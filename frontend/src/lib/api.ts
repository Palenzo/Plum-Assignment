import type { ClaimInput, ClaimsPage, Decision, Explanation, PolicyDoc } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

  updatePolicy: (policy: PolicyDoc) =>
    fetch(`${BASE}/api/policy`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(policy),
    }).then((r) => asJson<PolicyDoc>(r)),
};
