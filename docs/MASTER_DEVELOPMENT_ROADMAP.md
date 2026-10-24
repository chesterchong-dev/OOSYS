# OOSYS — Master Development Roadmap (23 Phases)

**Roadmap XMind:** https://app.xmind.com/share/JGrSGk06  
**Product map:** https://app.xmind.com/share/QsPytPPH  
**Developer Implementation Blueprint:** https://app.xmind.com/share/EkL12TxG

This file is a compact repository index for the authoritative roadmap XMind. Read the XMind before planning any phase; then inspect the current repository and the linked phase record before changing code.

## Source-of-truth rules

1. Accepted repository phase records and verified implementation/CI evidence govern completed phases.
2. `docs/requirements/REQUIREMENTS_REGISTER.md`, `docs/requirements/requirements_register.csv` and `docs/requirements/REQUIREMENT_SOURCE_NODE_CROSSWALK.csv` define stable requirement IDs and source traceability.
3. The product map defines intended product capabilities; the Developer Implementation Blueprint governs engineering/security/testing standards.
4. Linear issues CHE-6 through CHE-28 provide the recorded phase sequence and detailed future-phase scope. Some tracker statuses are stale and must be reconciled against repository evidence.
5. The original roadmap was not found as a single document in the current branch. Phase 05–22 titles and scoped summaries below are recovered from Linear records; this companion is a traceable reconstruction, not a claim that the original roadmap file was recovered.

## Accepted baseline

- Phase 00 — Repository Audit & Development Baseline: accepted for audit and traceability only. See [Phase 00 record](PHASE_00_AUDIT.md).
- Phase 01 — Architecture & Delivery Governance: accepted for architecture/governance scope only. See [Phase 01 record](PHASE_01_ARCHITECTURE.md).
- Phase 02 — Identity, Authentication & Multi-Tenancy: accepted for scoped identity/authentication/tenant controls. See [Phase 02 record](PHASE_02_IDENTITY_MULTITENANCY.md).
- Phase 03 — Core Platform Foundation: accepted for bounded API/readiness scope only. See [Phase 03 record](PHASE_03_CORE_PLATFORM_FOUNDATION.md). The older Linear Phase 03 title “Shared Platform Services” does not override the accepted boundary.
- Phase 04 — Frontend Shell & Administration: accepted for the frontend shell and existing-API administration milestone. See [Phase 04 record](PHASE_04_FRONTEND_SHELL_ADMINISTRATION.md). The older Linear title “Navigation, Dashboard & Administration UI” does not override the accepted title.

Acceptance is scoped: it does not mean all requirements associated with a domain are complete. At Phase 05 PR head `57477a1052032a2884a769b1bf97e68a1a83020e`, the reconciled requirement view reports 87 unique IDs: 74 missing and 13 partial. No full product requirement is marked verified. See the Phase 05 record and PR #1 for current evidence.

## Phase index

