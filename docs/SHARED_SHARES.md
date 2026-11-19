# Fundivo — Draft shared shares (v0.1)

Status: **implemented draft proposal foundation**. No installment, payment, consent,
sponsor, transfer, fund activation, or lottery execution APIs are supplied here.

## Vocabulary

- `Share`: one full participation unit and, later, at most one lottery chance per cycle.
- `ShareParticipation`: one member's precise fractional participation in a Share.
- `Share.membership`: **original allottee** for backward compatibility; not necessarily
  the current only participant. `Share.participations` is the authoritative breakdown.
- Membership `user_id = null` represents a guest. Existing solo guest shares stay intact.
  New shared proposals with guests wait for an explicit sponsorship/consent workflow.

## Integer arithmetic

Each share has exactly **12 units**. 6/12 = half; 4/12 = third; 3/12 = quarter;
2/12 = sixth; 1/12 = twelfth. Other ratios (e.g. fifths) are not supported by
this version. Values are integers, not floating-point percentages.

The transactional service validates exactly 12 units per share. PostgreSQL
checks each row's `units` is between 1 and 12 and enforces uniqueness on
`(share, membership)`. A database-wide aggregate SUM constraint is *not*
provided; direct SQL/manual Admin writes must not bypass the service layer.

## Existing data

`shares.0002_share_participations` backfills one `12/12` participation for
**every existing Share** (including guest-owned shares), keeping original UUIDs,
share number, allocation ID, and membership unchanged.

The existing `POST /api/v1/funds/{fund_id}/shares/` allocates solo shares and
creates the initial 12/12 participation in the same transaction. The original
share-capacity calculation continues to count Share rows, not participants.

## Draft API

A verified manager of a draft fund may make **one** fractional split of a
previously unsplit solo share. The original allottee must remain a participant.
Only active **registered** fund memberships may be newly proposed as co-holders.
This is an administrative **proposal**, not legal acceptance or a new payment
obligation. For activation, an explicit participant-consent and sponsor policy
must be implemented separately.

`POST /api/v1/funds/{fund_id}/shares/{share_id}/participations/`

```json
{
  "request_id": "e98821d1-a63b-4385-a807-991f5a39c72a",
  "participants": [
    {"membership_id": "eb2c7913-e855-4f0e-8d0a-c2fa1dfa9611", "units": 6},
    {"membership_id": "b14b2866-3416-44c2-a3a6-eb472988e73a", "units": 6}
  ]
}
```

First success: **201**. Same `request_id` and unchanged participants: **200**
without rewriting history. Different request or changed participants: **409**;
invalid sum/membership data: **400**. Unauthorized member: **403**; unrelated
fund: **404**. An original allottee cannot be removed through this endpoint.

`GET` on the same endpoint returns the participant UUIDs/units to a current
share participant or manager. `GET /shares/` and `GET /shares/{id}/` now include
`participations`; ordinary members can see their own *fractional* shares.

## Lottery eligibility policy (configuration only)

`PATCH /api/v1/funds/{fund_id}/` (manager, draft only):

```json
{"lottery_eligibility_policy": "fully_settled"}
```

Allowed values: `fully_settled` (default) and `allow_outstanding`. After
activation, the current Fund service rejects any draft edits with HTTP 409.
This field is **not enforced in a lottery yet**. The future installment/lottery
services must use approved payments, capture an eligibility snapshot, and
count each Share **once** regardless of partner count.

## Financial obligations (NOT implemented yet)

An eventual `Installment` is the full per-share charge. Individual partner
obligations must be represented separately and their integer IRR amounts must
sum exactly to the whole installment. For non-divisible amounts, distribute
remainders deterministically and preserve the allocation snapshot across time.
Actual payer, beneficiary, and financially responsible sponsor must remain
separate fields. No guest financial liability is inferred from its placeholder.

## Next safety milestones

- Explicit consent of all registered partners, sponsored guest responsibility
  acceptance, and fund activation validation.
- Guest-to-verified-user linking and share transfer as audited workflows.
- Append-only snapshots of ownership and responsible parties per installment
  and lottery result; no retroactive recalculation of past obligations.
- Database/service concurrency stress tests on PostgreSQL with real separate
  connections, and abuse-prevention limits for proposal endpoints.

## Calculation helper (available but not applied to actual installments)

`apps.shares.money.split_amount_irr(total_irr, units, rotation=...)` is a pure
function for future installment snapshots. E.g. `1_000_000` IRR for `[4,4,4]`
produces `[333334,333333,333333]`; changing `rotation` cycles an extra rial
across otherwise equal partners. This is *not* a payment, debt, or database
operation. Unit order must be stable and the future installments must preserve
the computed amounts rather than recalculating past rounds.
