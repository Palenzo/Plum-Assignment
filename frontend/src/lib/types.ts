export type Verdict = "APPROVED" | "REJECTED" | "PARTIAL" | "MANUAL_REVIEW";

export interface Prescription {
  doctor_name?: string;
  doctor_reg?: string;
  diagnosis?: string;
  treatment?: string;
  medicines_prescribed?: string[];
  procedures?: string[];
  tests_prescribed?: string[];
}

export interface ClaimInput {
  member_id: string;
  member_name: string;
  treatment_date: string;
  claim_amount: number;
  member_join_date?: string | null;
  hospital?: string | null;
  cashless_request?: boolean;
  previous_claims_same_day?: number;
  prescription?: Prescription | null;
  bill?: Record<string, number | string | string[]>;
}

export interface AuditEntry {
  step: string;
  rule: string;
  passed: boolean;
  detail: string;
}

export interface Decision {
  claim_id: string;
  decision: Verdict;
  claim_amount: number;
  approved_amount: number;
  rejection_reasons: string[];
  rejected_items: string[];
  deductions: Record<string, number>;
  flags: string[];
  network_discount: number | null;
  cashless_approved: boolean | null;
  confidence_score: number;
  notes: string;
  next_steps: string;
  audit_trail: AuditEntry[];
}

export interface Explanation {
  summary: string;
  citations: string[];
}

export interface PolicyDoc {
  coverage_details: {
    annual_limit: number;
    per_claim_limit: number;
    family_floater_limit: number;
    [key: string]: unknown;
  };
  exclusions: string[];
  [key: string]: unknown;
}

export interface ClaimListItem {
  claim_id: string;
  member_name: string;
  decision: Verdict;
  claim_amount: number;
  approved_amount: number;
  flags?: string[];
}

export interface ClaimsPage {
  items: ClaimListItem[];
  total: number;
}
