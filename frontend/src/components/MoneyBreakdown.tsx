import type { Decision } from "@/lib/types";
import { inr } from "@/lib/format";

export function MoneyBreakdown({ decision }: { decision: Decision }) {
  const lines: { label: string; amount: number; deduction?: boolean }[] = [
    { label: "Claimed", amount: decision.claim_amount },
  ];
  if (decision.deductions?.copay) lines.push({ label: "Co-pay", amount: decision.deductions.copay, deduction: true });
  if (decision.network_discount) lines.push({ label: "Network discount", amount: decision.network_discount, deduction: true });

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <dl>
        {lines.map((line) => (
          <div key={line.label} className="flex items-center justify-between border-b border-border px-4 py-2.5">
            <dt className={`text-sm ${line.deduction ? "text-ink-muted" : "text-ink"}`}>{line.label}</dt>
            <dd className={`tnum text-sm ${line.deduction ? "text-ink-muted" : "text-ink"}`}>
              {line.deduction ? "−" : ""}{inr(line.amount)}
            </dd>
          </div>
        ))}
        <div className="flex items-baseline justify-between bg-surface px-4 py-3">
          <dt className="font-medium text-ink">Approved</dt>
          <dd className="tnum text-xl font-semibold text-ink">{inr(decision.approved_amount)}</dd>
        </div>
      </dl>
    </div>
  );
}
