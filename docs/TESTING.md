
# Fundivo — Testing Strategy

## 1. Overview

Fundivo uses automated testing to validate
application behavior, security, and financial integrity.

Status: Initial Draft

Testing is mandatory for new business functionality.

## 2. Technology Stack

- pytest
- pytest-django
- Django Test Client
- PostgreSQL 17
- Ruff
- GitHub Actions

## 3. Testing Principles

- Test observable behavior, not implementation details.
- Keep tests independent and repeatable.
- Include positive and negative test cases.
- Test financial calculations with integer IRR values.
- Test permission boundaries across different funds.
- Never rely on production data.
- Prevent tests from modifying development data.
- Fix regressions with automated tests.
- Run tests before merging changes.

## 4. Test Categories

### Unit Tests

Validate individual business rules and pure functions.

Examples:

- Fund amount calculations
- Installment amount validation
- Share eligibility rules
- State transition rules

Unit tests should avoid unnecessary database access.

### Integration Tests

Validate interactions between application components.

Examples:

- Django models and PostgreSQL
- Payment allocation persistence
- Fund membership relationships
- Database uniqueness constraints
- Transactional business services

Database integration tests must use isolated
test databases.

### API Tests

Validate HTTP contracts and authorization.

Examples:

- Request validation
- Response status codes
- Authentication requirements
- Fund-level permissions
- Serialization behavior
- Pagination and filtering
- Error responses

### Security Tests

Validate security boundaries and abuse prevention.

Examples:

- Anonymous access restrictions
- Cross-fund data isolation
- Unauthorized payment approval
- Invalid and expired OTPs
- Token expiration and revocation
- IDOR prevention
- Restricted receipt access

### Financial Integrity Tests

Validate high-risk financial operations.

Examples:

- Partial payment allocation
- Duplicate payment approval
- Payment correction history
- Installment balance calculations
- Duplicate lottery execution
- Winner eligibility
- Duplicate payout prevention
- Concurrent financial operations

Financial correctness must not depend solely
on API-level validation.

## 5. Test Organization

Current structure:

```text
backend/
├── apps/
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_infrastructure.py
└── pytest.ini
```

Future domain-specific tests may be organized
by business module.

Suggested structure:

```text
backend/tests/
├── unit/
├── integration/
├── api/
├── security/
└── financial/
```

This structure is planned and does not
represent directories already implemented.

## 6. pytest Configuration

Current configuration:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
pythonpath = .
testpaths = tests
python_files = test_*.py
addopts = -ra
```

Tests use the development settings module.

pytest-django sets DEBUG to False during
test execution by default.

API documentation routes are controlled by
API_DOCS_ENABLED independently of DEBUG.

## 7. Running Tests Locally

Run from the repository root.

Activate the virtual environment:

```powershell
.\backend\.venv\Scripts\Activate.ps1
```

Run the complete current test suite:

```powershell
python -m pytest -c backend/pytest.ini backend/tests -v
```

Run infrastructure tests:

```powershell
python -m pytest -c backend/pytest.ini backend/tests/test_infrastructure.py -v
```

Run Django system checks:

```powershell
python backend\manage.py check
```

Run Ruff:

```powershell
python -m ruff check backend
```

Validate the OpenAPI schema:

```powershell
python backend\manage.py spectacular --validate --fail-on-warn
```

## 8. Current Automated Tests

The initial infrastructure suite contains
five test cases:

1. PostgreSQL database engine configuration
2. Django REST Framework installation
3. OpenAPI schema response
4. Swagger UI availability
5. ReDoc availability

These tests have passed locally.

They do not constitute complete application
or production security coverage.

## 9. Database Testing

PostgreSQL is the primary database engine.

Database-dependent tests must use pytest-django
database access markers or fixtures.

Example:

```python
import pytest


@pytest.mark.django_db
def test_database_integration():
    # Example placeholder for a future database test.
    pass
