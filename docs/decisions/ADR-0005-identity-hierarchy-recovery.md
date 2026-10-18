# ADR-0005: Organisation Hierarchy, Recovery, Invitations and PostgreSQL RLS

- Date: 2026-10-18
- Status: Accepted for the Phase 02 implementation baseline.

## Context
The initial identity implementation covered authentication, sessions, organisation membership and tenant-scoped RBAC. Acceptance also requires a usable organisation hierarchy, secure credential recovery, invitations, and database-enforced defence in depth.

## Decisions
- Represent business units, locations, departments and teams in a tenant-scoped hierarchy with same-tenant parent constraints, validated parent types, audited changes and soft archival.
- Password-reset tokens and invitation tokens are cryptographically random; persist only token digests, enforce expiry and one-time consumption, and revoke sessions after a successful password reset.
- Send reset and invitation links through an explicit SMTP adapter. Delivery is opt-in through environment configuration; reset requests return a generic response and are throttled per account.
- Require an authenticated account whose email matches the invitation before accepting it. Invitees must already have a controlled OOSYS account; account provisioning remains a separate controlled process.
- Apply PostgreSQL RLS to identity user records, sessions, organisations, memberships, roles, role assignments, audit events, reset tokens, hierarchy units and invitations. Requests set transaction-local context through `set_tenant_context`.
- Require a non-superuser application database role that does not own the protected tables. RLS is defence in depth, not a replacement for application permission checks.

## Verification
Exact-HEAD CI run [39110600679](https://github.com/chesterchong-dev/OOSYS/actions/runs/39110600679) passed at commit `4c84c3fcf4b1a18a5fa41f2734a2af2af5ab5615`: 46 passed, 2 PostgreSQL-only tests skipped in the standard suite; dedicated PostgreSQL concurrency regression passed 2 tests; 91% `app.identity` coverage; SQLite migration upgrade/downgrade; PostgreSQL migration/persistence/constraint checks; restricted-role RLS denial tests including user-record isolation, invitation acceptance and organisation switching; and compileall.

## Consequences and known limits
- Future tenant-owned modules must define RLS policies, set trusted tenant context, use tenant-scoped foreign keys where practical, and test cross-tenant denial.
- SMTP, reset URLs, CORS, secret management, backup/recovery and least-privilege database credentials require environment-specific deployment configuration.
- No independent penetration test, security certification or production deployment is claimed.
