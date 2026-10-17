# OOSYS Requirements Sources

## Canonical sources inspected on 2026-10-18
1. **Master product map — OOSYS — Only One System:** https://app.xmind.com/share/QsPytPPH (`QsPytPPH`), sheet `2a4bcc0a-f5ad-4383-a3a3-7746be58145a`, 183 topic anchors including root.
2. **Developer Implementation Blueprint:** https://app.xmind.com/share/EkL12TxG (`EkL12TxG`), four sheets: Development Contract & Architecture (`cdb78a4a-2506-4a9c-ba92-699d5bfda822`, 132); Business Systems (`d0ed8f5e-7e0a-4e78-b8ee-463a46c81455`, 157); Manufacturing, Engineering and Logistics (`2b7c676e-9abc-4de0-b4b2-1c8ed34227db`, 132); Integrations, AI and Enterprise Experience (`cce01cb1-422f-4a65-8aeb-9bcb1694e937`, 181). Blueprint total 602; combined map anchors 785.
3. **CRM master prompt:** `OOSYS_CRM_Master_Prompt.md`, found in Library (30,174 bytes); CRM workflows, tenant isolation, admin/customization, AI safeguards, integration contracts, tests and definition of done reviewed.
4. **GitHub source:** https://github.com/chesterchong-dev/OOSYS, branch `phase-00-02-starter`. Live branch ref, recursive tree, README, Phase 00 target file and baseline commit were inspected.

## Traceability rules
`REQUIREMENT_SOURCE_NODE_CROSSWALK.csv` maps all 87 stable IDs to actual topic UUIDs from live Xmind anchors. Match classes distinguish exact title, semantic feature, semantic parent, duplicate-title disambiguation, partial coverage and proxy gap. UUIDs are source locators, not evidence of implementation.

## Source gaps and overlaps
- **Settings/configuration (CORE-010):** verified nodes partially cover environment configuration (`4cad7a6a-8e2b-4352-9232-5f84be03b74e`), user notification preferences (`d8d6ddaf-52d0-486c-b543-ac91c93edac3`) and per-tenant connector configuration (`55839809-6854-4d8f-8c52-374a5fac46f2`). The saved-view preferences node (`ad9b63ba-2177-43af-af31-99246ce24d36`) is only UI state, not general tenant/user settings CRUD and lifecycle. No dedicated general settings topic or approved scope reduction exists.
- **Subscriptions/entitlements (CORE-013, OPS-086):** no dedicated SaaS subscription, billing-plan, feature-entitlement or commercial-readiness topic was found. `Commercial Enablement` (`560e332e-cbfe-4657-9107-0da7bda708f2`) is a parent whose children are CRM, Sales and Marketing. `Pricing and sales controls` (`0ca9cf8d-8dfa-4c43-a019-377a26569209`) covers transaction/customer pricing; `Define contract coverage, entitlements, response and resolution targets` (`cb386407-51e4-4bfb-a424-8daf4e011c71`) covers service-contract/SLA scope. Neither is a valid SaaS subscription/feature-entitlement/commercial-readiness mapping. No owner-approved scope decision exists; retain both gaps.
- **Customer service cases:** a detailed `Service desk and ticketing` branch exists in the blueprint, covering incidents, service requests, assignment, SLA, customer, lifecycle states, comments, attachments and escalation. The crosswalk uses this semantic match rather than a proxy.
- CRM, sales/order and marketing overlap across map sections; QMS and MRP recur in more than one product context; workflow/approvals recur across domains. Canonical ownership and shared contracts need architecture decisions.

## Repository boundary
The branch is a minimal FastAPI scaffold, not the full product implementation. Source maps describe intended scope and must not be mistaken for implemented code.
