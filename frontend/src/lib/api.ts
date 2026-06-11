import type { ClaimInput, ClaimListItem, Decision } from "./types";

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

  listClaims: () =>
    fetch(`${BASE}/api/claims`, { cache: "no-store" }).then((r) => asJson<ClaimListItem[]>(r)),

  getClaim: (id: string) =>
    fetch(`${BASE}/api/claims/${id}`, { cache: "no-store" }).then((r) => asJson<Decision>(r)),

  resolveClaim: (id: string, action: "approve" | "reject", note: string) =>
    fetch(`${BASE}/api/claims/${id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, note }),
    }).then((r) => asJson<Decision>(r)),
};
