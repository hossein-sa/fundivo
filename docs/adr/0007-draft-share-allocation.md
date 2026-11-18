# ADR 0007 — Draft share allocation and retry safety

Status: Accepted for initial shares slice, subject to later financial-domain review

## Context

A member may own multiple participation units. Sharing a user ID alone is not
sufficient to represent each lottery-eligible participation unit. Two API
requests for the same assignment may be delivered because a client retries.

## Decision

- Model `Share` separately and connect it to `FundMembership`.
- Assign a per-fund sequential number and public UUID.
- Allocate only within a draft fund whose target share count is set.
- Lock the Fund row before capacity checks and creation.
- Require client-provided random `allocation_id`; identical retries return the
  original set without creating another set.
- Audit and insertion occur atomically.
- Managers see all shares; normal members see only their own.

## Consequences

The model has no monetary amount or transfer workflow yet. Read-only
administration avoids bypassing the service layer. We must revisit the
allocation data model before enabling transfers, guest ownership and rounds.

This ADR does not authorize guest membership or financial operations.
