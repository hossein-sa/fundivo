
# Fundivo — REST API Documentation

## 1. Overview

Fundivo provides a versioned REST API for managing
community savings and interest-free lending groups.

Status: Draft v0.1

This document distinguishes implemented API
infrastructure from planned API contracts.

## 2. API Conventions

### Base URL

All business API endpoints will be versioned under:

`/api/v1/`

### Data Format

- Request and response format: JSON
- Character encoding: UTF-8
- Public identifiers: UUID
- Monetary amounts: integer Iranian rials (IRR)
- Date and time: ISO 8601 with timezone information
- Stored timestamps: UTC
- No floating-point monetary values

### HTTP Methods

- GET: Retrieve resources
- POST: Create resources or execute operations
- PATCH: Partially update resources
- DELETE: Remove resources where explicitly permitted

Financial history must not be destructively deleted.

### HTTP Status Codes

| Status | Meaning |
| --- | --- |
| 200 | Successful request |
| 201 | Resource created |
| 204 | Successful request without response body |
| 400 | Invalid request |
| 401 | Authentication required or invalid credentials |
| 403 | Insufficient permissions |
| 404 | Resource not found or intentionally concealed |
| 409 | Resource state conflict |
| 429 | Request rate limit exceeded |
| 500 | Unexpected server error |

The final status behavior of each endpoint must be
documented and tested during implementation.

## 3. Current Implementation

The following development documentation endpoints
are implemented:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/v1/schema/ | OpenAPI schema |
| GET | /api/v1/docs/ | Swagger UI |
| GET | /api/v1/redoc/ | ReDoc |

Documentation routes are controlled by the
`API_DOCS_ENABLED` setting.

They are enabled in development and disabled
in production by default.

### Current Authentication

Django REST Framework currently uses:

- SessionAuthentication
- IsAuthenticated as the default permission

OTP verification and JWT session endpoints are implemented.

No business-domain endpoints are available yet.

## 4. Planned Authentication

The planned authentication system includes:

- Mobile phone verification
- One-time passwords (OTP)
- Access tokens using JWT
- Refresh tokens
- Logout and token revocation
- Rate limiting and OTP attempt restrictions

The final endpoint paths, payloads, and token
lifetime policies will be defined in Phase 1.

Authentication endpoints will use narrowly scoped
anonymous access where required.

## 5. Authorization

Permissions are scoped to individual funds.

A user may have different roles in different funds.

Fund roles are represented through FundMembership.

Planned roles include:

- Fund Manager
- Fund Member

Platform administration is separate from
fund-level membership permissions.

All resource access must validate authorization
at the object level.

Knowing a resource UUID does not grant access.

Querysets must exclude unauthorized fund resources.

## 6. Planned API Modules

| Module | Purpose |
| --- | --- |
| auth | Authentication and sessions |
| users | User profiles |
| funds | Fund management |
| memberships | Fund memberships |
| shares | Participation shares |
| invitations | Membership invitations |
| rounds | Fund rounds |
| installments | Financial obligations |
| payments | Payments and allocations |
| lotteries | Winner selection |
| payouts | Winner settlements |
| notifications | User notifications |
| reports | Financial reports |

These modules are planned, not implemented.

## 7. Example Future Endpoint

The following is an illustrative design proposal,
not an active or finalized API contract.

### Create Fund

`POST /api/v1/funds/`

Authentication: Required (planned JWT)

Authorized role: Verified registered user

Request body:

```json
{
  "name": "Family Savings Fund",
  "description": "A community savings group"
}
```

Proposed successful response:

