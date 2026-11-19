
# Fundivo — Security Architecture

## 1. Overview

Fundivo manages community savings and interest-free
lending groups.

The platform records financial transactions but
does not directly hold or transfer users' money.

Security is a core requirement of the project.

Status: Initial Draft
Security Review: Pending

This document distinguishes implemented security
controls from planned requirements.

## 2. Security Principles

Fundivo follows these principles:

- Deny access by default.
- Apply the principle of least privilege.
- Enforce fund-level data isolation.
- Never trust client-provided authorization data.
- Keep secrets outside version control.
- Preserve financial history and auditability.
- Validate all external inputs.
- Prevent duplicate financial operations.
- Protect sensitive personal information.
- Use secure defaults in production.

## 3. Authentication

### Current Implementation

Django REST Framework is configured with:

- SessionAuthentication
- IsAuthenticated as the default permission

Business authentication APIs have not been
implemented yet.

### Planned Authentication

Authentication will use:

- Verified mobile phone numbers
- One-time passwords (OTP)
- JWT access tokens
- JWT refresh tokens
- Secure logout and token revocation

### OTP Security Requirements

OTP verification must include:

- Short expiration periods
- Limited verification attempts
- Rate limiting per phone number and client
- Secure random code generation
- Prevention of OTP reuse
- Protection against account enumeration
- Safe delivery through an SMS provider

OTP codes must never appear in application logs,
API responses, or exception messages.

Exact expiration times and rate limits must be
defined before implementing authentication.

### Token Security

JWT implementation must consider:

- Short-lived access tokens
- Refresh token expiration
- Refresh token rotation where appropriate
- Token revocation
- Secure signing keys
- Protection against token replay
- Secure client-side token storage

Final token lifetime and revocation policies
remain OPEN.

## 4. Authorization

### Fund-Level Roles

Fundivo distinguishes between:

- Platform Administrator
- Fund Manager
- Fund Member

Fund Manager and Fund Member roles are scoped
to individual funds through FundMembership.

A user's role in one fund must not grant
permissions in another fund.

### Object-Level Authorization

Every business endpoint must validate:

1. The authenticated user.
2. Membership in the relevant fund.
3. The user's role in that fund.
4. Permission to access the requested resource.

Knowing a resource UUID must not grant access.

Querysets must be scoped to authorized resources.

### IDOR Protection

Fundivo must prevent Insecure Direct Object
Reference vulnerabilities.

For example:

- A member of Fund A must not access Fund B.
- A member must not approve unauthorized payments.
- A member must not read another user's private receipt.
- A manager must not manage an unrelated fund.

Negative permission tests are mandatory.

Authorization enforcement is pending
implementation of the business modules.

## 5. Financial Data Security

Financial records require strong integrity
guarantees.

### Monetary Representation

- Store financial amounts as integer IRR values.
- Never use floating-point values for money.
- Validate domain-defined financial constraints.

### Transaction Integrity

Sensitive financial operations must use:

- Database transactions
- Appropriate row-level locking
- Database uniqueness constraints
- Idempotency protection
- Audit logging

### Payment Verification

Only approved payments may affect
installment balances.

Pending and rejected payments must not
reduce financial obligations.

### Financial Corrections

Approved financial history must not be
silently overwritten or deleted.

Corrections must preserve a traceable history
through approved compensating operations.

### Concurrent Operations

Concurrent requests must not create:

- Duplicate effective payments
- Duplicate payment allocations
- Duplicate valid lottery results
- Duplicate payout settlements

These requirements will be implemented and
tested during the relevant business phases.

## 6. Lottery Security

Lottery execution must provide:

- Secure server-side randomness
- Atomic execution
- Appropriate database locking
- Duplicate execution prevention
- An auditable eligibility snapshot
- Recorded execution metadata
- Immutable or historically traceable results

Each share may win at most once within
the same fund cycle.

The platform must not claim public
cryptographic fairness verification unless
such a mechanism is actually implemented.

