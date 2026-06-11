# Decision logic

A claim flows top-to-bottom and stops at the **first** rule that decides it. The
order matters: cheap checks first (to save cost), then the ordered policy rules,
then the AI review, then a human if needed. This mirrors `adjudication_rules.md`
and its conflict-priority ("safety first, exclusions over everything, hard limits
cannot be exceeded").

```mermaid
flowchart TD
    A["Claim submitted"] --> B{"Cheap gates<br/>(zero AI cost)"}
    B -->|"no prescription"| R1["REJECTED · MISSING_DOCUMENTS"]
    B -->|"below ₹500 / duplicate"| R2["REJECTED"]
    B -->|pass| C{"1 · Eligibility<br/>waiting period"}
    C -->|within waiting| R3["REJECTED · WAITING_PERIOD"]
    C -->|ok| D{"2 · Documents<br/>doctor reg valid"}
    D -->|invalid| R4["REJECTED · DOCTOR_REG_INVALID"]
    D -->|ok| E{"Safety · fraud<br/>same-day count · high value"}
    E -->|anomaly| MR["MANUAL_REVIEW"]
    E -->|ok| F{"3 · Coverage<br/>exclusions · pre-auth"}
    F -->|excluded condition| R5["REJECTED · SERVICE_NOT_COVERED"]
    F -->|MRI/CT, no pre-auth| R6["REJECTED · PRE_AUTH_MISSING"]
    F -->|ok| G{"4 · Limits<br/>cosmetic items · per-claim"}
    G -->|cosmetic line item| P["PARTIAL · strip the item,<br/>cap by sub-limit"]
    G -->|over per-claim limit| R7["REJECTED · PER_CLAIM_EXCEEDED"]
    G -->|ok| H["Settlement<br/>co-pay or network discount"]
    H --> I{"5 · AI review team<br/>necessity + fraud"}
    P --> I
    I -->|"clinical concern"| MR
    I -->|"clear"| OK["APPROVED"]
    MR --> K{"Human reviewer"}
    K -->|approve| OK
    K -->|reject| RJ["REJECTED"]
```

## Who decides what

- **Cheap gates** and the **rule engine** are pure, deterministic Python. Same
  input → same output, every time. This is what makes the 10 provided test cases
  pass at 100%.
- The **AI review team** only sees the *clinical* picture (diagnosis, treatment,
  medicines) — never the amounts — and can only **escalate** an otherwise-approved
  claim to a human. It cannot approve, reject, or change money on its own.
- The **human reviewer** has the final say on anything escalated, and that
  resolution is recorded against the claim.

See [ASSUMPTIONS.md](../ASSUMPTIONS.md) for the documented calls made where the
provided rules and sample data were ambiguous (e.g. the per-claim-limit conflict
between test cases TC002 and TC003).