| Phase | Title | Current recorded state |
|---|---|---|
| 00 | Repository Audit & Development Baseline | Accepted — audit/traceability only |
| 01 | Architecture & Delivery Governance | Accepted — architecture/governance only |
| 02 | Identity, Authentication & Multi-Tenancy | Accepted — scoped identity/auth/tenant controls |
| 03 | Core Platform Foundation | Accepted — bounded API/readiness only |
| 04 | Frontend Shell & Administration | Accepted — shell and existing-API administration |
| 05 | Security, Observability & Recovery | In progress — implementation and CI evidence recorded in [PR #1](https://github.com/chesterchong-dev/OOSYS/pull/1); production operational acceptance remains blocked — [CHE-11](https://linear.app/chester-chong/issue/CHE-11/oosys-phase-05-security-observability-and-recovery) |
| 06 | Inventory Master Data & Stock Ledger | Linear says In Progress; implementation evidence must be reconciled — [CHE-12](https://linear.app/chester-chong/issue/CHE-12/oosys-phase-06-inventory-master-data-and-stock-ledger) |
| 07 | Warehouse Operations (WMS) | Not started — [CHE-13](https://linear.app/chester-chong/issue/CHE-13/oosys-phase-07-warehouse-operations-wms) |
| 08 | Suppliers & Purchasing | Not started — [CHE-14](https://linear.app/chester-chong/issue/CHE-14/oosys-phase-08-suppliers-and-purchasing) |
| 09 | Customers, Quotations & Sales Fulfilment | Not started — [CHE-15](https://linear.app/chester-chong/issue/CHE-15/oosys-phase-09-customers-quotations-and-sales-fulfilment) |
| 10 | CRM & Sales Force Automation | Not started — [CHE-16](https://linear.app/chester-chong/issue/CHE-16/oosys-phase-10-crm-and-sales-force-automation) |
| 11 | Commercial Readiness & Pilot Release | Not started — [CHE-17](https://linear.app/chester-chong/issue/CHE-17/oosys-phase-11-commercial-readiness-and-pilot-release) |
| 12 | Finance & Accounting Integration | Not started — [CHE-18](https://linear.app/chester-chong/issue/CHE-18/oosys-phase-12-finance-and-accounting-integration) |
| 13 | Projects, Tasks & Resource Planning | Not started — [CHE-19](https://linear.app/chester-chong/issue/CHE-19/oosys-phase-13-projects-tasks-and-resource-planning) |
| 14 | HRMS, Attendance & Payroll | Not started — [CHE-20](https://linear.app/chester-chong/issue/CHE-20/oosys-phase-14-hrms-attendance-and-payroll) |
| 15 | Engineering & Product Lifecycle (PLM) | Not started — [CHE-21](https://linear.app/chester-chong/issue/CHE-21/oosys-phase-15-engineering-and-product-lifecycle-plm) |
| 16 | Manufacturing & Production | Not started — [CHE-22](https://linear.app/chester-chong/issue/CHE-22/oosys-phase-16-manufacturing-and-production) |
| 17 | Quality, Maintenance & Asset Management | Not started — [CHE-23](https://linear.app/chester-chong/issue/CHE-23-oosys-phase-17-quality-maintenance-and-asset-management) |
| 18 | Email, WhatsApp & Internal Communications | Not started — [CHE-24](https://linear.app/chester-chong/issue/CHE-24-oosys-phase-18-email-whatsapp-and-internal-communications) |
| 19 | Integration, API & Automation Platform | Not started — [CHE-25](https://linear.app/chester-chong/issue/CHE-25-oosys-phase-19-integration-api-and-automation-platform) |
| 20 | AI, Search, Reporting & Analytics | Not started — [CHE-26](https://linear.app/chester-chong/issue/CHE-26-oosys-phase-20-ai-search-reporting-and-analytics) |
| 21 | Offline Capability & Hybrid Deployment | Not started — [CHE-27](https://linear.app/chester-chong/issue/CHE-27-oosys-phase-21-offline-capability-and-hybrid-deployment) |
| 22 | Industry Packs & Ecosystem Expansion | Not started — [CHE-28](https://linear.app/chester-chong/issue/CHE-28-oosys-phase-22-industry-packs-and-ecosystem-expansion) |

## Phase 05 — recovered scope

Source: [Linear CHE-11](https://linear.app/chester-chong/issue/CHE-11/oosys-phase-05-security-observability-and-recovery).

Scope: structured logs and correlation IDs; readiness/liveness; metrics hooks; secret management; rate limiting; backup/restore procedures; dependency scanning; security headers; CSRF/CORS review; incident and operational runbooks.

Acceptance evidence required: an actually tested backup restore; security tests; operational runbooks; evidence that secrets are not exposed; relevant test/build/migration and integration results; commit SHA; remaining blockers. No Phase 05 implementation commit or acceptance evidence was verified during roadmap creation.

Dependencies: preserve Phases 00–04; build on existing configuration, authentication, health/readiness, CI and migration foundations. Choose metrics, secrets and backup mechanisms deliberately; no vendor is presumed.

## Global delivery gates

- Inspect current branch, commit, architecture, dependent modules and tests before every phase.
- Preserve accepted work and implement only approved phase scope plus necessary prerequisites.
- Keep API/router, application/service, domain/contracts, repository/persistence and infrastructure responsibilities separated.
- Use migrations for schema changes; document rollback or recovery. Do not silently change shared APIs, permissions, events or database contracts.
- Enforce server-side authorization and tenant isolation. Add tenant constraints/RLS and cross-tenant denial tests for every tenant-owned business module.
- Run relevant unit/integration tests, migration checks, frontend build/type-check/lint where configured; record actual results, not assumptions.
- Record changed files, commit SHA, CI run, test output, known gaps and acceptance decision before marking a phase accepted.

## Explicit deferrals and known limitations

- Online/public production hosting and production database deployment are not verified; do not infer readiness from a development frontend or passing CI.
- ChatGPT/OpenAI and Claude/Anthropic integration is not in scope before Phase 20 and requires provider, data-security and cost approval.
- Phase 11 deployment guides and pilot readiness do not equal public production hosting; Phase 21 covers hybrid/private deployment.
- Phase 03 did not implement all shared platform services. Shared master data, general notifications, file storage, global search, reusable workflow, subscription services and broad AI/integration capabilities remain future work unless separately verified.
- The user's GitHub-web-only workflow means no local checkout cleanliness or local command execution is claimed.
- A passing CI run verifies only the commit and checks actually run; documentation-only CI does not prove new application behaviour.