Lottery security implementation is pending.

## 7. File Upload Security

Payment receipts may contain private
financial and personal information.

Future receipt uploads must enforce:

- File size limits
- Allowed file types
- Content validation
- Safe generated filenames
- Restricted storage access
- Authorized download endpoints
- Protection against malicious file execution
- Safe handling of file metadata

Client-provided filenames and MIME types
must not be trusted without validation.

Publicly accessible receipt URLs must not
expose private financial data.

The final storage provider and file limits
remain OPEN.

## 8. Secrets Management

### Current Implementation

Django configuration reads sensitive values
from environment variables.

The local development environment uses:

`backend/.env`

The file is ignored by Git.

A safe configuration template is maintained in:

`backend/.env.example`

### Security Requirements

Never commit:

- Django secret keys
- Database passwords
- JWT signing keys
- SMS provider credentials
- Production access tokens
- Private encryption keys

Production secrets must be managed through
a secure deployment mechanism.

If a secret is exposed, it must be revoked
or rotated promptly.

Git ignore rules do not protect secrets
already committed to version control.

## 9. Development and Production Security

### Development

The development environment uses:

- Django running locally
- PostgreSQL inside Docker
- Local environment variables
- API documentation enabled

Development settings must not be deployed
as production settings.

### Production

The production settings currently include:

- DEBUG disabled
- HTTPS redirection enabled
- Secure session cookies
- Secure CSRF cookies
- API documentation disabled by default

Production deployment is not yet configured.

Before deployment, review:

- ALLOWED_HOSTS
- CSRF_TRUSTED_ORIGINS
- Reverse proxy configuration
- Secure proxy headers
- HSTS configuration
- HTTPS certificate management
- Static and uploaded file serving
- Database network access
- Secret storage
- Logging and monitoring

Django's deployment security checks must
be executed before production release.

## 10. Rate Limiting

Authentication and sensitive operations
require rate limiting.

Planned protected operations include:

- OTP requests
- OTP verification
- Authentication retries
- Invitation validation
- Sensitive financial API requests

Rate limiting must consider distributed
deployments and concurrent requests.

The implementation and thresholds
remain pending.

## 11. Audit Logging

Sensitive actions must generate audit records.

Examples include:

- Membership and role changes
- Fund configuration changes
- Share transfers
- Payment approval and rejection
- Payment corrections
- Lottery execution
- Lottery result corrections
- Payout settlement
- Sensitive administrator actions

Audit records should include:

- Actor
- Timestamp
- Action
- Target resource
- Relevant changes
- Fund context when applicable

Audit logs must not contain passwords,
OTP codes, access tokens, or unnecessary
personal information.

Audit logging is not implemented yet.

## 12. Django Admin Security

Django Admin is intended for internal
platform administration.

Requirements include:

- Restricted staff access
- Minimum necessary permissions
- Controlled sensitive operations
- Auditing of administrative actions
- Prevention of financial rule bypasses

The default Django Admin must not be treated
as a completed production administration system.

## 13. Database Security

PostgreSQL is the primary database.

The development database currently runs
inside Docker.

The database port is bound to localhost.

Production requirements include:

- Restricted database network access
- Dedicated application credentials
- Least-privilege database permissions
- Secure credential management
- Encrypted connections where required
- Regular backups
- Backup restoration testing

Backup and restoration procedures are pending.

## 14. Logging and Error Handling

Application logs must not reveal:

- Passwords
- OTP codes
- JWT tokens
- Secret keys
- Private receipt contents
- Unnecessary personal information

Production API responses must not expose
internal tracebacks or infrastructure details.

Monitoring and incident-response procedures
will be defined before deployment.

## 15. Security Testing

Security tests must cover:

- Unauthenticated API access
- Role-based authorization
- Cross-fund access restrictions
- IDOR prevention
- OTP abuse and expiration
- JWT expiration and revocation
- Duplicate financial requests
- Concurrent financial operations
- Lottery duplicate execution
- Receipt access restrictions
- Unauthorized administrator actions

