"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import type { ClaimListItem } from "@/lib/types";
import { VerdictBadge } from "@/components/VerdictBadge";
import { Chevron } from "@/components/icons";

const PAGE = 10;

const STATUS_OPTIONS = [
  { value: "", label: "All decisions" },
  { value: "APPROVED", label: "Approved" },
  { value: "PARTIAL", label: "Partial" },
  { value: "REJECTED", label: "Rejected" },
  { value: "MANUAL_REVIEW", label: "Manual review" },
];

const SORT_OPTIONS = [
  { value: "recent", label: "Newest first", sort: "created_at", order: "desc" },
  { value: "oldest", label: "Oldest first", sort: "created_at", order: "asc" },
  { value: "amount_high", label: "Amount: high to low", sort: "claim_amount", order: "desc" },
  { value: "amount_low", label: "Amount: low to high", sort: "claim_amount", order: "asc" },
] as const;

type SortKey = (typeof SORT_OPTIONS)[number]["value"];

const selectClass =
  "rounded-md border border-border bg-bg px-3 py-2 text-sm text-ink transition-colors focus:border-primary focus-visible:outline-none";

export default function ClaimsPage() {
  const [items, setItems] = useState<ClaimListItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("recent");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const opt = SORT_OPTIONS.find((o) => o.value === sortKey) ?? SORT_OPTIONS[0];
    let active = true;
    setLoading(true);
    setError("");
    api
      .listClaims({
        limit: PAGE,
        offset: (page - 1) * PAGE,
        status: status || undefined,
        sort: opt.sort,
        order: opt.order,
      })
      .then((res) => {
        if (!active) return;
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [page, status, sortKey]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE));
  const from = total === 0 ? 0 : (page - 1) * PAGE + 1;
  const to = Math.min(page * PAGE, total);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Claims</h1>
          <p className="mt-2 text-ink-muted">
            Every adjudicated claim and its decision{total > 0 ? ` · ${total} total` : ""}.
          </p>
        </div>
        <Link
          href="/"
          className="shrink-0 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-ink transition-colors hover:bg-primary-hover"
        >
          New claim
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <select
          aria-label="Filter by decision"
          className={selectClass}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort claims"
          className={selectClass}
          value={sortKey}
          onChange={(e) => {
            setSortKey(e.target.value as SortKey);
            setPage(1);
          }}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-6">
        {error && <p className="rounded-lg bg-bad-bg px-4 py-3 text-sm text-bad">{error}</p>}
        {!error && items === null && <Skeleton />}
        {!error && items?.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border p-10 text-center">
            <p className="font-display text-lg font-medium">No claims found</p>
            <p className="mt-1.5 text-sm text-ink-muted">
              {status ? "Try a different filter." : "Submit your first claim to see it here."}
            </p>
          </div>
        )}
        {items && items.length > 0 && (
          <>
            <ul
              className={`divide-y divide-border overflow-hidden rounded-2xl border border-border transition-opacity ${
                loading ? "opacity-60" : ""
              }`}
            >
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

            <div className="mt-5 flex items-center justify-between">
              <p className="text-sm text-ink-muted">
                Showing <span className="tnum">{from}–{to}</span> of <span className="tnum">{total}</span>
              </p>
              <div className="flex items-center gap-2">
                <PageButton
                  label="Previous page"
                  disabled={page <= 1 || loading}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <Chevron className="h-4 w-4 rotate-90" />
                </PageButton>
                <span className="tnum text-sm text-ink-muted">
                  Page {page} of {totalPages}
                </span>
                <PageButton
                  label="Next page"
                  disabled={page >= totalPages || loading}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  <Chevron className="h-4 w-4 -rotate-90" />
                </PageButton>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function PageButton({
  children,
  disabled,
  onClick,
  label,
}: {
  children: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="grid h-9 w-9 place-items-center rounded-md border border-border text-ink transition-colors hover:border-primary disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
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
