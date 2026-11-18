
# Fundivo — System Architecture

## Overview

Fundivo is a platform for managing community savings
and interest-free lending groups.

The platform records and tracks financial activities.
It does not hold or transfer users' money.

## Architecture Style

Fundivo uses a Modular Monolith architecture.

The backend is a single Django application composed
of logically separated business modules.

## Technology Stack

- Python 3.12
- Django 5.2 LTS
- Django REST Framework
- PostgreSQL 17
- Docker Compose
- pytest and pytest-django
- Ruff
- drf-spectacular

## Repository Structure

- `backend/`: Django API and business logic
- `backend/apps/`: Domain modules
- `backend/config/`: Django configuration
- `backend/tests/`: Automated tests
- `infra/`: Future infrastructure configuration
- `docs/`: Architecture and technical documentation
- `compose.yaml`: Local PostgreSQL service
- `frontend/`: Future web application

## Application Layers

### API Layer

Handles HTTP requests, serializers, authentication,
permissions and responses.

### Service Layer

Contains business operations and transactional logic.

### Data Layer

Contains Django models, database constraints,
queries and persistence logic.

Business-critical operations should not be
implemented directly inside API views.

## Planned Domain Modules

- Users and Authentication
- Funds and Memberships
- Invitations and Shares
- Rounds and Installments
- Payments and Allocations
- Lotteries and Results
- Payouts
- Notifications
- Audit Logs and Reports

These modules are planned and are not yet implemented.

## Data Principles

- PostgreSQL is the primary database.
- Public identifiers use UUIDs.
- Financial amounts are stored as integer IRR values.
- Timestamps are timezone-aware and stored in UTC.
- Business integrity is enforced through database
  constraints and transactional operations.
- Financial records require an auditable history.

## Security Principles

- Authentication is required by default.
- Fund permissions are scoped to individual funds.
- Secrets must not be committed to Git.
- Financial operations must prevent duplicate execution.
- Sensitive actions must be auditable.
- Uploaded receipts must have restricted access.

## Development Environment

Django runs locally on Windows through PyCharm.

PostgreSQL runs inside Docker and is accessible
through 127.0.0.1:5433.

Development and production settings are separated.

## Continuous Integration

GitHub Actions runs automated checks for:

- Code quality with Ruff
- Django configuration
- OpenAPI schema validation
- PostgreSQL connectivity
- Automated tests with pytest

## Current Limitations

- Business domain modules are not implemented.
- Authentication and authorization flows are pending.
- Custom User Model is not implemented.
- Initial database migrations have not been run.
- Production deployment is not configured.
- Frontend development has not started.

## Funds module (implemented initial slice)

The `apps.funds` module contains `Fund`, `FundMembership` and `AuditLog`.
Fund creation and draft edits use a service layer with database transactions;
fund-level querysets enforce access isolation. See [FUNDS.md](FUNDS.md).

## Invitation module — initial implementation

`apps.invitations` owns the invitation record, token hashing, recipient identity
binding, transaction-safe consent workflows, HTTP serializers and views.
The fund model/membership roles stay in `apps.funds`. See [INVITATIONS.md](INVITATIONS.md).

## Shares module — implemented initial slice

The `apps.shares` domain stores individual participation units, separate
from user identity and membership role. Allocations are managed by a service
with fund row locking and audit logging; non-manager reads are restricted to
shares owned by their membership. See [SHARES.md](SHARES.md).
