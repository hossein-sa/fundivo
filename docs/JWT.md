# Fundivo — JWT Session Authentication

Status: Phase 1 implementation (requires local tests and CI confirmation).

## Flow

1. `POST /api/v1/auth/otp/request/` with `{ "phone_number": "09123456789" }`.
2. `POST /api/v1/auth/otp/verify/` with `{ "phone_number": "09123456789", "code": "123456" }` (replace with actual OTP); receives a short-lived, one-use `login_ticket`.
3. `POST /api/v1/auth/token/exchange/` with `{ "login_ticket": "..." }` returns:

```json
{
  "access": "<signed access JWT>",
  "refresh": "<signed refresh JWT>",
  "token_type": "Bearer",
  "expires_in": 300
}
```

4. Call `GET /api/v1/auth/me/` with `Authorization: Bearer <access>` for the read-only user profile.
5. Call `POST /api/v1/auth/token/refresh/` with `{ "refresh": "..." }`. A *new* refresh and access token are returned; discard the old refresh token immediately.
6. Call `POST /api/v1/auth/logout/` with the user's valid Bearer access token and `{ "refresh": "..." }`. The supplied refresh token is blacklisted and the endpoint responds `204`.

All examples contain placeholders; **never** publish actual credentials or tokens.

## Token lifetimes and constraints

- Access JWT: 5 minutes.
- Refresh JWT: 7 days, with rotation and PostgreSQL-backed blacklisting.
- Login ticket: 120 seconds, one use, stored as a digest in Redis.
- Issuance requires a verified and active user.
- Protected requests and refresh validation reject inactive or unverified users.
- Password-based JWT login is intentionally not exposed.

## Security limitations

- Logout only invalidates **the submitted refresh token**. Previously issued access tokens remain usable until they expire. Future all-device logout needs session-level revocation/versioning.
- JWTs are bearer secrets; possession grants access. Never put them in a URL, console output, Git, or logs.
- For a future browser frontend, choose secure transport and storage (e.g., HttpOnly/Secure cookies and CSRF strategy, or carefully hardened in-memory handling) before deployment.
- Production: HTTPS, independent signing key, SMS provider, monitoring and token cleanup are required.
- Running `python backend/manage.py migrate` creates Simple JWT blacklist tables. Periodically run `python backend/manage.py flushexpiredtokens` (the schedule is a deployment concern).

## Local setup

Generate and store a **different** `JWT_SIGNING_KEY` than `DJANGO_SECRET_KEY` in the ignored `backend/.env`. Install dependencies from `backend/requirements.txt`, then run Django migrations, tests, Ruff and OpenAPI validation. Do not add the private `backend/.env` to Git.

## Testing

`backend/tests/test_jwt_auth.py` covers the authentication flow, authorization boundaries, refresh rotation/blacklisting, token replay, inactive/unverified users and logout. The tests use fakeredis for OTP; the refresh token blacklist uses the PostgreSQL test database.
