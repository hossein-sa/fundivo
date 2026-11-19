# Guest sponsorship and consent (draft-only)

This module separates **beneficiary** from **sponsor / payment contact**.
Sponsorship records document an expressly accepted *proposed responsibility*;
no debts, installments, legally binding guarantee or financial ledger entries
are generated until the payment-obligation phase explicitly implements them.

## Status flow

- `pending_sponsor`: the manager nominated another registered member. That
  member must accept in their own authenticated session.
- `pending_manager`: sponsor has consented and manager must approve.
- `active`: consent and manager approval are recorded. For new requests, the
  placeholder guest membership becomes active only now.
- `rejected`: cancelled before activation; no active liability created.

The current fund manager creating a guest for **their own** accepted sponsorship
may directly create an `active` request. A regular member can create only for
themselves (`accept_responsibility=true`), entering `pending_manager`.

## API — JWT required

For `{fund_id}`:

| Method | Endpoint | Permission |
| --- | --- | --- |
| POST | `/api/v1/funds/{fund_id}/guest-sponsorships/` | Active fund member |
| GET | `/api/v1/funds/{fund_id}/guest-sponsorships/` | Manager sees all; members see sponsored guests only |
| POST | `/api/v1/funds/{fund_id}/guest-memberships/{guest_id}/sponsorship/` | Manager, old guest only |
| POST | `/api/v1/funds/{fund_id}/guest-sponsorships/{id}/accept/` | Nominated sponsor only |
| POST | `/api/v1/funds/{fund_id}/guest-sponsorships/{id}/approve/` | Manager only |
| POST | `/api/v1/funds/{fund_id}/guest-sponsorships/{id}/reject/` | Manager or nominated sponsor (pending only) |

Request for a new guest:

```json
{
  "request_id": "01010101-0202-4303-8404-050505050505",
  "guest_name": "Aunt of Ali",
  "accept_responsibility": true
}
```

Manager nomination of another member: include `sponsor_membership_id`, omit
`accept_responsibility` (or set false). The sponsor must use `/accept/` before
manager can call `/approve/`.

To attach sponsorship to an **existing** guest, manager POSTs:

```json
{
  "request_id": "20202020-3030-4404-8505-060606060606",
  "sponsor_membership_id": "00000000-0000-4000-8000-000000000000",
  "accept_responsibility": true
}
```

The sponsor UUID must be a real registered membership in the same fund; the
placeholder UUID must already be a guest. Setting consent true while naming
someone else is rejected, and the sponsor can accept only with their own JWT.
`request_id` uniquely identifies a proposal: repeat with the same parameters
returns 200, changing them returns 409. `POST` first creation returns 201.

## Safety and compatibility

- Draft fund only. Approval cannot occur in an active or paused fund.
- **No guest User record or OTP credentials are created.**
- Every request/decision is audited without logging names or tokens.
- Existing guest memberships, shares, and participation UUIDs are not
  rewritten by the migration.
- Legacy guests remain unsponsored. This is not retroactive consent.
- An inactive pending guest cannot receive a share under existing allocation
  checks. A newly approved sponsored guest can receive draft shares.
- A guest may appear in a fractional proposal only once sponsorship is active.
- Sponsor can see shares held by their sponsored guest, but does not thereby
  become the shareholder, lottery winner or beneficiary.
- A rejected new proposal leaves an inactive placeholder for audit and cannot
  be retried with a new sponsor in this version.
- An old already-active guest remains active while a proposed sponsorship is
  pending; financial obligation creation must require active sponsorship.
- Cross-fund sponsors, guest sponsors, unverified requesters, forged consent,
  repeated action calls, and non-manager approvals are rejected.

**Future**: installments + accepted liabilities, verified guest-account
claiming, sponsor reassignment with historical snapshots, payout recipients,
lottery snapshots, and post-activation invariants.
