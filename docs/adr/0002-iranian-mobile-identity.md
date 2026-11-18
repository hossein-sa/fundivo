# ADR 0002 — Canonical Iranian Mobile Identity

Status: Accepted as an initial MVP convention (revisit for international expansion)

## Context

Fundivo authenticates users through a verified mobile number instead of a username.
The MVP currently uses IRR and primarily targets Iranian community funds.
Different textual forms of one number must not produce different accounts.

## Decision

- Use a custom `accounts.User` model before the first migration.
- Use a UUID primary key and a unique `phone_number` field.
- Accept Iranian mobile formats `09XXXXXXXXX`, `+989XXXXXXXXX`,
  `00989XXXXXXXXX`, and `989XXXXXXXXX`, including Persian/Arabic digits.
- Store the canonical form `+989XXXXXXXXX`.
- Reject invalid numbers. Regular accounts start with `is_phone_verified=False`
  and an unusable password; OTP verification will be implemented separately.
- Platform administrators can use Django's password-based administrative login.
- Keep fund manager/member roles outside `User` in the future `FundMembership` model.
- Register users in Django Admin as read-only until secure audited editing exists.

## Consequences and limitations

- Identity is currently Iran-specific; international phone numbers require a
  deliberate normalization and migration plan.
- Phone verification and OTP registration are **not** implemented by this change.
- Changes to a verified phone number require a dedicated secure workflow.
- Normalization is performed on ordinary model saves and manager creation;
  bulk writes and direct SQL must not bypass the approved identity workflow.
