"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import type { ClaimListItem } from "@/lib/types";
import { VerdictBadge } from "@/components/VerdictBadge";

export default function ClaimsPage() {
  const [items, setItems] = useState<ClaimListItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listClaims().then(setItems).catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  return (
    <div>
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl">Claims</h1>
          <p className="mt-2 text-ink-muted">Every adjudicated claim and its decision.</p>
        </div>
        <Link href="/" className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover">
          New claim
        </Link>
      </div>

      <div className="mt-8">
        {error && <p className="rounded-lg bg-bad-bg px-4 py-3 text-sm text-bad">{error}</p>}
        {!error && items === null && <Skeleton />}
        {!error && items?.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border p-10 text-center">
            <p className="font-display text-lg font-medium">No claims yet</p>
            <p className="mt-1.5 text-sm text-ink-muted">Submit your first claim to see it here.</p>
          </div>
        )}
        {items && items.length > 0 && (
          <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border">
            {items.map((item) => (
              <li key={item.claim_id}>
                <Link
                  href={`/claims/${item.claim_id}`}
                  className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-ink">{item.member_name}</p>
                    <p className="tnum text-xs text-ink-faint">{item.claim_id}</p>
                  </div>
                  <div className="hidden text-right sm:block">
                    <p className="tnum text-sm text-ink">{inr(item.approved_amount)}</p>
                    <p className="tnum text-xs text-ink-faint">of {inr(item.claim_amount)}</p>
                  </div>
                  <VerdictBadge verdict={item.decision} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border">
      {[0, 1, 2].map((i) => (
        <li key={i} className="flex items-center gap-4 px-5 py-4">
          <div className="flex-1 space-y-2">
            <div className="h-3.5 w-32 animate-pulse rounded bg-border" />
            <div className="h-2.5 w-20 animate-pulse rounded bg-border" />
          </div>
          <div className="h-6 w-24 animate-pulse rounded-md bg-border" />
        </li>
      ))}
    </ul>
  );
}
