# ADR-0001: Use a Modular Monolith for the Fundivo backend

- **Status:** Accepted for the initial backend implementation
- **Date:** 2026-11-18
- **Scope:** Backend architecture

## Context

Fundivo manages funds, memberships, shares, installments, recorded payments, lotteries, payouts, notifications, and audit trails. These domains are related, particularly around transactional correctness and fund-level access control. The initial team and product scope do not justify the operational complexity of independent services.

## Decision

Build one Django backend deployed as one application, with domain modules under `backend/apps/`. Each module owns its models, services, validation, API components, and tests as appropriate. Keep sensitive business operations in service functions/classes and preserve essential invariants through PostgreSQL constraints and transactions. API views should orchestrate rather than implement financial rules directly.

Use a versioned REST API under `/api/v1/`. Maintain PostgreSQL as the source of truth, Django REST Framework for API delivery, and drf-spectacular for OpenAPI documentation. A frontend can be added to the same repository later without requiring a backend architecture change.

## Consequences

**Benefits:** simpler local development and deployment, fewer distributed transactions, explicit shared database consistency, and easier cross-module test coverage.

**Trade-offs:** module boundaries require discipline; a single application is deployed together; extracting a service later may require refactoring shared data access.

## Guardrails

- No cross-fund data access without membership and object-level permission checks.
- Business rules involving payments, lotteries, and settlements belong in service code and must have tests.
- Database constraints, idempotency, audit history, and locking should be used when required by the business invariant.
- Modules must not bypass another module's documented interface merely for convenience.
- Record a new ADR before making a major architecture reversal.

## Alternatives considered

- **Microservices from day one:** rejected due to distributed consistency and operational overhead at the current stage.
- **Single undifferentiated Django application:** rejected because it obscures business boundaries and makes financial logic harder to review.

## Status of implementation

The Django project and `backend/apps/` package exist. Business domain modules and their contracts are planned, not yet implemented.
