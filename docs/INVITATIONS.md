# Fundivo — Targeted Invitations (Phase 3, first slice)

**Status: implemented API foundation, not a complete membership management workflow.**

## Purpose

Only the manager of a draft fund can issue a code for a **specific Iranian mobile number**. A recipient signs in using the normal OTP -> login-ticket -> JWT flow and **must have a verified account with exactly that mobile number** to accept or reject. A code by itself does not grant membership. Managers cannot force an individual to join a fund.

The phone number does **not** have to correspond to an existing User at issuance time; the recipient can verify that phone and create their account before acceptance. Issuing a code never creates a User.

## Security and storage

- Invitation codes are generated using `secrets.token_urlsafe(32)` (~256 bits of randomness, 43 URL-safe characters).
- The code is returned **only in the successful creation response**. Never store it in Git, documentation, URLs, logs, screenshots, or analytics.
- PostgreSQL stores the SHA-256 code digest, not the raw code. The 256-bit random secret makes offline guessing impractical.
- Recipients are identified by a per-fund HMAC-SHA256 fingerprint of the canonical mobile number using `DJANGO_SECRET_KEY`. The plaintext recipient mobile is not stored on the Invitation model or exposed in listing endpoints. Rotating the Django secret invalidates phone matching for outstanding invitations; a secret rotation plan must handle this.
- The code expires after **48 hours**. Expiration is enforced on use, regardless of whether a background cleanup task runs.
- Creating a new invitation for the same fund/recipient first closes expired pending ones, but a second unexpired pending invitation is rejected with HTTP 409.
- An issuance limit of **20 codes per fund per rolling 24 hours** limits accidental flooding. Real SMS/email delivery, IP-based abuse protection and more extensive rate limits remain future work.
- Only draft funds accept new invitations and new memberships in this slice. Active-fund onboarding requires explicit business policies.
- Recipient acceptance is a transactional operation that locks the fund and the invitation before checking it. Membership creation, status change, and audit event either all commit or all roll back.
- Database constraints prevent duplicate pending invitations for one fund/target and duplicate memberships per user/fund.
- Only a verified account with the invited phone can consume the code, and it cannot be used twice. Failed or mismatched codes do not reveal fund details.
- Members are always created with the `member` role. Managers cannot use invitation input to grant the `manager` role.

## API endpoints

All routes require `Authorization: Bearer <access_token>`.

| Method | Endpoint | Permission | Response |
|---|---|---|---|
| POST | `/api/v1/funds/{fund_id}/invitations/` | Active manager, draft fund | 201 includes `invitation_code` **once** |
| GET | `/api/v1/funds/{fund_id}/invitations/` | Active manager | 200 paginated, no code/phone |
| POST | `/api/v1/invitations/accept/` | Verified targeted user | 200, new membership |
| POST | `/api/v1/invitations/reject/` | Verified targeted user | 200, rejected status |
| POST | `/api/v1/funds/{fund_id}/invitations/{invitation_id}/revoke/` | Active manager | 200, revoked status |

### Issue a code

```json
{ "phone_number": "09120000012" }
```

The create response includes `id`, `status`, `is_expired`, `created_at`, `expires_at`, `responded_at`, and a one-time `invitation_code`. The secret code must only be shared privately with the intended recipient.

### Accept or reject

```json
{ "code": "<secret-code-from-issuer>" }
```

Acceptance returns a new membership with a `member` role. Rejection returns invitation metadata, not a fund access token. The `invitation_code` is *not* an OTP, JWT, or user identity proof.

### Errors

- `400`: malformed, expired, already-used, or wrong-recipient code (generic error, no fund information).
- `401`: missing/invalid JWT.
- `403`: authenticated member who is not a manager attempting manager-only actions.
- `404`: unrelated fund or invitation ID.
- `409`: duplicate invitation/membership, wrong fund state, or invalid revoke transition.
- `429`: issuance rate limit.

## Constraints and pending scope

The first version covers **registered verified users** and consent-based membership. Temporary/guest memberships, phone-claim recovery, share allocation, manager transfer, notification delivery, share-transfer rules, and fund activation remain pending.

There is no manual manager-driven insert of a FundMembership through the API. Django Admin continues to be read-only for financial/domain records. This initial application-level AuditLog is not a tamper-proof ledger.

## Checks

From the repository root:

```powershell
python backend\manage.py makemigrations invitations
python backend\manage.py migrate
python -m ruff check backend
python -m pytest -c backend/pytest.ini backend/tests -q
python backend\manage.py check
python backend\manage.py makemigrations --check --dry-run
python backend\manage.py spectacular --validate --fail-on-warn --file "$env:TEMP\fundivo-schema.yaml"
```

## Accepted memberships and shares

Once an invitation is accepted, the resulting active registered membership
can receive one or more shares from the fund manager during draft. Issuing or
accepting an invitation does not automatically allocate shares. See
[SHARES.md](SHARES.md).

## Guests are not invitations

The separate guest placeholder feature does not automatically convert into a
registered member, even if a later verified account has a similar name.
Invitation acceptance keeps using the verified-user flow; claiming guest shares
requires a future explicitly approved workflow.
