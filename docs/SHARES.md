# Fundivo — Participation Shares (initial slice)

## Status

Implemented foundation for **active registered memberships in draft funds**.
No financial obligation, round, transfer, guest member, payment or activation
logic is implemented here.

## Domain decisions

A share represents exactly one participation unit. Its owner is a
`FundMembership`, not the global `User`; the same member can own several shares.
Managers can manage a fund without owning any. A UUID uniquely identifies the
share publicly and a sequential number distinguishes it inside its fund.

The draft fund may define `target_share_count` (a positive number). A manager
must set a target before assigning shares. New assignments may not exceed it.
Changing target count is allowed only in a draft and never below the number
of issued shares. This is a **count**, not a money amount.

## API

All endpoints require verified JWT authentication.

| Method | URL | Behavior |
| --- | --- | --- |
| PATCH | `/api/v1/funds/{fund_id}/` | Manager sets `target_share_count` while draft |
| GET | `/api/v1/funds/{fund_id}/shares/` | Manager: all, member: own only |
| GET | `/api/v1/funds/{fund_id}/shares/{share_id}/` | Manager or share owner |
| POST | `/api/v1/funds/{fund_id}/shares/` | Manager allocates to active membership |

Example create request:

```json
{
  "membership_id": "00000000-0000-4000-8000-000000000001",
  "count": 2,
  "allocation_id": "00000000-0000-4000-8000-000000000002"
}
```

The client generates a **new random UUID** as `allocation_id` for every new
allocation intent. Retrying the *same* HTTP operation must reuse its ID.
Success returns `201 Created` with a `shares` array. Replaying the same
allocation ID with identical inputs returns `200 OK` and the original array.
Reusing the ID with conflicting inputs returns `409 Conflict`. Capacity and
fund-state conflicts return `409`. Invalid input returns `400`. A manager
may allocate from 1 to 20 shares in one request.

No raw phone number or member contact information appears in share responses.
A member cannot view another member's shares. Unrelated funds and invisible
share IDs return `404`. Only an active manager can allocate shares (`403` for
other members); anonymous requests receive `401`.

## Concurrency and consistency

The allocation service locks the parent Fund row using PostgreSQL
`SELECT FOR UPDATE`, so concurrent allocations cannot both pass a capacity
check. A unique `(fund, number)` constraint provides another safeguard.
The `allocation_id` groups all shares created in one atomic operation and
allows safe retries. Audit logging is included in the transaction.

The service ensures the membership belongs to the same fund; the two ordinary
foreign keys alone do not form a database-level composite FK constraint.
Direct model writes outside the service are not a supported business API.

## Open decisions / next work

- Guest membership identity, linking to a verified account and acceptance
- Share transfers and withdrawals with preserved obligations
- Fund financial settings and currency/amount invariants
- When allocations become immutable after activation and what correction means
- Round creation, installments, winner selection and settlement

No migration or API in this slice silently implements those policies.

## Guest-owned draft shares

A draft share may be allocated to a guest membership by its UUID using the
existing allocation service and capacity/idempotency rules. This does not grant
login access or imply a verified identity; transfer and claiming are pending.

Shared draft participation (12 integer units/share) is described in [SHARED_SHARES.md](SHARED_SHARES.md).