HTTP 201 Created

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Family Savings Fund",
  "description": "A community savings group",
  "status": "draft"
}
```

Possible errors:

- 400: Invalid fund data
- 401: Authentication failure
- 429: Rate limit exceeded

Fund creation will automatically assign the creator
as the manager of that fund.

Required financial parameters, field validation,
duplicate-request behavior, and final response
structure remain to be specified in Phase 2.

## 8. Error Responses

Error responses must be consistent, safe,
and understandable to API consumers.

Current DRF errors may use its standard
`detail` response field.

Example of a typical DRF error:

```json
{
  "detail": "Authentication credentials were not provided."
}
```

A project-wide error schema, field-level validation
format, and stable application error codes
remain OPEN design decisions.

Internal tracebacks, secrets, OTP codes, and tokens
must never appear in public error responses.

## 9. Pagination and Filtering

List endpoints must support pagination where
appropriate.

Filtering and ordering must be explicitly restricted
to supported fields.

Planned examples include:

- Fund status filtering
- Payment status filtering
- Round filtering
- Date-range filtering
- Report pagination

Pagination strategy, page-size limits, and exact
query parameter names remain OPEN.

## 10. Idempotency and Concurrency

Sensitive financial operations must prevent
duplicate effective execution.

This includes:

- Payment approval and correction
- Lottery execution
- Payout settlement
- Other non-repeatable financial actions

Implementation must consider:

- Database transactions
- Appropriate locking
- Unique constraints
- Request retries
- Concurrent requests
- Audit history

Idempotency-key format, retention policy,
and operation-specific retry responses remain OPEN.

## 11. API Documentation Requirements

Every implemented endpoint must document:

- HTTP method and URL
- Authentication requirements
- Authorized roles
- Path and query parameters
- Request body
- Successful response
- Validation and error responses
- Resource-level permissions
- Idempotency behavior where applicable

OpenAPI must be updated together with the code.

## 12. Security Requirements

- Deny unauthorized access by default
- Enforce fund-level object permissions
- Prevent cross-fund data exposure
- Protect payment receipts
- Rate-limit authentication operations
- Use HTTPS in production
- Never expose secrets in responses or logs
- Audit sensitive financial operations

## 13. Implementation Status

Implemented:

- Django REST Framework integration
- Versioned documentation routes
- OpenAPI schema generation
- Swagger UI and ReDoc
- Default authentication and permission settings
- Basic infrastructure tests

Pending:

- Custom User Model
- JWT authentication and refresh/logout
- Business API endpoints
- Resource-level authorization
- Pagination and filtering implementation
- Standardized application errors
- Financial idempotency handling
- Business endpoint tests

## OTP API Update

The OTP request and verification endpoints are now implemented in Phase 1.
See `docs/OTP.md` for request/response examples, status codes, limits,
and login-ticket behavior. JWT access/refresh/logout are implemented; see docs/JWT.md.

## Phase 1 JWT API (implemented)

- `POST /api/v1/auth/token/exchange/`: consumes a one-use OTP `login_ticket`; returns `access`, `refresh`, `token_type`, `expires_in`.
- `POST /api/v1/auth/token/refresh/`: consumes a refresh token, rotates it, and returns a new access/refresh pair.
- `POST /api/v1/auth/logout/`: requires `Authorization: Bearer <access>` and that user's refresh token; blacklists the supplied refresh token; returns 204.
- `GET /api/v1/auth/me/`: authenticated user's read-only identity profile.

JWT Bearer is now the default DRF authentication backend. Previous planning notes about JWT being pending are superseded by this section. See `docs/JWT.md` for request examples and limitations.

## Initial Funds API — implemented

See [FUNDS.md](FUNDS.md) for permission rules, request/response examples and
current limitations. Endpoints under `/api/v1/funds/` are JWT-protected:
GET/POST list/create, GET/PATCH detail, GET own membership and GET memberships
(manager only). List responses are paginated. Fund status and role are not
client-writeable. Non-members receive 404 for protected fund resources.

## Invitation API — initial implementation

Authenticated fund managers can issue/list/revoke invitation codes for draft funds.
Verified recipients accept or reject using a code. See [INVITATIONS.md](INVITATIONS.md)
for endpoints, access rules, errors, security constraints and limitations.

## Shares API — draft allocations

`PATCH /api/v1/funds/{fund_id}/` accepts `target_share_count` for a draft fund.
`GET /api/v1/funds/{fund_id}/shares/` returns a paginated list: managers see all
shares, regular members only their own. `GET /api/v1/funds/{fund_id}/shares/{share_id}/`
enforces the same scope (nonvisible shares return 404).
Managers allocate via `POST /api/v1/funds/{fund_id}/shares/` with JSON
`{"membership_id": "<uuid>", "count": 2, "allocation_id": "<new-uuid>"}`.
Initial success returns 201; the same request ID and matching inputs return
200 without additional shares. Conflicting reuse or exceeded capacity returns
409. Allocation is limited to active memberships and draft funds.

## Guest membership API (initial implementation)

Manager-only `POST /api/v1/funds/{fund_id}/guest-memberships/` accepts
`{"guest_name": "Sample Guest"}` and returns `201` with membership UUID,
`user_id: null`, `is_guest: true`, `guest_name`, and `role: "member"`.
Existing manager-only membership list now includes guest records. This is not
an invitation, nor a user account registration flow.

See [Shared Shares](SHARED_SHARES.md) for the draft share participation endpoint and its authorization contract.
