# Phase 02 — Identity, Authentication & Multi-Tenancy

## Status

**Core Phase 02 scope is implemented and verified.** Exact-SHA CI run [39109323597](https://github.com/chesterchong-dev/OOSYS/actions/runs/39109323597) passed on commit `e7aec0d877c2ff835ed19dd5a793f174d805734f`: 46 tests, 91% coverage for `app.identity`, SQLite migration upgrade/downgrade, PostgreSQL migration/persistence/constraint checks, restricted-role PostgreSQL RLS checks for tenant data and user records, API invitation acceptance and organisation switching under RLS, and compileall. This is not a claim of production certification or external security review.

## Delivered scope

- Registration (disabled by default), login, logout, logout-all, profile updates, password changes, account deactivation and organisation switching.
- Argon2 password hashing; opaque random bearer tokens; only token digests are stored; expiry and server-side revocation.
- Login failure throttling with HMAC-keyed email/IP identifiers, a production secret, PostgreSQL advisory locks and bounded retention cleanup; password-reset requests are throttled per account.
- Tenant-scoped organisation lifecycle, memberships, roles, permission assignments and audit-event queries.
- Least-privilege role management: actors cannot grant permissions they do not possess.
- Business unit, location, department and team hierarchy with tenant scope, valid parent-type checks, bounded listing, audit events and soft archival.
- SMTP-backed password reset and invitations for existing OOSYS accounts, including invitation revocation. Reset/invitation tokens are one-time, hashed at rest, time-limited and replay-protected. Reset revokes all sessions; invitation acceptance requires an authenticated account whose email matches the invite.
- Composite tenant foreign keys and PostgreSQL RLS for user records, sessions, organisations, memberships, roles, role-permission assignments, membership-role assignments, audit events, password-reset tokens, hierarchy units and invitations.
- Versioned migrations `20261018_0002` through `20261018_0006`; requirements, architecture contracts and phase records updated.

## API contract

All endpoints use the configured API prefix (default `/api/v1`).

- Authentication: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `POST /auth/logout-all`, `GET /auth/me`, `PATCH /auth/me`, `POST /auth/me/password`, `POST /auth/me/deactivate`, `POST /auth/switch-organization/{organization_id}`.
- Recovery: `POST /auth/password-reset/request`, `POST /auth/password-reset/confirm`.
- Invitations: `POST /organizations/{organization_id}/invitations`, `POST /organizations/{organization_id}/invitations/{invitation_id}/revoke`, `POST /auth/invitations/accept`.
- Organisation/membership/roles/audit: `GET/PATCH /organizations/{organization_id}`, archive, member, role, permission and audit-event routes described in `docs/architecture/IDENTITY_ACCESS_CONTRACT.md`.
- Hierarchy: `GET/POST /organizations/{organization_id}/units`, `PATCH /organizations/{organization_id}/units/{unit_id}`, and `POST /organizations/{organization_id}/units/{unit_id}/archive`.

## Required deployment configuration and security notes

- Registration stays disabled unless `OOSYS_ALLOW_SELF_REGISTRATION=true`; public onboarding must be deliberately controlled.
- Password recovery requires `OOSYS_SMTP_HOST`, `OOSYS_EMAIL_FROM` and `OOSYS_PASSWORD_RESET_URL`. Invitations require SMTP plus `OOSYS_INVITATION_ACCEPT_URL`. SMTP uses STARTTLS; configure a trusted relay and valid sender.
- Set `OOSYS_LOGIN_RATE_LIMIT_SECRET` in production. Use a non-superuser PostgreSQL application role that does not own the tables; superusers bypass RLS. CI exercises actual API requests using a restricted role.
- Bearer tokens must be protected by clients. Cookie/CSRF handling is not part of this API; configure explicit CORS origins if browser clients are added.
- Identity user rows are protected by RLS for the authenticated user, explicit target-user lookup and current-tenant memberships. The global permission catalogue and HMAC-keyed login-attempt telemetry remain platform-wide; do not expose them through tenant APIs.
- No external penetration test, independent security certification or production deployment is claimed. RLS policies must be added and denial-tested for every future tenant-owned module/table. Distributed edge/IP throttling and operational retention monitoring remain deployment hardening.

## Acceptance checklist

- [x] Identity, authentication, sessions, reset, invitations, RBAC and tenant-scoped organisation lifecycle.
- [x] Business-unit/location/department/team hierarchy and audit trail.
- [x] Application tenant checks, composite same-tenant constraints and PostgreSQL RLS.
- [x] Negative tests for cross-tenant access, privilege escalation, invalid hierarchy parentage, reset/invitation replay and session revocation.
- [x] CI run 39109323597 passed on `e7aec0d877c2ff835ed19dd5a793f174d805734f`: 46 tests, 91% `app.identity` coverage, SQLite/PostgreSQL migration checks, restricted-role PostgreSQL RLS probes including user-record isolation, invitation acceptance and organisation switching, and compileall.
- [x] Requirements register and architecture/security limitations documented.

**Phase 02 core scope is complete.** Production launch still requires environment-specific security review, correct SMTP/CORS configuration, non-superuser database credentials and tenant RLS coverage for every subsequently implemented business module.
