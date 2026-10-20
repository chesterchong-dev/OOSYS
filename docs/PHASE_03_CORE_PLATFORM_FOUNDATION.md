# Phase 03 — Core Platform Foundation

**Status:** IN PROGRESS — bounded foundation slice implemented; full phase acceptance not claimed.

## Scope resolution and evidence

The master product map's Architecture and Product Roadmap → Foundation branch names four workstreams: multi-tenant architecture, authentication and authorisation, shared design system and navigation, and API standards and database conventions. The first two were implemented and accepted in Phases 01–02. The repository is a Python/FastAPI backend with no frontend tree, so a UI shell cannot be delivered without inventing a frontend phase/stack. The Developer Implementation Blueprint's Shared Platform Services is a product capability catalogue, not a phase-by-phase allocation; its topics are candidates, not blanket permission to implement every service.

The requirements register and crosswalk contain 87 stable IDs and preserve their existing classifications. The register explicitly says CORE-005 shared master data belongs to a subsequent phase. The roadmap does not allocate every Shared Platform Services item to Phase 03. This phase implements the smallest safe remaining Foundation slice evidenced by the roadmap: operational readiness and API/operations conventions. It does not create speculative settings, notification, file, search, workflow, integration, subscription, or AI products.

## Phase 03 scope matrix

| Requirement ID | Source topic | Existing implementation | Phase 03 deliverable | Dependencies | Acceptance test / evidence | Deferred boundary |
|---|---|---|---|---|---|---|
| OOSYS-CORE-001 | Tenant and organisation management | Phase 02 identity/tenant slice; broader lifecycle partial | No change | Phase 02 contracts | Preserve identity regression suite | Provisioning/export/deletion lifecycle deferred |
| OOSYS-CORE-002 | Secure sign-in, sign-out, reset and session expiry | Phase 02 implementation slice | No change | Phase 02 auth | Existing identity CI regression suite | No auth rewrite |
| OOSYS-CORE-003 | Roles, permissions and module scopes | Phase 02 RBAC slice | No change | Phase 02 permission vocabulary | Existing permission-denial tests | Module-specific permissions await owning modules |
| OOSYS-CORE-004 | Organisation hierarchy | Phase 02 hierarchy CRUD | No change | Phase 02 identity | Existing hierarchy tests | Downstream integrations deferred |
| OOSYS-CORE-005 | Master Data Management | Missing; register explicitly says subsequent phase | Deferred | Canonical master-data domain and pagination contracts | No Phase 03 acceptance claim | Separate master-data phase |
| OOSYS-CORE-006 | Audit and compliance | Identity audit events exist | No shared audit contract change | Event ownership and retention policy | Existing identity audit tests | Cross-platform audit service deferred |
| OOSYS-CORE-007 | Notifications | SMTP delivery is an identity-flow adapter boundary | No new service | Provider policy, queue/retry/idempotency design | No Phase 03 acceptance claim | Shared notification service deferred |
| OOSYS-CORE-008 | File Management | Missing | Deferred | Storage adapter, malware/type/size policy, tenant ACLs | No Phase 03 acceptance claim | File/document service deferred |
| OOSYS-CORE-009 | Global search limited by tenant and permissions | Missing | Deferred | Search indexing and module authorization contracts | No Phase 03 acceptance claim | Global search deferred |
| OOSYS-CORE-010 | Settings and Configuration Management | Deployment-wide non-secret platform_settings table only | No CRUD API added | Settings schema ownership, tenant context, secret boundary, audit policy | Existing migration tests only | Tenant/user settings CRUD deferred |
| OOSYS-CORE-011 | API standards and database conventions | Versioned router, safe error envelope, explicit Alembic migrations | Preserve liveness; add generic readiness endpoint | Existing Settings/SQLAlchemy factory/error contract | Readiness tests plus full CI on resulting SHA | Pagination/filter conventions implemented with first owning collection, not as unused abstractions |
| OOSYS-CORE-012 | Monitoring, alerting and system health | /health is liveness only | Add /health/ready with configured DB SELECT 1 check | Injectable settings and existing DB factory | 200 only when query succeeds; 503 otherwise; generic failure response | Metrics, alerting, backup/restore drills and production probes deferred |
| OOSYS-CORE-013 | Subscription and entitlement management | Missing | Deferred | Commercial product model and tenant entitlement enforcement | No Phase 03 acceptance claim | SaaS commercial phase |
| OOSYS-CORE-014 | Database backups and tested restoration | Missing | Deferred | Deployment/storage topology and recovery objectives | No Phase 03 acceptance claim | Operations/release phase |
| OOSYS-CORE-015 | Security and privacy controls | Partial baseline | No shared-contract rewrite | Existing identity/security baseline | Generic readiness errors; no secrets returned | Comprehensive security baseline/review remains open |
| OOSYS-CORE-016 | Common data model and master records | Missing/partial by domain | Deferred | Domain ownership and migration policy | No Phase 03 acceptance claim | Implement with master-data/owning domains |
| OOSYS-CORE-017 | Multi-deployment configuration | Environment settings exist; deployment manifests absent | No change | Deployment topology decision | Existing configuration tests | Deployment profiles/manifests deferred |
| OOSYS-CORE-018 | Shared design system and navigation | No frontend tree | Deferred | Approved frontend stack and UI phase | No frontend build available | UI shell deferred; no stack invented |
| OOSYS-CORE-019 | Dashboards | Missing | Deferred | Persisted domain metrics and permissions | No Phase 03 acceptance claim | Analytics phase |
| OOSYS-CORE-020 | Operation command center | Missing | Deferred | Operational telemetry and role model | No Phase 03 acceptance claim | Operations UI phase |
| OOSYS-CORE-021 | Workflow engine | Missing | Deferred | Durable state, idempotency, retries, authorization and audit | No Phase 03 acceptance claim | Workflow phase |
| OOSYS-CORE-022 | Integration framework | Provider adapters limited to identity email flows | No external connector invented | Connector contracts and credentials | No external integration claim | Integration framework deferred |
| OOSYS-CORE-023 | Shared AI services | Missing | Deferred | Permission-aware retrieval, provider/usage policy | No Phase 03 acceptance claim | AI platform phase |
| OOSYS-CORE-024 | Offline capability | Missing | Deferred | Client architecture and conflict-resolution policy | No Phase 03 acceptance claim | Offline phase |
| OOSYS-CORE-025 | Status and activity tracking | Identity audit is not a general activity feed | Deferred | Canonical event and retention contracts | No Phase 03 acceptance claim | Shared activity service deferred |
| OOSYS-CORE-026 | Reporting foundation | Missing | Deferred | Domain data, metrics definitions and permission filtering | No Phase 03 acceptance claim | Reporting phase |

