# OOSYS Requirements Sources

## Canonical sources inspected on 2026-10-18
1. **Master product map — OOSYS — Only One System:** https://app.xmind.com/share/QsPytPPH (`QsPytPPH`), sheet `2a4bcc0a-f5ad-4383-a3a3-7746be58145a`, 183 topic anchors including root.
2. **Developer Implementation Blueprint:** https://app.xmind.com/share/EkL12TxG (`EkL12TxG`), four sheets: Development Contract & Architecture (`cdb78a4a-2506-4a9c-ba92-699d5bfda822`, 132); Business Systems (`d0ed8f5e-7e0a-4e78-b8ee-463a46c81455`, 157); Manufacturing, Engineering and Logistics (`2b7c676e-9abc-4de0-b4b2-1c8ed34227db`, 132); Integrations, AI and Enterprise Experience (`cce01cb1-422f-4a65-8aeb-9bcb1694e937`, 181). Blueprint total 602; combined map anchors 785.
3. **CRM master prompt:** `OOSYS_CRM_Master_Prompt.md`, found in Library (30,174 bytes); CRM workflows, tenant isolation, admin/customization, AI safeguards, integration contracts, tests and definition of done reviewed.
4. **GitHub source:** https://github.com/chesterchong-dev/OOSYS, branch `phase-00-02-starter`. Live branch ref, recursive tree, README, Phase 00 target file and baseline commit were inspected.

## Traceability rules
`REQUIREMENT_SOURCE_NODE_CROSSWALK.csv` maps all 87 stable IDs to actual topic UUIDs from live Xmind anchors. Match classes distinguish exact title, semantic feature, semantic parent, duplicate-title disambiguation, partial coverage and proxy gap. UUIDs are source locators, not evidence of implementation.

## Source gaps and overlaps
- **Settings/configuration (CORE-010):** three verified nodes partially cover environment configuration, user notification preferences and per-tenant connector configuration. They do not specify generic tenant/user settings CRUD and lifecycle; no dedicated general settings topic was found.
- **Subscriptions/entitlements (CORE-013, OPS-086):** no dedicated SaaS subscription, billing-plan, feature-entitlement or commercial-readiness topic was found; `Commercial Enablement` is a parent-level proxy. Service-contract entitlements describe customer service coverage/SLA and are not a substitute for SaaS feature entitlements.
- **Customer service cases:** a detailed `Service desk and ticketing` branch exists in the blueprint, covering incidents, service requests, assignment, SLA, customer, lifecycle states, comments, attachments and escalation. The crosswalk uses this semantic match rather than a proxy.
- CRM, sales/order and marketing overlap across map sections; QMS and MRP recur in more than one product context; workflow/approvals recur across domains. Canonical ownership and shared contracts need architecture decisions.

## Repository boundary
The branch is a minimal FastAPI scaffold, not the full product implementation. Source maps describe intended scope and must not be mistaken for implemented code.
