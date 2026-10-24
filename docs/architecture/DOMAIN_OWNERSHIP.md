# OOSYS Domain Ownership and Shared Contracts

**Status:** Accepted planning baseline for the OOSYS master-map boundaries reviewed in Phase 01. This records ownership decisions for subsequent module implementation; it does not change the source mind maps or claim the business domains are implemented. Revisit only through a documented ADR if a requirement demonstrates a genuine boundary conflict.

## Ownership rules

1. Each capability has one canonical owner for its records, invariants, lifecycle and write APIs.
2. Repeated map topics are navigation aliases or integration references unless a deliberate bounded-context decision says otherwise. They must not create duplicate tables or competing write APIs.
3. A domain reads another domain's published application/API contract or consumes versioned events. It must not import another module's ORM models, tables or private repositories.
4. Shared platform services provide reusable mechanisms; business domains own business policies and state transitions.
5. Cross-domain changes that must be atomic belong in one application use case/transaction where possible. Otherwise use durable events/outbox, idempotent consumers and reconciliation.
6. Tenant-owned contracts must use tenant context derived from verified identity/membership, never an untrusted caller-supplied tenant ID as authorization.

## Canonical ownership baseline

| Capability | Canonical owner | Boundary and consumers |
|---|---|---|
| User identity, organisation membership, sessions, roles and permissions | Identity & Access (shared platform; Phase 02) | Publishes verified actor, organisation membership and permission decisions. Business domains do not own passwords or reimplement authorization. |
| Tenant provisioning, organisation hierarchy and tenant lifecycle | Identity & Tenant Administration | Commercial onboarding may initiate lifecycle workflows; tenant state and isolation remain owned by identity/tenant administration. |
| Global and tenant configuration, preferences, connector configuration | Platform Configuration | Provider adapters own secret use; APIs enforce tenant scope, validation, permissions, versioning and audit. |
| Subscription plans, subscription state, entitlements and billing-provider adapters | SaaS Commercial / Entitlements | Owns plan lifecycle and server-side feature/usage enforcement. Finance owns the general ledger and accounting policy, not SaaS access decisions. |
| Customer/account, contact, lead, opportunity, forecasting, campaign and CRM activity | CRM | Canonical customer relationship records and relationship/sales-pipeline forecasts. Sales, marketing, service and messaging integrations reference CRM IDs through contracts. |
| Sales territories, representative assignment, quotas and commissions | Sales Force Management | References CRM accounts/leads/opportunities; does not create competing customer or opportunity masters. |
| Quotations, commercial pricing, sales orders, order lifecycle, fulfilment, delivery, returns and order tracking | Sales & Order Management | Canonical owner for commercial order records. Repeated Sales and Order Management topics are references to this one domain. |
| Demand planning, material availability calculations, purchasing requirements and production schedules (MRP) | Planning & MRP | One canonical planning domain. Produces demand/material plans and planned requirements/schedules; Procurement owns supplier selection, purchase orders and purchasing execution; Manufacturing owns work-order execution and actual production consumption. Finance consumes approved financial facts rather than operating a second MRP engine. |
| Purchasing, supplier records and purchase orders | Procurement & Supplier Management | Owns supplier/procurement workflow and purchase-order lifecycle. Finance consumes approved payable/invoice facts; inventory consumes receipt/movement events. |
| Stockable SKU identity, stock balances, movement ledger, reservations, adjustments and trace references | Inventory (Phase 06) | Owns the operational stock ledger and stockable product attributes (SKU, barcode, category and unit). Finance consumes cost-bearing stock facts; purchasing, sales, warehouse and manufacturing integrate through stable contracts. Product Lifecycle & Engineering owns controlled specifications/revisions, not inventory SKU identity. |
| Warehouses, locations, handling units, picking, packing, transfers and warehouse execution | Warehouse Management (WMS; Phase 07) | Owns the physical warehouse/location hierarchy and warehouse execution. It consumes the Inventory ledger contract and must not duplicate balances or movement records. |
| General ledger, AP/AR accounting, financial periods, tax and financial reporting | Finance & Accounting | Owns accounting records and postings. Operational modules emit source facts; they do not write ledger tables directly. Money uses Decimal and database numeric types. |
| Product master, engineering revisions, BOM and engineering change control | Product Lifecycle & Engineering | Owns controlled product specifications and revisions. Planning and manufacturing consume released revisions through contracts. |
| Work orders, shop-floor execution, actual consumption, yield and downtime | Manufacturing Execution | Owns actual production execution and records; consumes released engineering revisions and planned schedules, without taking ownership of the MRP plan. |
| Inspections, nonconformance, corrective/preventive actions and quality disposition | Quality Management (QMS) | One canonical QMS domain despite references under supply chain and product lifecycle. Defines interfaces to inventory, engineering and manufacturing. |
| Project plans, tasks, dependencies, milestones, resource/budget tracking | Project & Resource Management | Owns project/task lifecycle. Other modules may link work items but do not create a competing project/task master. |
| Workflow definitions, triggers, execution history, retries and routing engine | Shared Workflow Platform | Provides execution mechanics. Each domain owns approval rules, state machine and allowed transitions; workflow cannot bypass domain authorization or invariants. |
| Audit trail, notifications, files, search, observability and common integration APIs | Shared Platform Services | Reusable mechanisms; access policy remains enforced by the owning domain. Audit events identify actor, tenant, action, target, time and outcome. |
| WhatsApp, email, website, social, accounting and external provider connectivity | Integration Hub / provider adapters | Owns credentials, webhook verification, retries, idempotency and provider mapping. Business records remain owned by their domain. |
| AI model-provider adapters, AI orchestration and automation suggestions | AI & Automation Platform | Uses only authorized data and approved domain contracts. Sensitive actions require explicit authorization and human approval where specified. |
| Shared navigation, UI shell and reusable design system | Experience Platform | Shared frontend components only; business screens remain owned by their module. Backend authorization is mandatory regardless of UI visibility. |