The remaining 61 non-CORE rows in the 87-row register map to business-domain and cross-cutting capabilities. They remain in their existing classifications and are not pulled into this phase merely because they appear in the product map. The source crosswalk remains the mapping authority.

## Operational API contract

- GET /health remains backwards-compatible liveness and does not connect to dependencies.
- GET /health/ready returns 200 with status ready and database check ok only after a configured database answers SELECT 1. Missing configuration or query/connection failure returns 503 with only status not_ready.
- Readiness does not run migrations and does not claim mail, object storage, search, AI, external integrations or application workflows are ready.
- The endpoint reuses an existing identity engine. If it creates a temporary engine, it disposes it after the probe.
- No credentials, connection strings, SQL errors or exception messages are returned.

## Assumptions and impact

1. The product-map roadmap has four high-level Foundation workstreams rather than an explicit 23-phase numbered breakdown. Phase 03 is interpreted as remaining backend API/operations foundation after accepted Phase 00–02 work.
2. The requirements register's generic “Core platform foundation” label does not mean every CORE requirement belongs to Phase 03. CORE-005 is explicitly subsequent; other Shared Platform Services are deferred unless a concrete dependency requires them.
3. Readiness reports database readiness only. Production telemetry, alerting, backup restoration, deployment topology and service dependency probes remain unverified.
4. CI is the execution environment because the workflow is GitHub-web-only; no claim is made that local commands were run.

## Verification gates

Phase 03 is not complete until the resulting exact commit's CI passes, readiness tests pass, operations-module coverage is reported and reviewed against the 90% target, and documentation/status reflects verified evidence. This bounded implementation does not satisfy acceptance for deferred shared platform services.