```

This example is illustrative and must be
replaced with a meaningful assertion.

Database tests must never connect to
production databases.

pytest-django normally creates a dedicated
test database for database-enabled tests.

Test database creation requires suitable
PostgreSQL permissions.

Custom User Model implementation must
precede the first application migration.

## 10. Transaction and Concurrency Testing

Financial operations must be tested under
concurrent execution when applicable.

Test scenarios should include:

- Two requests approving the same payment
- Concurrent allocation to one installment
- Repeated lottery execution
- Concurrent payout confirmation
- Retrying the same idempotent operation

Concurrency tests may require transaction-aware
database fixtures and multiple connections.

SQLite must not be used as a substitute for
PostgreSQL when testing PostgreSQL-specific
locking or transaction behavior.

## 11. Authentication Testing

Future authentication tests must cover:

- Valid and invalid OTPs
- OTP expiration
- OTP replay prevention
- Verification attempt limits
- Authentication rate limiting
- Access token expiration
- Refresh token behavior
- Logout and token revocation

Real SMS services must not be called during
automated tests.

External services must be mocked or replaced
by controlled test implementations.

## 12. Authorization Testing

Each protected endpoint must include:

- An authorized user test
- An unauthenticated user test
- A user with insufficient permissions
- A user belonging to another fund
- An invalid or inaccessible resource test

Fund isolation is a mandatory security property.

## 13. Continuous Integration

GitHub Actions executes Backend CI for
pushes and pull requests targeting main.

The workflow currently performs:

- Repository checkout
- Python 3.12 setup
- Dependency installation
- Ruff validation
- Django system checks
- OpenAPI schema validation
- PostgreSQL connectivity verification
- pytest execution

CI uses a temporary PostgreSQL service.

CI credentials are test-only values.

No local .env file is uploaded to GitHub.

## 14. Test Data

Test data must be:

- Deterministic where possible
- Isolated between tests
- Safe to share in public repositories
- Free from real personal information
- Free from real passwords and tokens

Future fixtures should cover:

- Multiple users
- Multiple funds
- Different fund roles
- Multiple shares per membership
- Payment and installment states
- Eligible and ineligible lottery shares

## 15. Coverage Strategy

Coverage reporting is planned but has not
yet been configured.

Initial coverage goals will be defined
after domain modules are implemented.

Critical financial and authorization paths
require particularly strong test coverage.

Coverage percentage alone is not proof
of correctness.

## 16. Definition of Done

A feature is considered complete when:

- Required business behavior is implemented.
- Relevant positive tests pass.
- Relevant negative tests pass.
- Security boundaries are tested.
- Financial constraints are tested where applicable.
- Database migrations are reviewed if applicable.
- Ruff passes.
- Django system checks pass.
- OpenAPI documentation is updated.
- CI passes.
- No secrets or private data are committed.

## 17. Current Limitations

The following are not implemented yet:

- Domain-level unit tests
- Database integration tests
- Business API tests
- Financial concurrency tests
- JWT and fund-level permission tests
- Coverage reporting
- Load and performance testing

These will be added incrementally as the
corresponding features are developed.

## 18. Maintenance

Tests must evolve together with business rules.

Bug fixes should include regression tests.

CI failures must be investigated before
declaring a development milestone complete.

## OTP Test Coverage Update

`backend/tests/test_otp.py` tests OTP API contracts, invalid/expired codes,
rate limits, cooldown, inactive users, single-use code consumption, and
one-use login tickets using fakeredis. Production Redis connection is checked
separately in GitHub Actions; a real concurrency stress test remains pending.

## JWT tests (Phase 1)

`backend/tests/test_jwt_auth.py` verifies ticket exchange, no ticket replay, invalid and expired tickets, profile access, refresh rotation and blacklisting, logout authorization, and inactive/unverified user denial. Run `python -m pytest -c backend/pytest.ini backend/tests -v`. The blacklist app's migrations are applied in CI. Previous sections listing JWT tests as pending are superseded by this update.

## Funds tests — initial implemented slice

`backend/tests/test_funds.py` covers JWT authentication, member-specific roles,
cross-fund IDOR isolation, unauthorized changes, draft edits, audit events,
atomic rollback, and PostgreSQL uniqueness constraints. Run with the existing
`pytest -c backend/pytest.ini backend/tests -v` command. No separate
SQLite test path is supported for these database constraints.

## Invitation tests — Phase 3 initial slice

`backend/tests/test_invitations.py` verifies manager-only issuance, target phone
identity enforcement, code secrecy/replay protection, expiration, duplicate
membership/invitation rejection, audit and rollback, fund isolation and revocation.
Use the existing full pytest/CI workflow; no real SMS service is called.

## Shares — new tests

`backend/tests/test_shares.py` checks manager authorization, share ownership
isolation, capacity, allocation idempotency, target count edits, rejected
cross-fund membership IDs, database uniqueness constraints and atomic rollback.
Use the existing PostgreSQL-backed pytest suite and CI pipeline.