Each sensitive feature must include
appropriate negative tests.

## 16. Current Security Status

Implemented:

- Environment-based Django secret management
- Git ignore rules for local secrets
- Default DRF authentication and permissions
- Separate development and production settings
- Basic production HTTPS security settings
- PostgreSQL bound to localhost in development
- Automated Ruff and Django checks in CI

Not yet implemented:

- JWT authentication and revocation
- Fund-level object permissions
- Business API rate limiting
- Financial audit logging
- Financial idempotency controls
- Secure receipt handling
- Production deployment hardening
- Backup and recovery procedures
- Comprehensive security testing

## 17. Security Review Requirements

Before production deployment:

- Complete authentication security testing.
- Verify cross-fund permission isolation.
- Review financial integrity constraints.
- Verify receipt access controls.
- Run Django deployment checks.
- Review production secret management.
- Configure HTTPS and monitoring.
- Test backup restoration.
- Review applicable legal and privacy obligations.

This document must be updated whenever
security-sensitive functionality changes.

## OTP Security Update

OTP rate limiting, hashed challenges in Redis, limited attempts, and one-use
verification are implemented for local development. Codes are visible only
through an ignored local outbox, not in API responses/logs. JWT issuance,
production SMS, and production-grade abuse controls remain pending.
See `docs/OTP.md`.

## Phase 1 JWT implementation update

Simple JWT bearer authentication, refresh rotation, PostgreSQL-backed refresh-token blacklisting, and ticket exchange are implemented. An independent `JWT_SIGNING_KEY` is required. Protected requests and refreshes reject inactive or unverified users. Logout revokes only the supplied refresh token, **not** outstanding access tokens: access tokens remain valid for at most five minutes after issue. Immediate logout from all devices, production hardening, and secure browser token transport are not implemented. Prior status lists marking JWT as pending are superseded by this update. See `docs/JWT.md`.

## Funds authorization — initial implemented controls

All funds endpoints use existing verified JWT authentication. Fund read
querysets require active membership; unrelated fund UUIDs return 404.
Only active managers may list memberships or edit drafts. Membership list
responses do not expose phone numbers. Database constraints protect against
duplicate memberships and concurrent second active managers. Audit logging
is initial application-level history, not an immutable financial ledger.

## Invitation security — implemented initial scope

Random code digest only in PostgreSQL, phone-bound HMAC fingerprint (not plaintext
recipient phone), verified JWT recipient acceptance, transactional one-use
execution, fund-level authorization, audit without code/phone, 48-hour expiration,
and basic fund-scoped issuance rate limiting. Do not share invitation codes in
logs, public links or issue tracker screenshots. Production notifications, IP-based
abuse controls, and secure code delivery remain pending.

## Shares — initial security controls

Managers alone may allocate shares; active members can view only their own
shares, while managers can view all. Foreign fund membership IDs return 404.
A fund-level PostgreSQL lock serializes allocations and protects capacity.
Allocation IDs protect against accidental duplicate API retries. Assignment
and audit occur in one database transaction. This does not yet provide an
immutable financial ledger or complete share-transfer security.

## Guest access boundary

Guest records have no User or tokens and cannot authenticate. Creation requires
an active verified manager and draft fund. Public request fields cannot set
role or user identity. A database constraint blocks guest managers. Claims
based solely on name or phone are forbidden; future linking needs explicit
verification and acceptance. Audit logs exclude the guest name itself.

Draft shared-share proposals are manager-only, fund-scoped, one-time, audit logged, and do not confer consent or financial liability. See [Shared Shares](SHARED_SHARES.md).

## Sponsorship security

Fund-scoped visibility: manager sees sponsorships, sponsor sees their own. Other members and outsiders cannot inspect or approve. A manager cannot accept consent for someone else. No guest tokens, phone identities, or unverified guest account linking. Shared participation requires active sponsorship for a guest.