## Contract and dependency implications

- Dependency direction: API/transport -> application use case -> domain and ports. Persistence/infrastructure implement ports and are wired at the composition root.
- No circular domain imports. If domains need each other's data, define a stable contract/event and identify the authoritative owner for every shared field.
- Shared identifiers are stable and opaque; ORM internals are not API contracts. Schema reviews record tenant scope and authorization implications.
- Event contracts are versioned; consumers are idempotent; failure/replay/reconciliation behavior is documented.
- Before changing a shared API, permission, event or database contract, inspect consumers, record additive/breaking compatibility impact and add contract tests.
- CRM owns relationship pipeline and its forecast; Planning & MRP owns material/demand planning. Sales & Order Management owns quotes and orders. This avoids conflating CRM sales forecasting with material requirements planning.
- Repeated QMS/workflow/project topics resolve to one canonical domain each. These boundaries are accepted for planning; detailed schemas, APIs, permissions and acceptance tests still belong to the phase that implements each module.

## Evidence and current gaps

The connected master map OOSYS — Only One System (198 topics) and Developer Implementation Blueprint (four sheets: 143, 173, 132 and 181 topics) were reviewed. The live repository register and source crosswalk each contain 87 requirement IDs; they are traceability artifacts, not runtime implementation.

The project-library CRM master prompt specifies a real modular-monolith CRM/SFA with database persistence, validated CRUD, search/filter/sort/pagination, frontend integration, and verifiable working behavior—not mockups or fake live data. That prompt is a product specification, not implementation evidence.

The current scaffold has no business-domain packages, domain models, domain repositories, migrations, identity/session services, frontend or business APIs. A generic SQLAlchemy engine/session lifecycle factory now exists, but no schema, model mappings or migration baseline is defined. Do not create empty business packages merely to mirror the map.

