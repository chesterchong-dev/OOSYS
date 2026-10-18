# ADR-0004: Identity, Revocable Sessions and Tenant-Scoped RBAC

- Date: 2026-10-18
- Status: Accepted for the Phase 02 implementation baseline; production acceptance remains open.

## Context
Phase 01 established synchronous SQLAlchemy session factories, Alembic migration ownership, a versioned API router and a safe error envelope. Identity must integrate without adding a global engine or changing the Phase 01 transaction contract.

## Decision
- Store user passwords with Argon2 via pwdlib; store only SHA-256 digests of cryptographically random opaque bearer tokens.
- Authenticate each protected request against server-side session expiry/revocation and active user, organisation and membership state.
- Derive active tenant from the verified session and active membership. Tenant path identifiers are resource selectors and are compared to the principal tenant; mismatches return 404.
- Scope roles and membership-role assignments by organisation. Composite foreign keys prevent a membership in one tenant from receiving a role belonging to another tenant.
- Keep the permission vocabulary code-owned. Tenant administrators may only create roles containing permissions they themselves hold; no tenant API can invent global permissions.
- Audit sensitive events without credential material. Use soft archival for organisations and users rather than destructive deletion.
- Chain migration 20261018_0002 after 20261018_0001 and preserve platform_settings.
- Use Authorization: Bearer transport rather than cookies in this phase. Browser clients must protect tokens; if cookie auth is introduced, add CSRF protections and origin checks.

## Compatibility and consequences
- New API paths are mounted under the existing configurable /api/v1 prefix. Existing / and /health endpoints and API error contract remain unchanged.
- Authentication is server-side revocable, not stateless JWT. Database availability is required for protected requests.
- Existing users/memberships are not backfilled because Phase 01 had no identity data. The first registration provisions an owner and organisation in one transaction.
- Registration is a bootstrap route and must be restricted before public deployment. Invitation and password-reset delivery, PostgreSQL RLS, robust distributed throttling, retention jobs, and a security review remain open.
- Phase 02 must not be marked complete until CI and adversarial tenant/security tests pass.
