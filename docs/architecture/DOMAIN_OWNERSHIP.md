# OOSYS Domain Ownership and Shared Contracts

**Status:** Proposed ownership baseline for Phase 01; cross-domain assignments below require product-owner sign-off before domain implementation. This document resolves obvious duplicate map entries for planning purposes; it does not change the source mind maps or mark requirements implemented.

## Ownership rules

1. Each business capability has one canonical domain owner for its records, invariants, lifecycle and write APIs.
2. A repeated topic in a map is a navigation alias or integration reference unless a decision explicitly defines separate bounded contexts. It must not produce duplicate tables or competing write APIs.
3. A domain may read another domain's published API/application contract or consume its versioned events. It must not import another domain's ORM models, tables or private repositories.
4. Shared platform services provide reusable mechanisms; business domains own their policies and domain-specific state transitions.
5. Cross-domain writes that must be atomic belong in one application use case/transaction where possible. Otherwise use durable events/outbox, idempotent consumers and reconciliation.
6. Every tenant-owned contract must carry tenant context derived from verified identity/membership; never trust a caller-supplied tenant ID as authorization.

## Proposed canonical ownership

| Capability | Canonical owner | Boundary and consumers |
|---|---|---|
| User identity, organisation membership, sessions, roles and permissions | Identity & Access (shared platform; Phase 02) | Publishes verified actor, organisation membership and permission decisions. Business domains do not own passwords or reimplement authorization. |
| Tenant provisioning, organisation hierarchy and tenant lifecycle | Identity & Tenant Administration | SaaS Commercial Readiness may initiate onboarding/suspension workflows; tenant lifecycle state and isolation remain owned by the shared identity/tenant domain. |
| Global and tenant configuration, preferences, connector configuration | Platform Configuration | Provider-specific adapters own secret use; configuration APIs enforce tenant scope, validation, permissions, versioning and audit. |
| Subscription plans, subscription state, entitlements and billing-provider adapters | SaaS Commercial / Entitlements | Owns plan lifecycle and server-side feature/usage enforcement. Finance owns the general ledger and accounting policy, not SaaS access decisions. |
| Customer/account, contact, lead, opportunity and CRM activity | CRM | Canonical customer relationship records. Sales, marketing, service and messaging integrations reference CRM IDs through contracts. |
| Sales territories, representative assignment, quotas and commissions | Sales Force Management | References CRM accounts/leads/opportunities; does not create competing customer or opportunity masters. |
| Quotes, sales orders, order lifecycle and fulfilment coordination | Sales & Order Management | Canonical owner for commercial orders. Repeated Sales and Order Management topics are treated as references to this domain, not separate implementations. |
| Campaigns, journeys, segmentation, consent-aware messaging and attribution | Marketing Automation | Uses CRM identities and published consent/preferences; does not own the customer master. |
| Purchasing, supplier records and purchase orders | Procurement & Supplier Management | Owns supplier/procurement workflow. Finance consumes approved payable/invoice facts; inventory consumes receipt/movement events. |
| Stock balances, locations, handling units, picking, packing, transfers and warehouse execution | Warehouse Management (WMS) | Owns warehouse operations and stock movement records. Sales, purchasing, production and finance integrate through stable contracts. |
| General ledger, AP/AR accounting, financial periods, tax and financial reporting | Finance & Accounting | Owns accounting records and postings. Operational modules emit source facts; they do not write ledger tables directly. Money uses decimal types. |
| Demand/material planning (MRP) | Planning domain, with one canonical owner to be confirmed during module design | The master map lists MRP under both ERP/finance and manufacturing. Before implementation, decide whether planning is a distinct domain or owned by Production Planning; do not build two MRP engines. Procurement, inventory and production remain consumers/providers through contracts. |
| Product master, engineering revisions, BOM and engineering change control | Product Lifecycle & Engineering | Owns controlled product specifications and revisions. Production and inventory consume released revisions; no direct private-table writes. |
| Production plans, work orders, execution, consumption, yield and downtime | Production Planning & Manufacturing Execution | Owns shop-floor execution. Consumes released BOM/revisions and material availability through contracts. |
| Inspections, nonconformance, corrective/preventive actions and quality disposition | Quality Management (QMS) | QMS appears under both supply chain and product lifecycle in the map; treat these as navigation references to one canonical QMS domain. Define interfaces to inventory, engineering and production. |
| Project plans, tasks, dependencies, milestones, resource/budget tracking | Project & Resource Management | Owns project/task lifecycle. Other modules may link work items but must not create a second project/task master without a deliberate bounded-context decision. |
| Workflow definitions, triggers, execution history, retries and routing engine | Shared Workflow Platform | Provides execution mechanics. Each domain owns its approval rules, state machine and allowed transitions; workflow engine cannot bypass domain authorization or invariants. |
| Audit trail, notifications, files, search, observability and common integration APIs | Shared Platform Services | Reusable mechanisms with access policy enforced at the owning domain boundary. Audit events identify actor, tenant, action, target, time and outcome. |
| WhatsApp, email, website, social, accounting and external provider connectivity | Integration Hub / provider adapters | Owns credentials, webhook verification, retries, idempotency and provider mapping. Business records remain owned by their domain. |
| AI model-provider adapters, AI orchestration and automation suggestions | AI & Automation Platform | Uses only authorized data and approved domain contracts. Sensitive actions require explicit authorization and human approval where specified. |
| Shared navigation, UI shell and reusable design system | Experience Platform | Shared frontend components only; business screens remain owned by their module. Backend authorization is mandatory regardless of UI visibility. |

## Contract and dependency implications

- Preferred direction: transport/API -> application use case -> domain and ports; persistence/infrastructure implement ports and are wired at the composition root.
- No circular domain imports. If two domains need each other's data, define a stable contract/event and identify the authoritative owner for each field.
- Shared identifiers should be stable and opaque; do not expose ORM internals as API contracts. Include tenant scope and authorization implications in schema review.
- Event contracts must be versioned, consumers idempotent, and failure/replay/reconciliation behavior documented.
- Before changing an existing shared API, permission, event or schema, inspect all consumers, record additive/breaking compatibility impact, and add contract tests.
- CRM vs Sales, Finance vs MRP, and duplicated QMS/Workflow/Project topics are explicit boundary-review items. Proposed ownership above is not a substitute for domain-owner sign-off.

## Evidence and current gaps

The connected master map OOSYS — Only One System (198 topics) and Developer Implementation Blueprint (four sheets: 143, 173, 132 and 181 topics) were read during Phase 01 review. The maps include shared platform foundation, identity/tenant, settings, entitlements, integration hub, AI/automation, CRM/sales, finance, supply chain/WMS, engineering/manufacturing, QMS and project tracking. The live repository contains the 87-row requirements register and 87-row source crosswalk; they are traceability artifacts, not runtime implementation.

The current repository scaffold has no business-domain packages, database mappings/repositories, migrations, identity/session services, frontend or domain APIs. Do not create empty module packages merely to mirror the map. Build a domain only when its phase begins and its contract/acceptance criteria are agreed.
