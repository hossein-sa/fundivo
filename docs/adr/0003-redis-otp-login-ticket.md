# ADR 0003 — Redis OTP and one-time login ticket

Status: **Accepted for development; production delivery remains unresolved**

## Context

Fundivo uses a custom user model with Iranian mobile numbers, without user passwords. OTP requires expiration, bounded attempts, protection from concurrent replay, and a future JWT integration. Financial identities and phone numbers should not be exposed in Redis key names.

## Decision

- Use ephemeral Redis for OTP challenges, rate counters and a one-use login ticket.
- Store the code using an HMAC digest derived with Django `SECRET_KEY`; never log the clear-text code.
- Use `WATCH/MULTI/EXEC` to atomically consume a successful verification or decrement the retry counter.
- Issue a short-lived login ticket only after the OTP is consumed and the account is verified; the ticket is **not an access token**.
- Permit only a development-only file outbox for local delivery; production adapter is disabled until SMS vendor selection.
- Do not add Celery to this stage; it will be evaluated for retries/notifications later.

## Consequences

Redis is required by the authentication endpoints. A Redis outage fails closed. A loss of Redis state invalidates outstanding challenges and login tickets; users request a new code. Simple fixed-window limits are a starting point rather than production abuse protection. The next phase must atomically consume the ticket before issuing JWTs, and must validate user activity at redemption time.
