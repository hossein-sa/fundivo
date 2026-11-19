# ADR 0008 — Integer-unit shared shares and frozen draft lottery policy

Status: Accepted for the **draft proposal foundation**, 2026-11-19.

## Context

Fundivo currently allocates whole Share rows to one FundMembership. The user
requires halves, thirds, and partnerships while each whole Share remains one
lottery entry. Guest sponsorship and installment payments are not implemented.

## Decision

- Add `ShareParticipation` for discrete 12-unit shares; no floats.
- Backfill all existing shares at 12 units to the original membership.
- `Share.membership` remains the historical initial allottee for compatibility.
  Current participation is read from `Share.participations`.
- During draft, managers can propose **one** split, with the initial allottee
  retained. One request ID makes retries idempotent. Subsequent changes require
  an audited transfer workflow, not editing history in place.
- Do not allow new guest co-ownership proposals until sponsorship and consent
  flows exist. Historic single-guest shares remain intact.
- Add `Fund.lottery_eligibility_policy`: `fully_settled` by default, or
  `allow_outstanding`; only editable in draft, and no execution until lottery
  and installment services exist.

## Trade-offs

A 12-unit denominator supports 1/2, 1/3, 1/4, 1/6 and 1/12 exactly, but not
1/5 or arbitrary percentages. Changing denominator later needs explicit
migration/contract review. Aggregate 12-unit sums are enforced by a locked
transactional service, not a simple per-row SQL check constraint.

These draft proposals do not assign enforceable liability. Activation must be
blocked until owner consent and guest sponsor acceptance are designed and
implemented. Existing shares and IDs are preserved by the data migration.
