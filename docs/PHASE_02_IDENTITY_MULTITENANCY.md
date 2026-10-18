# Phase 02 — Identity, Authentication & Multi-Tenancy

## Status
**Code implemented and CI-verified at commit 0a238a6926ab6b1296c42c2096dbcbb5922bc40e; Phase 02 remains open for documented scope gaps and production security hardening.**

## Scope delivered in this increment
- User and organisation bootstrap, account profile update, organisation update/archive.
- Organisation membership list, add existing user, status changes, and tenant-aware role assignment.
- Argon2 password hashing via pwdlib; opaque bearer sessions with only SHA-256 digests persisted; expiry, logout, logout-all, password change and organisation switching.
- RBAC permission catalogue and organisation-scoped roles/assignments; role creation cannot grant permissions the actor does not possess.
- Server-side principal resolution from a live session and active membership; cross-tenant organisation routes return 404.
- Database-backed failed-login attempt records keyed by hashed email and IP; limit of eight failures in a rolling 15-minute window.
- Audit events for registration, authentication outcomes, logout, password change, organisation changes, membership changes and role creation.
- Migration 20261018_0002 extends existing 20261018_0001; existing platform settings schema is preserved.

## API contract
All endpoints are mounted under configured API prefix (default /api/v1):
- POST /auth/register (disabled by default; enable OOSYS_ALLOW_SELF_REGISTRATION only for controlled onboarding)
- POST /auth/login, POST /auth/logout, POST /auth/logout-all
- GET /auth/me, PATCH /auth/me, POST /auth/me/password
- POST /auth/me/deactivate
- POST /auth/switch-organization/{organization_id}
- GET/PATCH /organizations/{organization_id}
- POST /organizations/{organization_id}/archive
- GET/POST /organizations/{organization_id}/members
- PATCH /organizations/{organization_id}/members/{user_id}
- GET/POST /organizations/{organization_id}/roles
- PATCH /organizations/{organization_id}/roles/{role_id}
- POST /organizations/{organization_id}/roles/{role_id}/archive
- GET /organizations/{organization_id}/permissions
- GET /organizations/{organization_id}/audit-events

Bearer token transport is intentional: clients must protect access tokens and send them in the Authorization header. Tokens are opaque, random, server-side revocable and not JWTs. Cookie/CSRF handling is therefore not used by this API. CORS remains deployment configuration and must use explicit allowed origins if browser clients are introduced.

## Security limitations requiring closure
- The identity module combines app-level tenant scoping, same-tenant composite foreign keys and PostgreSQL RLS policies. Deploy using a non-superuser application role; PostgreSQL superusers bypass RLS.
- Login limiting is database-backed but concurrency/cluster guarantees and cleanup/retention need a production review; enforce edge/IP throttling as defence in depth.
- Public self-service registration must be gated behind controlled onboarding before deployment.
- Email invitations are SMTP-backed for existing accounts; acceptance requires an authenticated session matching the invited email.
- Password reset is SMTP-backed with single-use hashed tokens, 30-minute expiry, generic account response, session revocation and replay prevention.
- No dedicated platform-global administrator is exposed. Global permission vocabulary is code-owned, not mutable by tenant administrators.
- Account self-service password change revokes all sessions. A user must authenticate again.
- No live external penetration test or dependency vulnerability scan is claimed.

## Acceptance checklist
- [x] Versioned identity migration chained after the existing platform settings migration.
- [x] Password hashing and opaque revocable session implementation.
- [x] Server-side permission dependency and trusted tenant context.
- [x] Tenant-scoped organisation/member/role/audit APIs with pagination on collection endpoints.
- [x] Composite constraints prevent cross-tenant membership-role and role-permission references.
- [x] Audit events exclude credential values.
- [x] CI run 39105886707 passed on implementation commit 0a238a6926ab6b1296c42c2096dbcbb5922bc40e: 37 tests, SQLite migration upgrade/downgrade, PostgreSQL migration/persistence/constraint check/downgrade, and compileall.
- [x] Cross-tenant read/update denial, expired/revoked sessions, login throttling, and role privilege-escalation tests pass on CI.
- [x] Coverage measured at 93% across app.identity in CI run 39105886707 (not a production-readiness certification).
- [x] Organisation hierarchy CRUD with tenant scoping, parent-type validation, archive rules and audit events.\n- [x] SMTP-backed password reset and invitation acceptance with expiry and replay prevention.\n- [x] PostgreSQL RLS policies and a CI cross-tenant row-visibility denial probe.\n- [x] PostgreSQL advisory-lock login throttling and bounded attempt retention.\n- [ ] External security review and broader module tenant coverage.

Phase 02 remains OPEN until final CI is green and the remaining external security review and broader module tenant-coverage requirements are addressed.