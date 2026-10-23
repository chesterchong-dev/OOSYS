# Phase 05 — Operational Acceptance Plan

**Status: Proposed acceptance criteria; production operations are not configured or verified by this repository task.**  
**Applies to:** OOSYS Phase 05, PR #1, phase-05-security-observability  
**Latest verified checkpoint before this acceptance-record update:** PR head 4cfb46209fa4029ad41a7edda02a2f4e73be832d. All three PR workflows succeeded on that exact SHA: Phase 00 validation run [39962507916](https://github.com/chesterchong-dev/OOSYS/actions/runs/39962507916), Dependency Audit run [39962507847](https://github.com/chesterchong-dev/OOSYS/actions/runs/39962507847), and Secret Scan run [39962507931](https://github.com/chesterchong-dev/OOSYS/actions/runs/39962507931). This establishes repository CI only, not production operational acceptance. This acceptance-record update changes the branch HEAD, so the new head must receive its own workflow verification before acceptance.  
**Decision rule:** A documented plan is not proof that a production control is deployed. Keep Phase 05 In Progress until the applicable evidence exists.

## 1. Current repository verification

At PR head `4cfb46209fa4029ad41a7edda02a2f4e73be832d`, commit-scoped GitHub Actions records confirm all three workflows completed successfully:

| Workflow | Run | Result | Verified job evidence |
|---|---:|---|---|
| Phase 00 validation | [39962507916](https://github.com/chesterchong-dev/OOSYS/actions/runs/39962507916) | Success | Backend tests, SQLite migration upgrade/downgrade, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL backup/restore, PostgreSQL downgrade and compileall; frontend unit tests and production build |
| Dependency Audit | [39962507847](https://github.com/chesterchong-dev/OOSYS/actions/runs/39962507847) | Success | pip-audit step succeeded |
| Secret Scan | [39962507931](https://github.com/chesterchong-dev/OOSYS/actions/runs/39962507931) | Success | Gitleaks history scan succeeded |

This supersedes the earlier note that Phase 00 validation at this checkpoint was pending. The disposable PostgreSQL restore uses synthetic CI data in a temporary database. It does not establish production backup policy, central monitoring, production deployment or independent security testing. Any subsequent commit changes HEAD and requires a separate exact-head workflow check.

## 2. Production backup, encryption, retention and access

### Proposed baseline — approval required

The following are recommended acceptance targets, not current production settings:

- **Backup frequency:** continuous WAL/PITR or an equivalent mechanism with a maximum 15-minute recovery-point gap; at least one daily full/base backup.
- **Retention:** 35 daily recovery points and 12 monthly recovery points, subject to legal, privacy and cost review.
- **Encryption:** TLS in transit and provider-supported encryption at rest; managed keys with restricted key administration and documented rotation/revocation.
- **Off-site isolation:** store backups in a separate account/project or security boundary from the primary database. Enable versioning/immutability where supported and prevent the application runtime identity from deleting backup history.
- **Access:** dedicated backup and restore identities, least privilege, MFA for human administrators, audited access, no shared credentials, and tested break-glass access.
- **Restore rehearsal:** at least quarterly and after material database/backup changes; restore into an isolated target and verify schema revision, row-count/integrity checks, and critical application workflows.

### Required evidence before acceptance

1. Product owner approves retention, data residency, encryption/key ownership and access policy.
2. Name the production database and backup provider/environment; record the configuration location without committing credentials.
3. Provide sanitized configuration/export evidence showing schedule, retention, encryption, off-site boundary, immutability/versioning and access policy.
4. Execute a restore into an isolated environment using a representative encrypted backup.
5. Record run timestamp, source backup timestamp, recovered data point, measured RPO/RTO, integrity checks, operator and outcome.
6. Demonstrate denied access for an unauthorized identity and prove application credentials cannot erase backup history.

**Current status:** Blocked on production environment/provider access and owner-approved retention/security decisions. No production backup configuration was inspected in this task.

## 3. RPO and RTO

### Proposed service objectives — product-owner approval required

| Objective | Proposed target | Measurement |
|---|---|---|
| Recovery Point Objective (RPO) | At most 15 minutes of committed-data loss | Compare latest recoverable transaction/WAL position with incident cut-off during a timed restore drill |
| Recovery Time Objective (RTO) | Core API and database restored to validated service within 4 hours | Measure from declared recovery start until health/readiness and critical identity/API smoke tests pass |

These are planning targets, not measured guarantees. If the product owner approves different targets, update this document before accepting recovery controls.

**Acceptance test:** simulate loss of the primary database in a non-production environment; restore from the documented off-site backup/PITR chain; record timestamps and data-point checks; calculate actual RPO and RTO; verify migrations, readiness and critical application operations. Pass only if measured results meet the approved targets. Record any data loss and corrective actions.

**Current status:** The disposable CI restore drill passed, but it does not measure production RPO/RTO. Production targets and recovery timing remain unverified.

## 4. Central metrics and alert delivery

### Required design decision

Select a supported central metrics/alerting destination only after deployment ownership, cost, data-residency and access requirements are approved. Keep provider credentials outside source control. Do not expose /metrics publicly; it is currently optional, token-protected and process-local.

### Acceptance criteria

1. Metrics from every production application instance are collected centrally, or the selected platform's equivalent service telemetry is enabled.
2. Use bounded labels only; do not add tenant IDs, user IDs, URLs with identifiers, query strings or secrets as metric labels.
3. Configure actionable alerts for sustained elevated server-error rate, readiness failure, unavailable database, missing telemetry, backup failure, restore-test failure and critical dependency/security findings. Set thresholds and evaluation windows based on baseline load and agreed SLOs.
4. Route alerts to a named, monitored destination with an on-call owner and escalation path.
5. Trigger a controlled test alert and verify end-to-end delivery, acknowledgement, resolution and audit trail.
6. Verify alerts do not contain passwords, tokens, connection strings or unnecessary personal data.
7. Test a monitoring outage or missing-data condition so silent telemetry loss is detectable.

**Current status:** Metrics code is process-local; no central collector, alert routing destination or end-to-end alert delivery was verified. Blocked pending environment access and a provider/ownership decision.

## 5. Staged deployment and rollback

### Required release controls

- Separate development, staging and production configuration and secrets.
- Require successful backend tests, migration checks, frontend tests/build, dependency audit and secret scan before promotion.
- Deploy first to staging using a versioned immutable artifact; record artifact/commit SHA and configuration version.
- Run smoke tests for /health, /health/ready, login/session revocation, key administrative API flows, CORS/security headers and metrics access policy.
- Require explicit production approval and a documented change/rollback owner.
- Keep database migrations backward-compatible where feasible; never assume application rollback reverses a migration safely.
- Document rollback trigger thresholds, traffic/configuration rollback steps, migration/data compatibility and recovery escalation.
- Run one staging rollback rehearsal and verify the prior version is healthy, data remains consistent and the incident/change record is complete.

### Acceptance evidence

Retain staging deployment URL/environment identifier (without secrets), commit/artifact digest, approval, smoke-test results, rollback timestamps, prior/current version, database migration state, and post-rollback integrity results.

**Current status:** Repository CI is verified, but no staging/production environment, deployment provider, promotion gate or rollback rehearsal was available to verify. Do not treat GitHub CI as a deployment.

## 6. Independent penetration test

An independent penetration test is a release-governance requirement to be planned and commissioned; no external penetration test is claimed as performed.

### Scope

- Authentication, session expiry/revocation, password-reset and invitation flows.
- Authorization/RBAC and cross-tenant isolation, including direct object references.
- CORS, security headers, API input validation, injection and error handling.
- Rate limiting, abuse resistance and denial-of-service exposure at agreed safe limits.
- Secrets, logging/redaction, metrics endpoint protection and deployment configuration.
- Dependency/supply-chain findings and any externally exposed staging surface.

### Acceptance evidence

1. Approve an independent tester, scope, rules of engagement and authorized staging target.
2. Record report date, tested commit/build, environment, methodology and findings without exposing exploit details publicly.
3. Triage each finding with severity, owner, deadline and risk acceptance where remediation is deferred.
4. Fix and retest critical/high findings; record retest evidence.
5. Obtain an explicit security-owner sign-off or documented exception before production release.

**Current status:** Not performed or independently verified. Requires budget/owner authorization and an available staging target.

## 7. Requirements and XMind traceability

The authoritative source-node crosswalk remains the mapping authority. The following mappings were checked against docs/requirements/REQUIREMENT_SOURCE_NODE_CROSSWALK.csv; classifications should not be changed merely to imply implementation completion.

| Requirement | Source-map topic | Current scoped evidence | Remaining gap / status |
|---|---|---|---|
| OOSYS-CORE-012 | Master product map → Monitoring, alerting and system health (UUID cec50571-060b-40c9-9db1-b998f61cd633) | Safe structured logs, request correlation, health/readiness contract preservation, protected optional metrics; current-head CI passed | Central aggregation, alert routing and operational rehearsal absent; **partial** |
| OOSYS-CORE-014 | Developer Implementation Blueprint → Database backups and tested restoration procedure (UUID a5fbc39e-75c2-475c-96fa-902a2d9ad2d8) | Disposable PostgreSQL CI backup/restore drill passed | Production encryption, off-site isolation, retention, access controls and measured RPO/RTO absent; **partial** |
| OOSYS-CORE-015 | Master product map → Security and privacy controls (UUID fd661627-b52f-445c-aea6-6ae1b11ea1ca) | Secret/config validation, headers, strict CORS, abuse tests, dependency and secret scanning | Independent penetration test and production deployment security review absent; **partial** |
| OOSYS-OPS-085 | Master product map → Monitoring, alerting and system health (UUID cec50571-060b-40c9-9db1-b998f61cd633) | Runbooks, request logs, protected metrics and disposable restore evidence | Production telemetry, actionable alert delivery and recovery exercise absent; **partial** |
| OOSYS-OPS-087 | Developer Implementation Blueprint → Release safeguards (UUID b9295810-5c16-4cc2-872c-e5e9a6770c76) | CI tests/build, dependency audit and Gitleaks scan pass on current known PR head | Staged promotion, release approvals, rollback rehearsal, dedicated type-check/lint and independent security review absent; **partial** |

The IDs, titles, source maps, UUIDs and match classifications above match the current crosswalk. Keep each requirement partial until its full acceptance criteria—not just this phase's bounded slice—are met.

## 8. Blockers and decisions required

| Blocker | Required owner action | Exit evidence |
|---|---|---|
| No production backup/metrics/deployment environment available to this repository task | Provide approved environment access or designated operator and sanitized evidence | Configuration review plus successful drills |
| Backup retention, key ownership and data residency not approved | Product/security owner approves policy | Recorded decision and deployed configuration |
| RPO/RTO targets not approved | Product owner approves or revises proposed 15-minute RPO / 4-hour RTO | Approved objective and timed restore evidence |
| Central monitoring provider and alert recipient not selected | Operations owner chooses provider, budget and monitored destination | Central ingestion and test alert receipt |
| Staging release/rollback not configured | Release owner provisions staging and defines promotion/rollback policy | Staging deployment and rollback rehearsal |
| Independent penetration test not commissioned | Security owner approves scope, tester and budget | Signed report, remediation/retest and disposition |

## 9. Final acceptance gate

Phase 05 remains **In Progress** until:
- Current-head CI, dependency audit and secret scan are successful.
- Security and recovery regression tests pass without contract weakening.
- Production backup controls and restore evidence meet approved policy.
- Measured RPO/RTO meet approved targets.
- Central metrics and end-to-end alert routing are verified.
- Staged deployment and rollback are rehearsed.
- Penetration testing is completed or explicitly dispositioned by the authorized security owner.
- Requirements register, phase record and roadmap statuses match the evidence.
- The pull request has been reviewed and remains open until acceptance is explicitly authorized.

No production service, production backup, monitoring provider, deployment or penetration test is claimed operational by this document.


## Current intended-head CI verification (2026-10-23)

The previous implementation checkpoint above is historical. The repository's current intended head at the start of this acceptance review was `6bf79bcb1a729fa6df56f6b5f8f07c2fb1e3f825`. GitHub's commit-scoped workflow lookup returned these completed successful runs for that SHA:

- [Phase 00 validation, run 39960204359](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960204359): backend job passed, including test suite, SQLite migration lifecycle, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL restore, PostgreSQL downgrade and compileall; frontend unit tests and production build job passed.
- [Dependency Audit, run 39960204581](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960204581): pip-audit job passed.
- [Secret Scan, run 39960204464](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960204464): Gitleaks history scan job passed.

These are CI results for the intended SHA, not production operational evidence. The combined commit-status endpoint returned no separate status entries; the three workflow-run records and their jobs above are the evidence. Any subsequent commit changes the HEAD and must be checked separately before final acceptance. The Phase 00 disposable restore remains synthetic CI data only.


## Follow-up exact-head CI result — documentation HEAD b80148e6f6c9bfe3409a2b7a82600191e78cbdaa

The follow-up verification requested for this documentation head is now complete:

- Phase 00 validation [39960856737](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960856737) — workflow conclusion success. Backend job passed tests, isolated SQLite migration upgrade/downgrade, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL restore, PostgreSQL downgrade and compileall. Frontend unit tests and production build passed.
- Dependency Audit [39960856880](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960856880) — success.
- Secret Scan [39960856652](https://github.com/chesterchong-dev/OOSYS/actions/runs/39960856652) — success.

These results are for the exact SHA above. The restore evidence is still a disposable CI database using synthetic data; it does not close the production recovery gap. This paragraph is an acceptance-record update, so the new documentation commit will itself need its own exact-head CI check. No production infrastructure, approval, central alert delivery, staged release/rollback or independent penetration test was available or verified.


## Exact-head verification and exit blockers — 2026-10-23

Live GitHub verification at checkpoint `5a690acfdc5096bdec31497f6ea9e25fe6a29505` confirms all three pull-request workflows succeeded:

- [Phase 00 validation — run 39961354573](https://github.com/chesterchong-dev/OOSYS/actions/runs/39961354573): backend and frontend jobs passed. Backend steps passed tests, SQLite migration upgrade/downgrade, PostgreSQL migration/persistence, recovery-token concurrency, disposable PostgreSQL backup/restore, PostgreSQL downgrade and compileall; frontend unit tests and production build passed.
- [Dependency Audit — run 39961354869](https://github.com/chesterchong-dev/OOSYS/actions/runs/39961354869): success.
- [Secret Scan — run 39961354686](https://github.com/chesterchong-dev/OOSYS/actions/runs/39961354686): success.

This replaces the earlier pending statement for Phase 00 validation at this checkpoint. These workflow results are CI evidence only; they do not establish production operational acceptance. The new documentation commit will need its own exact-head workflow verification.

| Requirement | Blocker and responsible owner role | Exit evidence |
|---|---|---|
| OOSYS-CORE-012 | No configured central collector, alert route or missing-telemetry watchdog is evidenced; metrics are process-local. Platform/operations owner must select the monitoring destination, provide access and name an on-call receiver. | Approved thresholds/routes; sanitized configuration; delivery receipt, acknowledgement and resolution; missing-telemetry alert test; proof labels/logs exclude secrets and tenant/user identifiers. |
| OOSYS-CORE-014 | Production backup provider/environment, retention, encryption/key controls, isolated storage and production-equivalent restore are not evidenced. Product owner approves retention/data residency and recovery objectives; database/platform owner configures backup and restore. | Sanitized configuration; unauthorized-access denial; representative encrypted backup restored to an isolated target; integrity checks; timestamped measured RPO/RTO and operator/outcome. |
| OOSYS-CORE-015 | Independent authorized penetration test and remediation/retest evidence are absent. Security owner authorizes scope and tester; risk owner disposition residual findings. | Authorized scope, independent report, remediation and retest evidence, formal disposition of residual risk. |
| OOSYS-OPS-085 | Production on-call destination and timed operational recovery rehearsal are not evidenced. Operations owner names incident commander/on-call receiver and approves rehearsal. | End-to-end alert lifecycle evidence, timed isolated recovery rehearsal, after-action report and tracked remediation. |
| OOSYS-OPS-087 | Staging environment, promotion approval, immutable artifact provenance and rollback rehearsal are not evidenced. Release owner approves release flow/triggers; platform owner provides environment and provenance. | Staging promotion tied to immutable artifact digest/commit; approvals and smoke tests; documented triggers/owner; successful timed rollback and post-rollback validation. |

RPO ≤15 minutes and RTO ≤4 hours remain proposed, unapproved targets. Product-owner approval and measured recovery results are required before they can be represented as accepted objectives. No provider, credential, environment, approval or operational test result is assumed.
