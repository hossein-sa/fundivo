
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

OTP and JWT authentication are not implemented yet.

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
- OTP and JWT authentication
- Business API endpoints
- Resource-level authorization
- Pagination and filtering implementation
- Standardized application errors
- Financial idempotency handling
- Business endpoint tests
