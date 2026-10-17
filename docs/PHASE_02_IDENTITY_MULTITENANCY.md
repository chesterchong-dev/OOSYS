# Phase 02 — Identity, Authentication & Multi-Tenancy

## Status
**Not implemented in this starter bundle. Do not treat as production-ready.**

## Acceptance checklist
- [ ] Organisation create/read/update/archive lifecycle with permissions.
- [ ] User lifecycle and organisation membership lifecycle.
- [ ] Password hashing using a maintained password-hashing library.
- [ ] Login/logout, session expiry, refresh/revocation strategy.
- [ ] Authentication middleware and server-side authorization policies.
- [ ] Role/permission management with least privilege.
- [ ] Tenant context derived from authenticated membership, never trusted from a client-supplied tenant ID alone.
- [ ] Tenant-scoped repository queries and mutations.
- [ ] Database constraints and migrations for membership and identity invariants.
- [ ] Rate limiting and audit events for security-sensitive actions.
- [ ] Tests for unauthenticated access, cross-tenant access, privilege escalation, expired/revoked sessions, invalid input, and concurrent constraints.
- [ ] Meaningful business-logic coverage measured by an actual test run.

## Security notes
Do not store plaintext passwords. Do not log credentials, session tokens, or password reset secrets. Avoid hard deletion where audit history or ownership records must be retained.
