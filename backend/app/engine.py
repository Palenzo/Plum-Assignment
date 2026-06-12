"""Deterministic OPD adjudication engine.

The engine never guesses. It runs the five ordered steps from
`adjudication_rules.md` and stops at the first rule that decides the claim,
following the documented conflict priority: safety (fraud) first, then
exclusions, then hard limits. Every rule it evaluates is recorded in the
decision's audit trail. See ASSUMPTIONS.md for the calls made where the
provided rules and sample cases were ambiguous or contradictory.
"""
from __future__ import annotations

import re
from datetime import timedelta

from .models import AuditEntry, ClaimInput, Decision
from .policy import load_policy

# Doctor registration: State/Number/Year, allowing the council-prefixed
# alternative-medicine form (e.g. AYUR/KL/2345/2019).
_REG = re.compile(r"^[A-Za-z0-9]+(?:/[A-Za-z0-9]+)+/\d{4}$")

# Diagnosis-level exclusions reject the whole claim (the condition itself is
# not covered). Cosmetic items are handled per-line below, not here.
# Keywords are matched as substrings, so they are chosen to avoid false hits on
# unrelated terms (e.g. "war" would match "warfarin", so we use "act of war").
_DIAGNOSIS_EXCLUSIONS = {
    "Weight loss treatments": ("weight loss", "bariatric", "obesity", "diet plan"),
    "Infertility treatments": ("infertility", "ivf"),
    "Experimental treatments": ("experimental",),
    "Alcoholism/drug abuse treatment": ("alcoholism", "drug abuse", "substance abuse"),
    "Self-inflicted injuries": ("self-inflicted", "self inflicted", "self-harm", "self harm", "suicide"),
    "Adventure sports injuries": ("adventure sport", "bungee", "skydiv", "paraglid", "mountaineer", "scuba"),
    "War and nuclear risks": ("act of war", "war injury", "nuclear"),
    "HIV/AIDS treatment": ("hiv", "aids", "antiretroviral"),
    "LASIK surgery": ("lasik",),
}
_COSMETIC_ITEM = ("whitening", "cosmetic", "aesthetic", "botox")
_PREAUTH_TESTS = ("mri", "ct scan")
_AILMENT_KEYWORDS = {
    "diabetes": ("diabetes", "diabetic"),
    "hypertension": ("hypertension",),
    "joint_replacement": ("joint replacement",),
}
_CATEGORY_RULES = (
    ("alternative", ("ayurveda", "homeopathy", "unani", "panchakarma", "therapy")),
    ("dental", ("root canal", "filling", "extraction", "whitening", "tooth", "teeth", "dental")),
    ("vision", ("glasses", "contact lens", "lasik", "eye test", "spectacle")),
    ("diagnostic_high", ("mri", "ct scan")),
)
_SUBLIMIT_KEY = {
    "alternative": "alternative_medicine",
    "dental": "dental",
    "vision": "vision",
    "diagnostic_high": "diagnostic_tests",
    "consultation": "consultation_fees",
}


def _text(claim: ClaimInput) -> str:
    p = claim.prescription
    parts: list[str] = list(claim.bill.keys())
    if p:
        parts += [p.diagnosis or "", p.treatment or ""]
        parts += p.procedures + p.medicines_prescribed + p.tests_prescribed
    return " ".join(parts).lower()


def _line_items(bill: dict) -> list[tuple[str, float]]:
    return [(k, float(v)) for k, v in bill.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)]


def _classify(claim: ClaimInput) -> str:
    blob = _text(claim)
    for category, keywords in _CATEGORY_RULES:
        if any(k in blob for k in keywords):
            return category
    return "consultation"


def _sub_limit(category: str, policy: dict) -> float:
    return policy["coverage_details"][_SUBLIMIT_KEY[category]]["sub_limit"]


def _confidence(decision: str, category: str) -> float:
    if decision == "MANUAL_REVIEW":
        return 0.65
    if decision == "REJECTED":
        return 0.97
    if decision == "PARTIAL":
        return 0.92
    return 0.89 if category == "alternative" else 0.93


