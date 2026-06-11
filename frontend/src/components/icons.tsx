import type { Verdict } from "@/lib/types";

type Props = { className?: string };
const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const Check = ({ className }: Props) => (
  <svg {...base} className={className}><path d="m20 6-11 11-5-5" /></svg>
);
export const Cross = ({ className }: Props) => (
  <svg {...base} className={className}><path d="M18 6 6 18M6 6l12 12" /></svg>
);
export const Partial = ({ className }: Props) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none" />
  </svg>
);
export const Review = ({ className }: Props) => (
  <svg {...base} className={className}><circle cx="12" cy="12" r="9" /><path d="M12 7.5V12l3 2" /></svg>
);
export const Upload = ({ className }: Props) => (
  <svg {...base} className={className}>
    <path d="M12 15V4m0 0 4 4m-4-4-4 4" />
    <path d="M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" />
  </svg>
);
export const FileText = ({ className }: Props) => (
  <svg {...base} className={className}>
    <path d="M14 3v4a1 1 0 0 0 1 1h4" />
    <path d="M5 3h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
    <path d="M9 13h6M9 17h6" />
  </svg>
);
export const Chevron = ({ className }: Props) => (
  <svg {...base} className={className}><path d="m6 9 6 6 6-6" /></svg>
);
export const Sparkles = ({ className }: Props) => (
  <svg {...base} className={className}>
    <path d="M12 3l1.7 4.6L18 9.3l-4.3 1.7L12 15.6l-1.7-4.6L6 9.3l4.3-1.7L12 3z" />
  </svg>
);
export const Shield = ({ className }: Props) => (
  <svg {...base} className={className}>
    <path d="M12 3l7 3v6c0 4-3 7-7 8-4-1-7-4-7-8V6l7-3z" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);

const ICON: Record<Verdict, (p: Props) => React.ReactElement> = {
  APPROVED: Check,
  PARTIAL: Partial,
  REJECTED: Cross,
  MANUAL_REVIEW: Review,
};

export const verdictIcon = (v: Verdict) => ICON[v];
