# ADR-0009: Consent-based guest sponsorship (draft foundations)

Status: Accepted for draft-only API, no financial obligations yet.

## Problem

A guest may benefit from a share without an account, while an existing verified
member accepts responsibility for arranging contributions. These roles must
not be conflated. A manager must not silently make an unrelated member liable.

## Decision

Use a dedicated `GuestSponsorship` with a guest membership and a registered,
active sponsor membership in the same fund. Sponsor explicitly accepts using
their JWT. Manager reviews unless sponsor is the manager creating their own
proposal. Store status and consent/approval timestamps, actor-audited changes.
Do not transform an old guest into a sponsor-owned share and do not touch old
share allocations during migration.

An approved sponsorship allows a guest membership to be used as a draft
participant; the associated `ShareParticipation` still identifies the guest as
beneficiary, with the sponsor separately recorded. A 12-unit share stays one
lottery chance, including when the beneficiary is a guest.

## Trade-offs

This creates a placeholder before manager approval; it is inactive until
approved. Old guest placeholders may already be active and stay that way for
backward compatibility. Sponsorship here is consent metadata, *not* a legal
surety agreement, payment evidence or installment accounting. To change an
approved sponsor later requires an explicit future stateful transfer workflow
rather than overwriting historical rows.
