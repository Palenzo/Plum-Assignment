"""Adversarial / fuzz battery for the OPD API.

Fires malformed, hostile, and degenerate inputs at a *running* server and
classifies each response. The goal is to find anything that

  * returns 500 INTERNAL_ERROR (an unhandled crash), or
  * returns a 200 whose body is not standards-compliant JSON
    (e.g. bare ``Infinity`` / ``NaN``, which most JSON parsers reject), or
  * drops the connection / hangs.

Everything else (clean 4xx with an ``{"error", "code"}`` envelope, or a valid
2xx) is considered correctly handled.

Usage:
    python adversarial.py                 # hits http://localhost:8000
    python adversarial.py http://host:8000
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"

# A baseline-valid claim we mutate per case.
VALID = {
    "member_id": "EMP999",
    "member_name": "Fuzz Tester",
    "treatment_date": "2024-11-01",
    "claim_amount": 1500,
    "prescription": {
        "doctor_name": "Dr. Sharma",
        "doctor_reg": "KA/45678/2015",
        "diagnosis": "Viral fever",
        "medicines_prescribed": ["Paracetamol 650mg"],
    },
    "bill": {"consultation_fee": 1000, "diagnostic_tests": 500},
}

NULL = chr(0)  # built at runtime so the source file holds no literal null byte


def _raw(method: str, path: str, body: str | None,
         ctype: str = "application/json") -> tuple[int, str]:
    """Send a raw (possibly non-JSON) body; return (status, text)."""
    data = body.encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:  # connection reset, timeout, etc.
        return -1, f"{type(e).__name__}: {e}"


def _mut(**over) -> dict:
    c = json.loads(json.dumps(VALID))
    c.update(over)
    return c


def _reject_const(c):  # json parse_constant hook: surface Infinity/NaN as an error
    raise ValueError(c)


def classify(status: int, text: str) -> tuple[str, str]:
    """-> (verdict, short note).  verdict in BUG / WEAK / OK."""
    if status == -1:
        return "BUG", f"transport error: {text}"
    if status == 500:
        return "BUG", "500 - unhandled crash"
    # Body must be RFC-8259 JSON: reject bare Infinity/NaN that Python tolerates.
    try:
        json.loads(text, parse_constant=_reject_const)
    except ValueError as e:
        if str(e) in {"Infinity", "-Infinity", "NaN"}:
            if 200 <= status < 300:
                return "BUG", f"{status} body has non-standard JSON float (Infinity/NaN)"
        elif text.strip():
            return "WEAK", f"{status} non-JSON body: {text[:60]!r}"
    if 200 <= status < 300:
        try:
            d = json.loads(text)
            return "OK", f"{status} {d.get('decision', '')} amt={d.get('approved_amount', '')}".strip()
        except Exception:
            return "OK", f"{status}"
    if 400 <= status < 500:
        try:
            d = json.loads(text)
            return "OK", f"{status} {d.get('code', '')}: {str(d.get('error', ''))[:50]}"
        except Exception:
            return "WEAK", f"{status} (no error envelope)"
    return "WEAK", f"unexpected status {status}"


def _inf(token: str, **extra) -> str:
    """Build a JSON body with a raw non-standard float token for claim_amount."""
    s = json.dumps(_mut(claim_amount=1, **extra))
    return s.replace('"claim_amount": 1', f'"claim_amount": {token}')


# (name, method, path, raw-body[, content_type]) — raw bodies let us send
# invalid JSON too; the optional 5th element overrides the default content-type.
CASES: list[tuple] = [
    # --- numeric edge cases on claim_amount ---
    ("Infinity amount", "POST", "/api/claims/json", _inf("Infinity")),
    ("NaN amount", "POST", "/api/claims/json", _inf("NaN")),
    ("Overflow 1e400", "POST", "/api/claims/json", _inf("1e400")),
    ("Negative amount", "POST", "/api/claims/json", json.dumps(_mut(claim_amount=-5000))),
    ("Zero amount", "POST", "/api/claims/json", json.dumps(_mut(claim_amount=0))),
    ("Huge finite amount", "POST", "/api/claims/json", json.dumps(_mut(claim_amount=1e308))),
    ("Amount as string", "POST", "/api/claims/json", json.dumps(_mut(claim_amount="lots"))),
    # --- bill shape abuse ---
    ("Bill huge -> inf sum", "POST", "/api/claims/json", json.dumps(_mut(bill={"a": 1e308, "b": 1e308}, claim_amount=2000))),
    ("Bill bool values", "POST", "/api/claims/json", json.dumps(_mut(bill={"consultation_fee": True}))),
    ("Bill nested dict value", "POST", "/api/claims/json", json.dumps(_mut(bill={"x": {"y": 1}}, claim_amount=1500))),
    ("Bill is a list", "POST", "/api/claims/json", json.dumps(_mut(bill=[1, 2, 3]))),
    ("Bill empty-string key", "POST", "/api/claims/json", json.dumps(_mut(bill={"": 1500}))),
    ("Cosmetic + underscore key", "POST", "/api/claims/json", json.dumps(_mut(bill={"teeth_whitening_pro": 4000, "root_canal": 8000}, claim_amount=12000, prescription={**VALID["prescription"], "diagnosis": "tooth decay", "procedures": ["Root canal", "whitening"]}))),
    # --- string / injection / unicode ---
    ("SQLi in member_id", "POST", "/api/claims/json", json.dumps(_mut(member_id="'; DROP TABLE claims;--"))),
    ("XSS in member_name", "POST", "/api/claims/json", json.dumps(_mut(member_name="<script>alert(1)</script>"))),
    ("Null byte in name", "POST", "/api/claims/json", json.dumps(_mut(member_name="a" + NULL + "b"))),
    ("Emoji + RTL diagnosis", "POST", "/api/claims/json", json.dumps(_mut(prescription={**VALID["prescription"], "diagnosis": "fever \U0001f912 ‮evil"}))),
    ("1MB member_name", "POST", "/api/claims/json", json.dumps(_mut(member_name="A" * 1_000_000))),
    ("Regex-y diagnosis", "POST", "/api/claims/json", json.dumps(_mut(prescription={**VALID["prescription"], "diagnosis": "(.*)+[a-z]{999999}"}))),
    # --- date abuse ---
    ("Impossible date 2024-13-45", "POST", "/api/claims/json", json.dumps(_mut(treatment_date="2024-13-45"))),
    ("Date wrong format", "POST", "/api/claims/json", json.dumps(_mut(treatment_date="01/11/2024"))),
    ("Far-future date", "POST", "/api/claims/json", json.dumps(_mut(treatment_date="9999-12-31"))),
    ("Join after treatment", "POST", "/api/claims/json", json.dumps(_mut(member_join_date="2025-01-01"))),
    # --- counter abuse ---
    ("Negative same-day count", "POST", "/api/claims/json", json.dumps(_mut(previous_claims_same_day=-3))),
    ("Huge same-day count", "POST", "/api/claims/json", json.dumps(_mut(previous_claims_same_day=10**18))),
    ("same-day as float", "POST", "/api/claims/json", json.dumps(_mut(previous_claims_same_day=2.9))),
    # --- doctor reg abuse ---
    ("Reg year 0000", "POST", "/api/claims/json", json.dumps(_mut(prescription={**VALID["prescription"], "doctor_reg": "KA/123/0000"}))),
    ("Reg 5-digit year", "POST", "/api/claims/json", json.dumps(_mut(prescription={**VALID["prescription"], "doctor_reg": "KA/123/12345"}))),
    ("Reg empty", "POST", "/api/claims/json", json.dumps(_mut(prescription={**VALID["prescription"], "doctor_reg": ""}))),
    # --- malformed envelopes ---
    ("Empty object", "POST", "/api/claims/json", "{}"),
    ("Truncated JSON", "POST", "/api/claims/json", '{"member_id": "x"'),
    ("Not JSON at all", "POST", "/api/claims/json", "<<<not json>>>"),
    ("Wrong content-type", "POST", "/api/claims/json", json.dumps(VALID), "text/plain"),
    ("Array instead of object", "POST", "/api/claims/json", "[1,2,3]"),
    # --- endpoint misuse ---
    ("GET missing claim", "GET", "/api/claims/DOES_NOT_EXIST", None),
    ("Explain missing claim", "GET", "/api/claims/NOPE/explain", None),
    ("Review missing claim", "POST", "/api/claims/NOPE/review", json.dumps({"action": "approve"})),
    ("Review bad action", "POST", "/api/claims/NOPE/review", json.dumps({"action": "obliterate"})),
    ("Policy write no token", "PUT", "/api/policy", json.dumps({"coverage_details": {}})),
    ("Policy write junk", "PUT", "/api/policy", json.dumps({"nope": 1})),
    ("List negative paging", "GET", "/api/claims?limit=-5&offset=-9", None),
    ("List huge limit", "GET", "/api/claims?limit=999999", None),
]


def main() -> int:
    print(f"Target: {BASE}\n")
    bugs, weak = [], []
    width = max(len(n) for n, *_ in CASES)
    for name, method, path, body, *rest in CASES:
        ctype = rest[0] if rest else "application/json"
        status, text = _raw(method, path, body, ctype=ctype)
        verdict, note = classify(status, text)
        if verdict == "BUG":
            bugs.append(name)
        elif verdict == "WEAK":
            weak.append(name)
        mark = {"OK": "ok  ", "WEAK": "WEAK", "BUG": "BUG "}[verdict]
        print(f"  [{mark}] {name.ljust(width)}  {note}")

    print("\n" + "-" * 60)
    print(f"BUGS (crashes / invalid output): {len(bugs)}  {bugs}")
    print(f"WEAK (handled but not ideal):    {len(weak)}  {weak}")
    print(f"OK:                              {len(CASES) - len(bugs) - len(weak)}")
    return 1 if bugs else 0


if __name__ == "__main__":
    raise SystemExit(main())