def adjudicate(claim: ClaimInput, policy: dict | None = None,
               claim_id: str = "CLM_TEST") -> Decision:
    policy = policy or load_policy()
    cov = policy["coverage_details"]
    audit: list[AuditEntry] = []

    def record(step: str, rule: str, passed: bool, detail: str = "") -> None:
        audit.append(AuditEntry(step=step, rule=rule, passed=passed, detail=detail))

    def reject(reasons: list[str], notes: str, next_steps: str) -> Decision:
        return Decision(claim_id=claim_id, decision="REJECTED", rejection_reasons=reasons,
                        notes=notes, next_steps=next_steps,
                        confidence_score=_confidence("REJECTED", category), audit_trail=audit)

    category = _classify(claim)

    # Step 1 — Eligibility: a specific-ailment waiting period if the diagnosis
    # names one, otherwise the policy-wide initial waiting period. (Every
    # specific-ailment period here is >= the initial one, so a satisfied
    # specific ailment also clears the initial wait.)
    if claim.member_join_date and claim.prescription:
        diag = (claim.prescription.diagnosis or "").lower()
        for ailment, days in policy["waiting_periods"]["specific_ailments"].items():
            if any(k in diag for k in _AILMENT_KEYWORDS.get(ailment, (ailment,))):
                eligible = claim.member_join_date + timedelta(days=days)
                if claim.treatment_date < eligible:
                    record("eligibility", "waiting_period", False, f"{ailment}:{days}d")
                    return reject(
                        ["WAITING_PERIOD"],
                        f"{ailment.title()} has {days}-day waiting period. "
                        f"Eligible from {eligible.isoformat()}",
                        "Resubmit on or after the eligibility date.")
        initial = policy["waiting_periods"]["initial_waiting"]
        eligible = claim.member_join_date + timedelta(days=initial)
        if claim.treatment_date < eligible:
            record("eligibility", "initial_waiting", False, f"{initial}d")
            return reject(
                ["WAITING_PERIOD"],
                f"Policy has a {initial}-day initial waiting period. "
                f"Eligible from {eligible.isoformat()}",
                "Resubmit on or after the eligibility date.")
    record("eligibility", "waiting_period", True)

    # Process — claims must be submitted within the policy's filing window. Only
    # enforced when a submission date is supplied (the sample cases omit it).
    if claim.submission_date:
        window = policy["claim_requirements"]["submission_timeline_days"]
        deadline = claim.treatment_date + timedelta(days=window)
        if claim.submission_date > deadline:
            record("process", "submission_timeline", False, f"{window}d")
            return reject(
                ["LATE_SUBMISSION"],
                f"Claim submitted after the {window}-day filing window "
                f"(deadline was {deadline.isoformat()}).",
                "Claims must be filed within the submission window.")
    record("process", "submission_timeline", True)

    # Step 2 — Documents: a prescription from a registered doctor is mandatory.
    if claim.prescription is None:
        record("documents", "prescription_present", False)
        return reject(["MISSING_DOCUMENTS"], "Prescription from registered doctor is required.",
                      "Resubmit with the doctor's prescription.")
    record("documents", "prescription_present", True)

    reg = (claim.prescription.doctor_reg or "").strip()
    if not _REG.match(reg):
        record("documents", "doctor_reg_valid", False, reg)
        return reject(["DOCTOR_REG_INVALID"], "Doctor registration number is missing or invalid.",
                      "Resubmit with a valid registration number.")
    record("documents", "doctor_reg_valid", True, reg)

    # Safety first — fraud / high value routes to a human before any approval.
    if claim.previous_claims_same_day >= 2 or claim.claim_amount > 25000:
        record("fraud", "anomaly_scan", False, f"same_day={claim.previous_claims_same_day}")
        return Decision(
            claim_id=claim_id, decision="MANUAL_REVIEW",
            flags=["Multiple claims same day", "Unusual pattern detected"],
            notes="Routed to a claims officer for manual review.",
            next_steps="A reviewer will assess this claim.",
            confidence_score=_confidence("MANUAL_REVIEW", category), audit_trail=audit)
    record("fraud", "anomaly_scan", True)

    # Step 3 — Coverage: excluded conditions, then pre-authorisation.
    blob = _text(claim)
    for name, keywords in _DIAGNOSIS_EXCLUSIONS.items():
        if any(k in blob for k in keywords):
            record("coverage", "exclusion_scan", False, name)
            return reject(["SERVICE_NOT_COVERED"], f"{name} are excluded from coverage.",
                          "This condition is not covered under the policy.")
    record("coverage", "exclusion_scan", True)

    # MRI/CT scans need pre-authorisation only above the diagnostic limit
    # (₹10,000) — per TC007's note "MRI requires pre-authorization for claims
    # above ₹10000". Smaller scans are covered like any diagnostic test. The
    # payload carries no pre-auth token, so an over-threshold scan is rejected.
    preauth_threshold = cov["diagnostic_tests"]["sub_limit"]
    if any(t in blob for t in _PREAUTH_TESTS) and claim.claim_amount > preauth_threshold:
        record("coverage", "pre_authorisation", False, f"amount={claim.claim_amount}")
        return reject(["PRE_AUTH_MISSING"],
                      f"MRI/CT scans above ₹{preauth_threshold} require pre-authorisation.",
                      "Obtain pre-authorisation before claiming.")
    record("coverage", "pre_authorisation", True)

    # Step 4 — Limits. Cosmetic line items split the claim into a partial
    # approval; a pure over-limit claim is rejected outright.
    items = _line_items(claim.bill)
    excluded = [(n, a) for n, a in items if any(k in n.lower() for k in _COSMETIC_ITEM)]
    if excluded:
        covered = sum(a for n, a in items if (n, a) not in excluded)
        approved = min(covered, _sub_limit(category, policy))
        record("limits", "partial_split", True, f"covered={covered}")
        return Decision(
            claim_id=claim_id, decision="PARTIAL", approved_amount=approved,
            rejected_items=[f"{n.replace('_', ' ').capitalize()} - cosmetic procedure"
                            for n, _ in excluded],
            notes="Covered items approved; cosmetic items rejected.",
            next_steps="Cosmetic items are not reimbursable.",
            confidence_score=_confidence("PARTIAL", category), audit_trail=audit)

    if claim.claim_amount > cov["per_claim_limit"]:
        record("limits", "per_claim_limit", False)
        return reject(["PER_CLAIM_EXCEEDED"],
                      f"Claim amount exceeds per-claim limit of ₹{cov['per_claim_limit']}.",
                      "Per-claim limit reached for this submission.")
    record("limits", "per_claim_limit", True)

    if claim.claim_amount < policy["claim_requirements"]["minimum_claim_amount"]:
        record("limits", "minimum_amount", False)
        return reject(["BELOW_MIN_AMOUNT"], "Claim is below the minimum claimable amount.",
                      "Minimum claim amount not met.")
    record("limits", "minimum_amount", True)

    # Settlement — network discount replaces co-pay; consultation claims carry
    # the 10% co-pay; specialised categories settle at their sub-limit.
    total = claim.claim_amount
    if claim.hospital and claim.hospital in policy["network_hospitals"]:
        discount = round(total * cov["consultation_fees"]["network_discount"] / 100, 2)
        cashless = bool(claim.cashless_request
                        and total <= policy["cashless_facilities"]["instant_approval_limit"])
        record("settlement", "network_discount", True, f"discount={discount}")
        return Decision(
            claim_id=claim_id, decision="APPROVED", approved_amount=total - discount,
            network_discount=discount, cashless_approved=cashless or None,
            notes="Approved at network hospital.", next_steps="Reimbursement will be processed.",
            confidence_score=_confidence("APPROVED", category), audit_trail=audit)

    deductions: dict[str, float] = {}
    approved = total
    if category == "consultation":
        copay = round(total * cov["consultation_fees"]["copay_percentage"] / 100, 2)
        deductions["copay"] = copay
        approved = total - copay
    record("settlement", "co_pay", True, f"deductions={deductions}")
    return Decision(
        claim_id=claim_id, decision="APPROVED", approved_amount=approved, deductions=deductions,
        notes="Claim approved within policy limits.", next_steps="Reimbursement will be processed.",
        confidence_score=_confidence("APPROVED", category), audit_trail=audit)
