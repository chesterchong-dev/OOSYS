# Identity & Access Integration Contract

**Status:** Phase 02 implementation contract; authentication, tenant isolation and permissions must be tested by every consumer.

## Principal contract
Protected API handlers depend on `app.identity.dependencies.get_principal` and receive an immutable `Principal` with `user_id`, `email`, `organization_id`, `membership_id` and a frozen permission set. It is resolved from a random opaque bearer token by digest lookup, checked for expiry/revocation, then validated against active user, active organization and active membership. Do not accept an organization ID header or request-body field as tenant authority.

## Authorization
Use `require_permission("module.resource.action")` for every protected route. Permission keys are code-owned and seeded by migration; tenant administrators cannot invent global permission keys. Role and membership-role relationships are organization-scoped. Role creation/update and role assignment reject permissions the acting principal does not hold. Never use frontend visibility as the authorization boundary.

Current keys: `organization.read`, `organization.update`, `organization.archive`, `organization.units.read`, `organization.units.create`, `organization.units.update`, `organization.units.archive`, `members.read`, `members.invite`, `members.update`, `roles.read`, `roles.create`, `roles.update`, `roles.archive`, `audit.read`. Future modules add permission keys through a reviewed code/migration change and update tests and this contract; tenant admins cannot register new keys at runtime.

## Tenant query and mutation contract
Every tenant-owned repository method must require a trusted principal or an explicit verified tenant context. Add `organization_id == principal.organization_id` to all reads, updates, deletes, exports, aggregates and relationship lookups. For create operations, assign tenant ID from the principal, never from a caller-provided field. Cross-tenant resource IDs should return a safe 404. Check tenant scope before writing audit events or triggering side effects. Use composite foreign keys for relationships between tenant-owned entities wherever possible.

This module applies those rules to organization, membership, role, audit, hierarchy, invitation, session, reset-token and user-record access. PostgreSQL RLS is enabled on identity-owned and tenant-owned tables, including shared user records scoped to self lookup or current-tenant memberships. `set_tenant_context` must be applied before queries against RLS-protected tables. Deploy using a non-superuser application role that does not own the tables; superusers bypass RLS. Future business-domain modules must add tenant policies and denial tests for every tenant-owned table.

## Session and credential contract
- Send opaque tokens in the Authorization: Bearer header. Tokens are generated with a cryptographically secure random source; only SHA-256 digests are stored.
- Validate expiry and revocation on every protected request. Logout, logout-all, password change, account deactivation, organization suspension/archive and membership suspension/revocation invalidate relevant sessions.
- Hash passwords with Argon2 through pwdlib. Never log raw passwords, hashes, bearer tokens, reset tokens or Authorization headers.
- Registration is disabled unless `OOSYS_ALLOW_SELF_REGISTRATION=true`. Password recovery requires SMTP plus `OOSYS_PASSWORD_RESET_URL`; invitations require SMTP plus `OOSYS_INVITATION_ACCEPT_URL`. Tokens are digest-only at rest, time-limited and single-use. Password-reset email requests are throttled per account; login throttle keys are HMAC-keyed with `OOSYS_LOGIN_RATE_LIMIT_SECRET` in production.
- This API does not use browser cookies, so CSRF tokens are not part of the current bearer transport. If cookie auth is added, require CSRF protection and Origin validation. Browser CORS must be an explicit allowlist.

## Transactions and audit
Application use cases own transactions. Coupled membership/role/session/audit mutations must commit together and roll back on failure. Audit events capture actor, tenant, action, target, outcome, timestamp and optional correlation ID; never store credentials or raw request bodies. Audit read APIs must be tenant-scoped and permission-gated.

## Future-module acceptance tests
Each module must prove:
1. No bearer token, invalid token, expired token and revoked token are rejected.
2. An active member with the required permission succeeds; a member without it is denied.
3. Tenant A cannot list, read, update, archive/delete, export, search or aggregate tenant B records.
4. Tenant A cannot create relationships to tenant B records or assign tenant B roles.
5. Revoked/suspended memberships immediately lose access.
6. Permission assignment cannot escalate beyond the acting principal's permission set.
7. Background jobs and integrations carry a verified tenant context and cannot bypass policies.
8. Migration upgrade/downgrade and database constraints are tested on supported engines.
