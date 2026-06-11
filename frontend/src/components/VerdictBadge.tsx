import type { Verdict } from "@/lib/types";
import { TONE_CLASS, VERDICT } from "@/lib/verdict";
import { verdictIcon } from "./icons";

export function VerdictBadge({ verdict, size = "md" }: { verdict: Verdict; size?: "md" | "lg" }) {
  const v = VERDICT[verdict];
  const t = TONE_CLASS[v.tone];
  const Icon = verdictIcon(verdict);

  if (size === "lg") {
    return (
      <span className={`inline-flex items-center gap-2.5 rounded-lg ${t.bg} px-4 py-2`}>
        <Icon className={`h-6 w-6 ${t.text}`} />
        <span className={`font-display text-xl font-medium ${t.text}`}>{v.label}</span>
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md ${t.bg} px-2.5 py-1 text-sm font-medium ${t.text}`}>
      <Icon className="h-4 w-4" />
      {v.label}
    </span>
  );
}
