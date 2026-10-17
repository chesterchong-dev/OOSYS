# OOSYS Requirements Sources

## Canonical sources inspected and reconciled on 2026-10-18
1. **Master product map — OOSYS — Only One System:** https://app.xmind.com/share/QsPytPPH (`QsPytPPH`), sheet `2a4bcc0a-f5ad-4383-a3a3-7746be58145a`, 198 topics including root.
2. **Developer Implementation Blueprint:** https://app.xmind.com/share/EkL12TxG (`EkL12TxG`), four sheets: Development Contract & Architecture (`cdb78a4a-2506-4a9c-ba92-699d5bfda822`, 143); Business Systems (`d0ed8f5e-7e0a-4e78-b8ee-463a46c81455`, 173); Manufacturing and Operations (`2b7c676e-9abc-4de0-b4b2-1c8ed34227db`, 132); Integrations and Intelligence (`cce01cb1-422f-4a65-8aeb-9bcb1694e937`, 181). Blueprint total 629; combined map topics 827.
3. **CRM master prompt:** `OOSYS_CRM_Master_Prompt.md`, found in Library and reviewed for workflows, tenant isolation, integrations, AI safeguards, tests and definition of done.
4. **GitHub source:** https://github.com/chesterchong-dev/OOSYS, branch `phase-00-02-starter`. Branch metadata, repository tree, source files and workflow evidence were inspected.

## Traceability rules
`REQUIREMENT_SOURCE_NODE_CROSSWALK.csv` maps all 87 stable requirement IDs to source topic UUIDs. Classifications distinguish exact-title, semantic-feature, semantic-parent and duplicate-title-disambiguation. UUIDs are source locators, not evidence of implementation.

## Source-map additions made to resolve audit gaps
- **Settings/configuration (CORE-010):** Master-map topic `Settings and Configuration Management` UUID `730a172f-3553-4486-a597-bce093e752c7`; blueprint details include tenant-scoped settings CRUD, validation, permission checks, versioning/audit, user preferences, environment separation and secret-management boundaries.
- **Subscriptions/entitlements (CORE-013):** Master-map topic `Subscription and Entitlement Management` UUID `f9d48fe5-917b-4190-a581-281063e9f36b`; blueprint details cover plans, lifecycle, usage limits, server-side entitlement enforcement, billing adapters, suspension/cancellation and audit.
- **SaaS commercial readiness (OPS-086):** Master-map topic `SaaS Commercial Readiness` UUID `9a1f2a89-3a9b-4426-8764-840684b59b14`; blueprint details cover tenant onboarding, plan operations, billing/payment adapters, launch readiness and support procedures.
- **Customer service cases:** the crosswalk maps semantically to the verified `Service desk and ticketing` topic rather than an unrelated proxy.

## Repository boundary
The development branch is a minimal FastAPI scaffold, not the full product implementation. Source maps define intended scope and must not be mistaken for implemented code. Phase 01 must clarify overlapping module ownership and shared contracts.
