"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ClaimListItem } from "@/lib/types";
import { Chevron } from "@/components/icons";

const PAGE = 10;

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ClaimListItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadMore = useCallback(async () => {
    setLoading(true);
    try {
      const offset = items?.length ?? 0;
      const page = await api.listClaims({ status: "MANUAL_REVIEW", limit: PAGE, offset });
      setItems((prev) => [...(prev ?? []), ...page.items]);
      setTotal(page.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [items]);

  useEffect(() => {
    api
      .listClaims({ status: "MANUAL_REVIEW", limit: PAGE, offset: 0 })
      .then((page) => { setItems(page.items); setTotal(page.total); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const shown = items?.length ?? 0;

  return (
    <div>
      <h1 className="text-3xl">Review queue</h1>
      <p className="mt-2 text-ink-muted">
        Claims the AI escalated for a human decision{total > 0 ? ` · ${total} pending` : ""}.
      </p>

      <div className="mt-8">
        {error && <p className="rounded-lg bg-bad-bg px-4 py-3 text-sm text-bad">{error}</p>}
        {!error && items === null && <div className="h-24 animate-pulse rounded-2xl border border-border bg-surface" />}
        {!error && items?.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border p-10 text-center">
            <p className="font-display text-lg font-medium">Nothing waiting for review</p>
            <p className="mt-1.5 text-sm text-ink-muted">Escalated claims will appear here.</p>
          </div>
        )}
        {items && items.length > 0 && (
          <>
            <ul className="space-y-3">
              {items.map((item) => (
                <li key={item.claim_id}>
                  <Link
                    href={`/claims/${item.claim_id}`}
                    className="flex items-center gap-4 rounded-xl border border-border bg-bg px-5 py-4 transition-colors hover:border-info"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink">{item.member_name}</p>
                      <p className="mt-1 truncate text-sm text-ink-muted">
                        {item.flags && item.flags.length > 0 ? item.flags.join(" · ") : "Awaiting review"}
                      </p>
                    </div>
                    <span className="tnum hidden text-sm text-ink-faint sm:block">{item.claim_id}</span>
                    <Chevron className="h-4 w-4 -rotate-90 text-ink-faint" />
                  </Link>
                </li>
              ))}
            </ul>
            {shown < total && (
              <div className="mt-5 text-center">
                <button
                  onClick={loadMore}
                  disabled={loading}
                  className="rounded-md border border-border px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary disabled:opacity-50"
                >
                  {loading ? "Loading…" : `Load more (${total - shown} left)`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
