# ADR 0006 — Fund-specific, mobile-bound invitation codes

**Status:** Accepted for Phase 3's initial invitation slice (review for production rollout).

## Context

Fundivo allows a manager to invite participants, but a manager cannot silently enroll people. A shared invitation link alone may be forwarded, and a raw phone number in an Invitation record is unnecessary personal data. Users authenticate by verified Iranian mobile number.

## Decision

Generate one random 256-bit invitation code and expose it only at creation. Persist a SHA-256 digest rather than the code. Bind the invitation to a per-fund HMAC fingerprint of the invited canonical mobile. Accept/reject only from the verified JWT account whose current phone matches the fingerprint. Require a draft fund. Use transactions and row locking to protect one-use behavior, and audit issuance/acceptance/rejection/revocation without secrets or private phone numbers.

## Consequences

- A forwarded code cannot be accepted by a different verified phone identity.
- Invitations can be issued before a recipient creates their verified account, without creating phantom users.
- Service operators cannot retrieve a lost raw code from PostgreSQL; a manager must revoke and reissue.
- Secret rotation invalidates pending phone fingerprints unless a versioned migration/overlap scheme is added.
- A 48-hour lifetime and fund-level 20-per-day limit are preliminary business/security defaults.
- Guest memberships, share allocation, sender notifications, management transfer, and advanced anti-abuse controls remain future work.
