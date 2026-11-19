# Fundivo — Business Rules

## 1. Overview

Fundivo manages rotating community savings and
interest-free lending groups.

The platform records financial activities but does
not directly hold, receive, or transfer money.

Status: Initial Draft
Implementation: Not Started

## 2. Users and Roles

### BR-001: Fund Creation

Every registered and verified user may create a fund.

Creating a fund does not require approval from
the platform administrator.

### BR-002: Fund Manager

The creator automatically becomes the manager
of the newly created fund.

Fund management permissions are scoped to
the corresponding fund.

### BR-003: Multiple Memberships

A user may participate in multiple funds and
have different roles in each fund.

### BR-004: Manager Participation

A fund manager may participate financially or
act only as a manager.

To participate in a lottery, the manager must
own at least one eligible share.

### BR-005: Management Transfer

Management transfer requires acceptance by the
receiving member and an auditable history.

An active fund must not remain without a manager.

## 3. Memberships and Shares

### BR-006: Fund Membership

Membership is represented independently from
the global user account.

A fund membership may initially exist without
an associated registered user.

### BR-007: Guest Members

A manager may record a guest member.

A guest member must not automatically receive
a verified user account.

Linking a guest membership to a verified user
requires secure identity verification and acceptance.

### BR-008: Multiple Shares

One membership may own multiple shares.

Shares are independent business entities.

### BR-009: Share Participation

Every active share normally generates one
installment for each round.

### BR-010: Membership and Share Changes

Share transfers and membership exits must preserve
existing financial obligations and historical records.

Detailed transfer and exit policies remain OPEN.

## 4. Fund Lifecycle

### BR-011: Fund Status

Supported fund lifecycle states:

- Draft
- Active
- Paused
- Completed
- Cancelled

### BR-012: Activation

Before activation, share allocation and the round
schedule must be validated.

### BR-013: Financial Configuration

Financial settings must not be freely changed
after fund activation.

Exceptional changes require a documented and
auditable correction process.

### BR-014: Fund Completion

A fund may be completed only after validating
all required rounds, financial obligations,
and winner settlements.

## 5. Rounds and Installments

### BR-015: Round Structure

By default, each round has one winning share.

Each participating share has one installment
per round.

### BR-016: Expected Round Amount

Expected round amount equals:

Share amount multiplied by the number of
participating shares.

All calculations use integer Iranian rials (IRR).

### BR-017: Installment Uniqueness

A share must not have duplicate installments
for the same round.

### BR-018: Financial Obligations

Each installment records its amount, due date,
payment balance, settlement status and overdue state.

Detailed overdue handling remains OPEN.

## 6. Payments

### BR-019: Payment Recording

Members may submit payment records and receipts.

Authorized fund managers may also record payments.

### BR-020: Payment Verification

Payments must be reviewed by authorized managers.

A rejected payment requires a recorded reason.

### BR-021: Approved Payments

Only approved payments affect installment balances.

Pending or rejected payments must not reduce
outstanding financial obligations.

### BR-022: Partial Payments

The data model must support partial payments
and allocation of one payment to multiple
installments.

Detailed partial-payment policies remain OPEN.

### BR-023: Payment Corrections

Approved financial history must not be silently
overwritten or deleted.

Corrections require traceable compensating records.

### BR-024: Idempotency

Repeated or concurrent financial requests must
not create duplicate effective financial operations.

### BR-025: Receipts

Payment receipts are private.

Access must be restricted by fund membership,
role and the relevant resource permissions.

## 7. Lotteries

### BR-026: Lottery Methods

Supported winner-selection methods:

- Secure server-side random selection
- Predefined winner order

### BR-027: Share-Based Selection

Lottery participation is based on shares,
not individual users.

A member owning multiple shares may win
separately through different shares.

### BR-028: Winning Restrictions

A share may win at most once within
the same fund cycle.

### BR-029: Lottery Eligibility

Eligibility criteria must follow the
configured fund rules.

Eligibility conditions must be recorded before
the lottery execution.

Detailed eligibility policies remain OPEN.

### BR-030: Lottery Integrity

Lottery execution requires:

- Atomic transactions
- Appropriate database locking
- Duplicate-execution protection
- A secure random generator when applicable
- An auditable record of eligible shares,
  execution time, actor, method, and result

### BR-031: Lottery History

Valid lottery results must not be silently
deleted or replaced.

Exceptional corrections require a controlled,
auditable process.

The correction workflow remains OPEN.

## 8. Payouts

### BR-032: Independent Settlement

Winning a lottery and receiving a payout
are separate business processes.

### BR-033: Payout Records

The platform records expected payout amounts,
actual payout amounts, dates, statuses,
and relevant evidence.

### BR-034: Continuing Obligations

Winning a round does not eliminate a member's
future installment obligations.

## 9. Security and Audit

### BR-035: Fund Data Isolation

Users may access only funds and resources
for which they have appropriate permissions.

Object-level permissions are mandatory.

### BR-036: Audit Logging

Sensitive operations must be auditable,
including:

- Membership and role changes
- Share transfers
- Financial setting changes
- Payment approval and rejection
- Lottery execution and corrections
- Payout settlement
- Sensitive administrator actions

### BR-037: Financial Data Integrity

Financial operations must use appropriate
database constraints, transactions,
and concurrency controls.

### BR-038: Data Representation

- Public identifiers use UUIDs.
- Monetary values use integer IRR.
- Floating-point monetary values are prohibited.
- Timestamps must be timezone-aware.
- Stored timestamps use UTC.

## 10. Open Decisions

The following policies require explicit approval
before their corresponding implementation:

- Guest membership identity and linking details
- Share transfer and active-fund exit rules
- Partial-payment and prepayment policies
- Overdue-payment handling
- Lottery eligibility and exceptional corrections
- Secure receipt storage provider
- Payout confirmation procedures
- Fund cycle boundaries and repeated participation

These decisions must not be silently inferred
during implementation.

## 11. Implementation Status

This document defines planned business behavior.

Actual enforcement will be implemented through
Django models, database constraints, services,
permissions, and automated tests.

No business-domain functionality is considered
implemented merely because it is documented.

## Fund creation and access — first implemented slice

A verified active user may create a draft fund. Creation atomically assigns
that user an active manager membership and writes an audit event.
Draft `name` and `description` are manager-editable. A user can have roles in
multiple funds. Invitation acceptance, manager transfer, activation and
financial configuration remain pending; do not infer these are implemented.

## Invitations — implemented limited policy

Managers may issue up to 20 invitations per fund per 24 hours for draft funds.
Codes expire after 48 hours and target one verified Iranian mobile; issuance
never creates an account or membership. Only the intended verified user may
accept/reject, and acceptance creates a regular `member` membership with an audit
record. Manager revocation is supported. Guest membership, shares and manager
transfer remain OPEN and are not implicitly authorized by this workflow.

## Shares — first implemented slice

An active fund manager may allocate 1–20 participation units per request to an
active registered membership while the fund is in draft. A draft fund must
first define a positive `target_share_count`, which caps total allocations.
Each share has its own UUID and per-fund sequence number. A member may own
multiple shares and the manager need not hold any. Retried requests with a
matching allocation UUID do not create new shares. Transfer, guest ownership,
exit, rounding, obligations and activation remain OPEN.

## Guest members (implemented draft-only slice)

An active manager may create a named guest member of a draft fund. This is an
administrative placeholder and grants no access to Fundivo. Draft shares can
be allocated to that membership. Guest identity linking, cancellation, edits,
transfer, payouts and obligations are not implemented or authorized.
