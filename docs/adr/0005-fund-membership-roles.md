# ADR 0005 — Per-Fund Membership and Restricted Fund Mutations

Status: Accepted for this first Fund domain slice; future invitation/transfer policies remain open.

## Context

A single verified user may be a manager in one fund and a regular member in another. Platform staff status is not a fund role. Access must not depend on guessing an entity UUID.

## Decision

- Keep global identity in `accounts.User`.
- Introduce `funds.FundMembership` as the link between account and fund with a scoped role.
- Enforce `(fund, user)` uniqueness plus one active manager per fund at the database level.
- Create the fund and its manager membership inside `transaction.atomic()` together with an audit event.
- Scope reads by active memberships before object lookup; return 404 for unrelated fund IDs.
- Only active managers may PATCH `name`/`description` of draft funds; re-check permission and status under row lock.
- Do not attach existing users without invitation/acceptance; no membership-add API in this package.
- Keep Django Admin read-only for these models.

## Consequences

- Creation guarantees a manager in normal application workflows; no general-purpose role-edit or removal API is exposed yet.
- Database can constrain **at most one** active manager, but not **at least one**. Manager-transfer workflows must enforce the latter within a transaction.
- The first version of `AuditLog` is useful for initial traceability but not a tamper-proof ledger.
- Guest membership, transfer acceptance, financial settings, activation and advanced audit retention will require separate reviewed changes.
