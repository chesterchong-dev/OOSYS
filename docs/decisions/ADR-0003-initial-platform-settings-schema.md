# ADR-0003: Initial Versioned Schema — Platform Settings

- **Date:** 2026-10-18
- **Status:** Accepted for Phase 01 foundation.

## Context

Phase 01 requires a real, versioned migration baseline while avoiding Phase 02 identity, authentication and tenant provisioning. The master product map calls for configuration management, including environment configuration, tenant settings, user preferences and connector configuration. Only deployment-wide, non-secret settings are safe to model before identity and tenant authorization exist.

## Decision

- Use Alembic with SQLAlchemy 2 metadata; migration execution is an explicit operator/CI action and never runs during import or application construction.
- The first revision `20261018_0001` creates `platform_settings` for deployment-wide, non-secret values. It includes a bounded primary key, JSON value, optional description, timestamps and a non-empty-key constraint.
- Do not store credentials, tokens, tenant/user preferences or connector secrets in this table. Keep secrets in environment/secret management; defer tenant/user settings and connector configuration to their owning modules with authorization and audit controls.
- Test clean creation, repeated upgrade, schema constraints, downgrade/re-upgrade and missing-database-URL failure using isolated SQLite databases.
- PostgreSQL remains the production target, but these SQLite tests do not substitute for a live PostgreSQL migration run.

## Compatibility and rollout

This is the first revision and has no prior schema to upgrade. Deployments must run `alembic upgrade head` explicitly before using the table. Downgrade removes the table and its contents; therefore downgrade is destructive and must not be used against production without an approved backup/data-loss decision. Future revisions must preserve forward upgrade compatibility and include migration tests.

## Deferred

No settings CRUD endpoints, tenant-scoped settings, audit records, identity/session tables, business-domain tables or automated startup migrations are introduced by this decision.
