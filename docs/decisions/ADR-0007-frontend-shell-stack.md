# ADR-0007 — Frontend shell stack and API integration

- Date: 2026-10-22
- Status: Accepted for Phase 04 implementation

## Context
The accepted backend foundation has no frontend tree. The project conversation establishes Phase 04 as the first visual milestone and records the approved stack. The frontend must consume existing FastAPI contracts without weakening bearer authentication or tenant isolation.

## Decision
Use React 18, TypeScript, Vite and Tailwind CSS 3. Use the existing FastAPI /api/v1 endpoints and a typed frontend API client. Store opaque bearer tokens in tab-scoped sessionStorage, never localStorage. In development, Vite proxies /api to the backend. Production should route frontend and API through a same-origin reverse proxy where possible.

## Security and compatibility
- No backend route, permission vocabulary, database schema or migration changes are required.
- UI visibility does not authorize operations; existing principal and require_permission checks remain authoritative.
- Organization requests use the organization ID from the authenticated principal.
- Role metadata editing omits permissions because the current API does not expose assigned role permissions on read.
- Password changes revoke sessions and the frontend clears its session.
- Production CORS and reverse-proxy settings remain deployment responsibilities.

## Consequences
The first visual milestone works against existing APIs. Invitation listing, role-permission readback, richer dashboards and production deployment require separately scoped backend/deployment work.
