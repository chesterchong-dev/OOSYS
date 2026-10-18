# Phase 02 — Identity, Authentication & Multi-Tenancy

## Status
**Implemented in the development branch; acceptance remains open pending CI and security verification.**

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
- The identity module uses app-level tenant scoping and same-tenant composite foreign keys; PostgreSQL RLS is not enabled yet.
- Login limiting is database-backed but concurrency/cluster guarantees and cleanup/retention need a production review; enforce edge/IP throttling as defence in depth.
- Public self-service registration must be gated behind controlled onboarding before deployment.
- Membership add currently links an existing user; email invitations and delivery are not integrated.
- Password reset token persistence is modelled but a secure reset workflow requires a configured delivery adapter and must be implemented/tested before the requirement can be marked complete.
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
- [ ] Exact-HEAD CI suite and PostgreSQL migration/security integration pass.
- [ ] Cross-tenant and privilege escalation API tests pass on CI.
- [ ] Meaningful business-logic coverage measured at 90% or a documented evidence-based exception.
- [ ] PostgreSQL RLS, password reset/invitation delivery, and production rate-limit hardening completed or accepted as explicit blockers.

Phase 02 remains OPEN until all mandatory acceptance criteria are verified.