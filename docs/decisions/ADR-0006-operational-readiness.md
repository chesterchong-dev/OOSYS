# ADR-0006 — Operational Readiness Probe

- **Date:** 2026-10-21
- **Status:** Accepted for Phase 03 bounded foundation scope
- **Context:** The existing /health endpoint is liveness-only. Operators and orchestrators need a distinct readiness signal without changing existing liveness behavior or triggering migrations at startup.
- **Decision:** Add unversioned GET /health/ready. If database configuration is absent, return HTTP 503 with a generic not_ready status. If configured, execute SELECT 1 using the existing SQLAlchemy engine factory; reuse an engine already created by the identity request dependency, otherwise dispose the temporary engine after probing. Return HTTP 200 only after the query succeeds. On connection/query failure, return generic HTTP 503 and do not return exception text, SQL, or connection details.
- **Alternatives:** Treat liveness as readiness (rejected because it produces false positives); connect at app startup (rejected because construction must remain side-effect-free); report detailed DB errors (rejected due to information disclosure).
- **Security and compatibility:** Existing /health response is unchanged. The probe requires no authentication because it exposes only coarse service readiness. It reveals no dependency details beyond ready/not_ready. No migration or schema change is required.
- **Limitations:** Checks only database connectivity/query ability, not migration version, mail, storage, search, external connectors, AI, or end-to-end application readiness. Production topology and orchestrator integration remain unverified.
- **Verification:** Tests cover unconfigured database, successful query, generic failure response and temporary engine disposal. Exact-commit CI is the acceptance gate; do not treat the implementation as verified until that run passes.
