import type { Decision } from "@/lib/types";
import { VERDICT, reasonLabel } from "@/lib/verdict";
import { AuditTrail } from "./AuditTrail";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { MoneyBreakdown } from "./MoneyBreakdown";
import { VerdictBadge } from "./VerdictBadge";

export function DecisionCard({ decision }: { decision: Decision }) {
  const v = VERDICT[decision.decision];
  const showMoney = decision.decision === "APPROVED" || decision.decision === "PARTIAL";

  return (
    <article className="animate-rise rounded-2xl border border-border bg-bg p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04),0_12px_32px_-12px_rgba(0,0,0,0.12)] sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <VerdictBadge verdict={decision.decision} size="lg" />
        <span className="tnum text-sm text-ink-faint">{decision.claim_id}</span>
      </div>

      <p className="mt-4 max-w-prose text-ink-muted">{decision.notes || v.blurb}</p>

      {showMoney && (
        <div className="mt-6">
          <MoneyBreakdown decision={decision} />
          {decision.cashless_approved && (
            <p className="mt-2 text-sm text-ok">Cashless approved at a network hospital.</p>
          )}
        </div>
      )}

      {decision.rejected_items?.length > 0 && (
        <div className="mt-4 rounded-lg bg-warn-bg px-4 py-3">
          <p className="text-sm font-medium text-warn">Not included</p>
          <ul className="mt-1.5 space-y-1 text-sm text-ink-muted">
            {decision.rejected_items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {decision.rejection_reasons?.length > 0 && (
        <ul className="mt-5 space-y-2">
          {decision.rejection_reasons.map((code) => (
            <li key={code} className="flex items-center gap-2.5 text-sm text-ink">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-bad" />
              {reasonLabel(code)}
            </li>
          ))}
        </ul>
      )}

      {decision.flags?.length > 0 && (
        <div className="mt-5 rounded-lg bg-info-bg px-4 py-3 text-sm text-info">
          {decision.flags.join(" · ")}
        </div>
      )}

      <div className="mt-6">
        <ConfidenceMeter score={decision.confidence_score} />
      </div>

      {decision.next_steps && (
        <p className="mt-6 border-t border-border pt-4 text-sm text-ink-muted">
          <span className="font-medium text-ink">Next: </span>
          {decision.next_steps}
        </p>
      )}

      <div className="mt-4">
        <AuditTrail entries={decision.audit_trail} />
      </div>
    </article>
  );
}
