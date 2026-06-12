"""Engine coverage for policy rules the ten sample cases don't exercise.

These are deterministic, LLM-free checks of the rules that live in
`adjudication_rules.md` / `policy_terms.json` but aren't hit by TC001-TC010:
the initial waiting period, the full exclusions list, the LASIK carve-out,
the MRI/CT pre-auth threshold, and late submission. They guard against the
engine being silently overfit to the provided cases.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.engine import adjudicate
from app.models import ClaimInput, Prescription


def _claim(*, diagnosis="Viral fever", treatment="", amount=1500.0,
           join=None, submission=None, treatment_date="2024-10-10",
           procedures=None, medicines=None, tests=None, bill=None) -> ClaimInput:
    return ClaimInput(
        member_id="EMP999", member_name="Test Member",
        treatment_date=treatment_date, claim_amount=amount,
        member_join_date=join, submission_date=submission,
        prescription=Prescription(
            doctor_name="Dr. Test", doctor_reg="KA/45678/2015",
            diagnosis=diagnosis, treatment=treatment,
            procedures=procedures or [], medicines_prescribed=medicines or [],
            tests_prescribed=tests or []),
        bill=bill or {"consultation_fee": amount})


# --- Initial waiting period (policy_terms: initial_waiting = 30) -------------

def test_initial_waiting_period_rejects_claim_within_30_days():
    c = _claim(join=date(2024, 10, 1), treatment_date="2024-10-10")  # 9 days in
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "WAITING_PERIOD" in d.rejection_reasons
    assert "initial waiting period" in d.notes.lower()


def test_initial_waiting_period_satisfied_after_30_days():
    c = _claim(join=date(2024, 1, 1), treatment_date="2024-10-10")  # >30 days in
    assert adjudicate(c).decision == "APPROVED"


# --- Exclusions beyond weight-loss (only one provided as TC009) -------------

@pytest.mark.parametrize("diagnosis", [
    "HIV positive, on antiretroviral therapy",
    "Self-inflicted laceration to forearm",
    "Fracture sustained while skydiving",
    "Injury from an act of war",
])
def test_excluded_conditions_are_not_covered(diagnosis):
    d = adjudicate(_claim(diagnosis=diagnosis))
    assert d.decision == "REJECTED"
    assert "SERVICE_NOT_COVERED" in d.rejection_reasons


def test_lasik_is_excluded_even_though_vision_is_covered():
    c = _claim(diagnosis="Myopia", treatment="LASIK surgery",
               procedures=["LASIK"], bill={"lasik": 4000})
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "SERVICE_NOT_COVERED" in d.rejection_reasons


def test_warfarin_does_not_trip_the_war_exclusion():
    """Substring guard: 'war' must not match the drug 'warfarin'."""
    c = _claim(diagnosis="Atrial fibrillation", medicines=["Warfarin 5mg"])
    assert adjudicate(c).decision == "APPROVED"


# --- Doctor registration year must be a real, plausible year ----------------

@pytest.mark.parametrize("reg", ["KA/45678/0000", "KA/45678/9999", "KA/45678/2099"])
def test_implausible_registration_year_is_invalid(reg):
    c = _claim(treatment_date="2024-11-01")
    c.prescription.doctor_reg = reg
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "DOCTOR_REG_INVALID" in d.rejection_reasons


def test_registration_year_not_after_treatment_year():
    c = _claim(treatment_date="2024-11-01")
    c.prescription.doctor_reg = "KA/45678/2025"  # registered after the visit
    assert "DOCTOR_REG_INVALID" in adjudicate(c).rejection_reasons


def test_plausible_registration_year_passes():
    c = _claim(treatment_date="2024-11-01")
    c.prescription.doctor_reg = "KA/45678/2015"
    assert adjudicate(c).decision == "APPROVED"


# --- MRI/CT pre-auth threshold (TC007 note: "above ₹10000") -----------------

def test_mri_below_threshold_is_covered_without_preauth():
    c = _claim(diagnosis="Knee pain", tests=["MRI Knee"], amount=4000,
               bill={"mri_scan": 4000})
    d = adjudicate(c)
    assert d.decision == "APPROVED"
    assert d.approved_amount == 4000


def test_mri_above_threshold_needs_preauth():
    c = _claim(diagnosis="Lumbar disc herniation", tests=["MRI Lumbar Spine"],
               amount=15000, bill={"mri_scan": 15000})
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "PRE_AUTH_MISSING" in d.rejection_reasons


# --- Date integrity: impossible dates are rejected ---------------------------

def test_future_treatment_date_is_rejected():
    c = _claim(treatment_date="2999-01-01")
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "DATE_MISMATCH" in d.rejection_reasons


def test_join_date_after_treatment_is_rejected():
    c = _claim(join=date(2024, 11, 1), treatment_date="2024-10-01")  # joined after visit
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "DATE_MISMATCH" in d.rejection_reasons


# --- Late submission (policy_terms: submission_timeline_days = 30) -----------

def test_late_submission_is_rejected():
    c = _claim(treatment_date="2024-10-01", submission=date(2024, 12, 1))
    d = adjudicate(c)
    assert d.decision == "REJECTED"
    assert "LATE_SUBMISSION" in d.rejection_reasons


def test_on_time_submission_is_accepted():
    c = _claim(treatment_date="2024-10-01", submission=date(2024, 10, 20))
    assert adjudicate(c).decision == "APPROVED"
