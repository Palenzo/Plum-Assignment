import type { ClaimInput } from "./types";

/** Curated sample claims for one-click demos, drawn from the provided test cases. */
export const SAMPLES: { label: string; hint: string; claim: ClaimInput }[] = [
  {
    label: "Consultation",
    hint: "Straightforward approval with co-pay",
    claim: {
      member_id: "EMP001", member_name: "Rajesh Kumar",
      treatment_date: "2024-11-01", claim_amount: 1500,
      prescription: {
        doctor_name: "Dr. Sharma", doctor_reg: "KA/45678/2015",
        diagnosis: "Viral fever", medicines_prescribed: ["Paracetamol 650mg", "Vitamin C"],
      },
      bill: { consultation_fee: 1000, diagnostic_tests: 500 },
    },
  },
  {
    label: "Dental + cosmetic",
    hint: "Partial — cosmetic item stripped",
    claim: {
      member_id: "EMP002", member_name: "Priya Singh",
      treatment_date: "2024-10-15", claim_amount: 12000,
      prescription: {
        doctor_name: "Dr. Patel", doctor_reg: "MH/23456/2018",
        diagnosis: "Tooth decay requiring root canal",
        procedures: ["Root canal treatment", "Teeth whitening"],
      },
      bill: { root_canal: 8000, teeth_whitening: 4000 },
    },
  },
  {
    label: "Over limit",
    hint: "Rejected — exceeds per-claim limit",
    claim: {
      member_id: "EMP003", member_name: "Amit Verma",
      treatment_date: "2024-10-20", claim_amount: 7500,
      prescription: {
        doctor_name: "Dr. Gupta", doctor_reg: "DL/34567/2016",
        diagnosis: "Gastroenteritis", medicines_prescribed: ["Antibiotics", "Probiotics"],
      },
      bill: { consultation_fee: 2000, medicines: 5500 },
    },
  },
  {
    label: "Network cashless",
    hint: "Approved with network discount",
    claim: {
      member_id: "EMP010", member_name: "Deepak Shah",
      treatment_date: "2024-11-03", claim_amount: 4500,
      hospital: "Apollo Hospitals", cashless_request: true,
      prescription: {
        doctor_name: "Dr. Iyer", doctor_reg: "TN/56789/2013",
        diagnosis: "Acute bronchitis", medicines_prescribed: ["Antibiotics", "Bronchodilators"],
      },
      bill: { consultation_fee: 1500, medicines: 3000 },
    },
  },
];
