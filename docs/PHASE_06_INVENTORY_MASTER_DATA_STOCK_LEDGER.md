# Phase 06 — Inventory Master Data & Stock Ledger

**Status:** In progress; local implementation with synthetic data. Cloud and live-data release checks remain deferred per `MASTER_DEVELOPMENT_ROADMAP.md`.

## Scope

Implement tenant-scoped stockable product/SKU data, categories, units of measure, barcodes, balances, reservations, adjustments/counts, append-only movement history, and lot/serial trace references. The feature set maps to OOSYS-INV-027, INV-029, INV-035 and INV-036. Warehouse and bin hierarchies, receiving/putaway/picking, and warehouse transfers remain Phase 07 scope.

Inventory owns stockable SKU identifiers and the stock ledger. Product Lifecycle & Engineering will own controlled product specifications and revisions. Warehouse Management will own physical warehouse/location records and will consume the ledger contract without maintaining duplicate stock balances.

## Initial operating rules

- Stock quantities and costs use fixed-precision decimal storage, with up to six decimal places; each unit defines its allowed quantity precision.
- Negative on-hand or available stock is rejected. Reservations do not change on-hand quantity and cannot exceed available stock.
- Every stock mutation is an immutable ledger row with an organization-scoped idempotency key. A repeated identical request returns the original movement; reusing its key for different content is rejected.
- Movement posting locks the per-product balance row in PostgreSQL, updates the balance and appends the ledger movement in the same transaction.
- A product can be tracked by no identifier, lot, or serial. Lot-tracked movements require a lot code; serial-tracked movements require one serial per unit and reject receipt of a serial that is already in stock.
- Product cost currency is configurable per SKU and defaults to MYR for the initial Malaysia-oriented setup. Receipts with a supplied cost update a moving average. This is an inventory costing foundation only; it does not create accounting entries or support multi-currency conversion.
- Phase 06 balances are organization-wide. Phase 07 will add warehouse/location dimensions through a reviewed migration and contract change.

## API and user interface

API routes live under `/api/v1/organizations/{organization_id}/inventory`. Product and stock operations use separate permissions. All endpoints derive tenant identity from the authenticated principal, scope every read/write by that tenant, and record relevant actions in the existing audit log.

The frontend provides unit/category setup, product creation, stock posting, balances, and recent movement history. It uses the existing authenticated API; there are no mock success states.

## Deferred validation and limitations

- Local SQLite/API tests can verify request validation, tenant and permission denial, ledger math, idempotency, and migrations. PostgreSQL CI must verify RLS and movement concurrency.
- Cloud deployment, real monitoring/alert delivery, production backups/restores, independent security testing, staged rollback, and pilot data remain Phase 05 operational gates. No cloud resource is required for current development.
- Cost accounting integration, conversion between units, multi-currency valuation, warehouse locations, transfers, serial/lot lifecycle screens, and vendor/customer workflows are outside this phase's bounded slice unless a mapped acceptance criterion requires them.
- Do not accept the phase until its full mapped scope and tests are complete and the crosswalk/register are reconciled with evidence.

