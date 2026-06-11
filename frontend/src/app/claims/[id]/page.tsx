"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Decision } from "@/lib/types";
import { DecisionCard } from "@/components/DecisionCard";
import { ReviewPanel } from "@/components/ReviewPanel";

export default function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    api.getClaim(id).then(setDecision).catch((e) => setError(e instanceof Error ? e.message : "Claim not found"));
  }, [id]);

  return (
    <div>
      <Link href="/claims" className="text-sm text-ink-muted transition-colors hover:text-ink">
        ← All claims
      </Link>
      <div className="mt-5 max-w-xl">
        {error && <p className="rounded-lg bg-bad-bg px-4 py-3 text-sm text-bad">{error}</p>}
        {!error && !decision && <div className="h-72 animate-pulse rounded-2xl border border-border bg-surface" />}
        {decision && (
          <div className="space-y-5">
            <DecisionCard decision={decision} />
            {decision.decision === "MANUAL_REVIEW" && (
              <ReviewPanel claimId={decision.claim_id} onResolved={setDecision} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
