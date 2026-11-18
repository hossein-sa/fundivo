# ADR 0004 — JWT session lifecycle after OTP

Status: Accepted for the first authentication implementation (review before production).

## Context

Fundivo already verifies a mobile number using Redis-backed OTP and returns a one-use 120-second login ticket. It must issue access credentials without treating the OTP or login ticket as a long-lived credential.

## Decision

- Exchange the login ticket exactly once for a signed JWT access/refresh pair.
- Use **Simple JWT** and an independent `JWT_SIGNING_KEY` loaded from an environment variable.
- Access lifetime: **5 minutes**. Refresh lifetime: **7 days**.
- Rotate and blacklist refresh tokens on refresh; the blacklist tables are managed by Django migrations.
- Logout requires a valid Bearer access token plus its owner's refresh token, and blacklists that refresh token.
- Verify that a user is active and has a verified mobile number on protected requests and refresh operations.
- Do not expose a password-based JWT issuance endpoint for normal users; OTP verification is required.
- Profile v1 exposes only the signed-in user's UUID, verified phone, and join date.

## Consequences and limits

- Revoking a refresh token does **not** revoke access tokens already issued. They remain valid until their short expiry. Logout on every device and immediate access-token revocation require additional session-revocation infrastructure.
- Clients must replace both tokens after every successful refresh; the old refresh token becomes invalid.
- Access and refresh tokens are secrets. Avoid persisting them in insecure browser storage, console history, URLs, or logs. Final front-end cookie/CSRF strategy will be designed with the frontend.
- A missing Redis service makes login ticket exchange unavailable; the JWT refresh flow continues to rely on the database blacklist.
- Use HTTPS, production secret management and monitoring before public deployment.
