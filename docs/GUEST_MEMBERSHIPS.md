# Fundivo — Guest memberships (initial slice)

**Status:** Implemented for draft funds only; guest account claiming and share transfers are **not** implemented.

A manager can record a guest for a person who does not have a verified Fundivo account. This is an **administrative placeholder**, not an authenticated identity. No `User` object, OTP, or JWT is created, and the guest cannot directly call APIs. A guest has no fund-management powers.

## API

`POST /api/v1/funds/{fund_id}/guest-memberships/` (manager only)

```json
{"guest_name": "Sample Guest"}
```

Returns HTTP `201` with a membership representation containing an `id`, `user_id: null`, `guest_name`, `is_guest: true`, `role: "member"`, `is_active: true`, and `joined_at`.

`GET /api/v1/funds/{fund_id}/memberships/` (manager only) includes registered and guest memberships. Registered memberships have `user_id` set and `guest_name` empty. Other users cannot create guests, and nonmembers receive 404.

## Rules and limitations

- Draft funds only; the fund manager's membership must be active.
- Names are trimmed, required, at most 120 characters. Duplicate guest names are permitted; use the membership UUID to distinguish people.
- A guest can receive draft shares using the **existing** manager-only share allocation endpoint and its existing capacity and idempotency controls.
- Adding a guest is audited and transactional. The audit record records the field name but not the guest's name.
- Guest membership is not an invitation. It must **never** automatically bind to a registered account based on an entered or matching name or phone number.
- There is no public guest signup/claim endpoint; consent and verification rules must be specified before implementing conversion.
- There is no edit, removal, share transfer or fund exit API for guest records. Guest shares should not be re-assigned by editing foreign keys.
- Once rounds/obligations exist, financial history and ownership transitions will need independent immutable records.

## Data model

`FundMembership.user` is nullable for guests. `guest_name` is blank for registered memberships and required for guests. A database check forbids guest managers and enforces these two representations. PostgreSQL's `UNIQUE (fund, user)` still prevents duplicate registered memberships while permitting multiple null-user guest memberships.

## Testing

The suite tests authenticated manager creation, nonmanager/outsider restrictions, no user account creation, draft-only behavior, response shape, validation, database check constraints, atomic audit rollback, and allocation of a draft share to a guest.

## Approved sponsorship

For financial responsibility, use the separate [sponsorship request and approval workflow](GUEST_SPONSORSHIP.md). The old manager-only guest creation endpoint remains for compatibility and does not imply anyone has accepted financial responsibility.
