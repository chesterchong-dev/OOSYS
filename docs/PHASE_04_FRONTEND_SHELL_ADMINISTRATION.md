# Phase 04 — Frontend Shell & Administration

**Status:** Implementation committed; acceptance requires exact-HEAD GitHub Actions and live integration verification.
**Baseline:** Phase 03 accepted at 07a1e444754c8ef0e743c117a13c22d2c8025856.
**Stack:** React 18, TypeScript, Vite, Tailwind CSS 3; existing FastAPI/Pydantic API. No backend schema or shared API contract changes.

## Scope recovered from the project conversation
Phase 04 is the first visual milestone. It delivers a real sign-in screen, permission-aware sidebar navigation, dashboard shell and working administration screens. The approved frontend stack is React, TypeScript, Vite and Tailwind CSS. This phase consumes existing API contracts; it does not implement master data, tenant/user settings CRUD, global search, subscriptions, workflow, shared notifications, file storage or later business modules.

## Requirement crosswalk
| Requirement | Phase 04 work | Acceptance evidence |
|---|---|---|
| OOSYS-CORE-018 Shared UI shell | Responsive shell, navigation, active workspace, semantic landmarks and visible keyboard focus | Frontend build and component tests; exact-HEAD CI |
| OOSYS-CORE-019 Dashboards | Initial dashboard derives counts from permitted member, role, hierarchy and audit endpoints | Counts originate in authorized API responses; no fabricated data |
| OOSYS-CORE-001 Tenant and organisation management | Existing organization read/update/archive endpoints surfaced in administration UI | Uses authenticated principal organization; server permission and tenant checks remain authoritative |
| OOSYS-CORE-002 Authentication and sessions | Login, organization selection, bearer session, logout and password change | Existing /api/v1/auth contracts; tab-scoped sessionStorage, never localStorage |
| OOSYS-CORE-003 Roles and permissions | Role list/create/edit metadata/archive; creation grants only permissions held by current principal | Existing roles API validates mutations; role assignments preserved when editing metadata |
| OOSYS-CORE-004 Organisation hierarchy | List/create/update/archive business units, locations, departments and teams | Existing hierarchy endpoints validate tenant scope and parent constraints |
| OOSYS-CORE-006 Audit and compliance | Read-only paginated audit trail | Existing audit.read permission and tenant-scoped endpoint |
| OOSYS-CORE-011 API conventions | Typed client, bearer headers, status-aware errors, bounded pagination | Unit tests cover auth headers, errors and 204 handling |
| OOSYS-CORE-012 Monitoring and health | No changes to accepted Phase 03 health/readiness behavior | Existing backend regression workflow retained |

## Implementation and security notes
- All displayed records and mutation results come from the existing API; no demo records or fake successful actions are used.
- Navigation visibility is a usability measure, not an authorization boundary.
- Multi-organization login selection repeats login with the selected organization ID.
- Invitations require an existing active OOSYS account and configured SMTP plus invitation URL; the API error is shown if these prerequisites are absent.
- The current API does not expose role permission assignments for readback. Role metadata edits therefore omit the permission field, preserving existing assignments.
- Password changes revoke backend sessions; the frontend clears the now-invalid session.
- Vite proxies /api to the backend in development. Production must configure same-origin reverse proxy routing or VITE_API_BASE_URL and a strict CORS allowlist.

## Known limitations
No invitation list/revocation UI, role-assignment readback, profile-name readback, tenant/user settings CRUD or analytics-grade dashboard is implemented because the required read contracts/services are absent. The dashboard is an initial administrative overview, not a reporting product. No production deployment is claimed. CI must pass on the exact final commit before Phase 04 can be accepted.
