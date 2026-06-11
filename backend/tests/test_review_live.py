"""Live test for the Agno review team. Skips without a Groq key."""
from __future__ import annotations

from datetime import date

import pytest

from app.config import settings
from app.models import ClaimInput, Prescription
from app.review import assess

from ._llm import skip_on_quota

pytestmark = pytest.mark.skipif(not settings()["groq_api_key"], reason="GROQ_API_KEY not set")


def _claim(diagnosis: str, **presc) -> ClaimInput:
    return ClaimInput(
        member_id="E", member_name="N", treatment_date=date(2024, 11, 1), claim_amount=1500,
        prescription=Prescription(diagnosis=diagnosis, doctor_reg="KA/12345/2020", **presc),
        bill={"consultation_fee": 1500})


@skip_on_quota
def test_team_confirms_a_sensible_claim():
    result = assess(_claim("Viral fever", medicines_prescribed=["Paracetamol 650mg"]))
    assert result.necessity_justified is True


@skip_on_quota
def test_team_flags_a_clear_mismatch():
    result = assess(_claim("Common cold", procedures=["Rhinoplasty (cosmetic nose reshaping)"]))
    assert (result.necessity_justified is False) or result.fraud_concern
