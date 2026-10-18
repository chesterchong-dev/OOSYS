# Phase 02 — Identity, Authentication & Multi-Tenancy

## Status

**Status: OPEN — implementation acceptance is evidenced, but final documentation-commit CI is not yet verified.** The user works through GitHub website on Android and does not maintain a local Git checkout, so local working-tree verification is **Not Applicable (N/A)** to this workflow. This is a workflow-scope decision, not evidence that local Git commands passed or that any local working tree is clean.

**Remote implementation/evidence checkpoint:** branch `phase-00-02-starter`, commit `9cba87d8940dc44b88c517b572632631abeb208a`, passed exact-HEAD CI run [39112902344](https://github.com/chesterchong-dev/OOSYS/actions/runs/39112902344). That run verifies the documentation/evidence checkpoint, not new application behavior.

**Implementation evidence (separate):** code-verification commit `4c84c3fcf4b1a18a5fa41f2734a2af2af5ab5615`, CI run [39110600679](https://github.com/chesterchong-dev/OOSYS/actions/runs/39110600679): 46 passed, 2 PostgreSQL-only tests skipped in the standard suite, 91% `app.identity` coverage, and 2 dedicated PostgreSQL concurrency tests passed.

**Remaining mandatory gate:** exact-HEAD CI for the final documentation commit must be independently verified, including its actual conclusion and checked-out SHA. The connected GitHub tools available in this session expose prior run/job details but do not provide a workflow-dispatch or repository-wide Actions-run listing, and the public Actions page could not be fetched here. Do not treat the prior checkpoint run as verification of later documentation commits. No local cleanliness, production certification, external security review, or production deployment is claimed.
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
- [x] Code-verification CI run 39110600679 passed on `4c84c3fcf4b1a18a5fa41f2734a2af2af5ab5615`: 46 passed, 2 PostgreSQL-only tests skipped in the standard suite; dedicated PostgreSQL concurrency tests passed 2 tests; 91% `app.identity` coverage, SQLite/PostgreSQL migration checks, restricted-role PostgreSQL RLS probes including user-record isolation, invitation acceptance and organisation switching, and compileall.
- [x] Documentation-only HEAD `54d85138551460a1226ad0a35f174b9ae7158886` verified by exact-HEAD CI run [39111339023](https://github.com/chesterchong-dev/OOSYS/actions/runs/39111339023).
- [x] Evidence-reconciliation commit `eb2433b70c303c5496c913b88f48fc38635a8ed8` verified by exact-HEAD CI run [39112486983](https://github.com/chesterchong-dev/OOSYS/actions/runs/39112486983); all substantive steps passed. This validates the evidence/documentation commit, not a new implementation change.
- [x] Requirements register and architecture/security limitations documented.
- [x] Local working-tree gate disposition recorded as **Not Applicable (N/A)** because the declared workflow uses GitHub website on Android and has no maintained local checkout; this is not a local Git pass or cleanliness claim.
- [x] Remote branch/commit/CI evidence recorded separately from implementation-test evidence.
- [ ] Exact-HEAD CI for the final documentation commit independently verified, including the checked-out SHA and conclusion.

**Closure decision: Phase 02 remains OPEN.** The local-checkout gate is N/A for the user's declared GitHub-web-only workflow; it is not marked as passed, and no local working-tree cleanliness is asserted. The prior remote checkpoint CI passed, but exact-HEAD CI for the final documentation commit is not independently verified in this session. This is the precise remaining acceptance blocker. No dedicated type-checker, linter, frontend build, dependency vulnerability scanner or external security assessment is configured or claimed. Production launch additionally requires environment-specific security review, correct SMTP/CORS configuration, non-superuser database credentials and tenant RLS coverage for every subsequently implemented business module.
