# OOSYS Requirements Register

**Status:** Traceability artifact; each requirement status is grounded in the current branch and its verification evidence.  
**Canonical CSV:** [requirements_register.csv](./requirements_register.csv)  
**Source UUID crosswalk:** [REQUIREMENT_SOURCE_NODE_CROSSWALK.csv](./REQUIREMENT_SOURCE_NODE_CROSSWALK.csv)

The live register contains 87 requirement rows, 14 columns and 87 unique stable IDs. Current implementation status counts are 79 `missing` and 8 `partial`; identity-related partial statuses describe the implemented Phase 02 slice and do not imply the full OOSYS platform is complete. Phase 02 records implementation evidence for CORE-001 (tenant/organisation management), CORE-002 (authentication/sessions), CORE-003 (RBAC), CORE-004 (organisation hierarchy) and CORE-006 (audit logging). Code-verification CI run [39110600679](https://github.com/chesterchong-dev/OOSYS/actions/runs/39110600679) passed on commit `4c84c3fcf4b1a18a5fa41f2734a2af2af5ab5615` with 46 passed, 2 PostgreSQL-only tests skipped in the standard suite; dedicated PostgreSQL concurrency tests passed 2 tests; 91% `app.identity` coverage, migration checks, restricted-role PostgreSQL RLS probes, two concurrency regressions and compileall. Documentation-only HEAD `54d85138551460a1226ad0a35f174b9ae7158886` passed run [39111339023](https://github.com/chesterchong-dev/OOSYS/actions/runs/39111339023), and evidence-reconciliation HEAD `eb2433b70c303c5496c913b88f48fc38635a8ed8` passed exact-HEAD run [39112486983](https://github.com/chesterchong-dev/OOSYS/actions/runs/39112486983); these runs verify documentation/evidence commits, not new application behavior. Phase 02 acceptance remains OPEN pending local working-tree evidence; dedicated type-check/lint/frontend-build tools are not configured and are not claimed. CORE-005 shared master data remains missing and belongs to a subsequent phase. Traceability and identity tests do not imply completion of the remaining OOSYS product map.

## Traceability

The live crosswalk contains 87 rows and 8 columns, with the same 87 requirement IDs as the register. Normalized mapping counts are: exact_title=15, semantic_feature=37 (34 semantic feature matches plus 3 resolved dedicated source topics for settings/configuration, subscription/entitlements, and SaaS commercial readiness), semantic_parent=32, duplicate_title_disambiguated=3. There are no unresolved proxy-gap or partial-coverage classifications in the current crosswalk. The long “Resolved” descriptions in the CSV classification column are normalized as semantic-feature coverage for these counts; preserve the detailed review notes.

The canonical sources were inspected through the connected Xmind account:
- Master product map, “OOSYS — Only One System”: 198 topics.
- Developer Implementation Blueprint: four sheets with 143, 173, 132 and 181 topics (629 total).

Traceability confirms where requirements are represented in the source maps; it is not proof of implemented functionality. Cross-domain ownership overlaps are documented in [DOMAIN_OWNERSHIP.md](../architecture/DOMAIN_OWNERSHIP.md) as proposed boundaries requiring product-owner sign-off.

## Status rules

- `verified implemented`: code reviewed and acceptance evidence executed.
- `implemented, unverified`: implementation exists but acceptance verification is incomplete.
- `partial`: only part of the requirement is evidenced in the branch.
- `missing`: no implementation for the requirement exists in the audited branch snapshot.
- `blocked`: a concrete dependency/access issue prevents assessment or completion.
- `not verified`: evidence is insufficient to determine status.

Do not mark a requirement complete from a roadmap or documentation checklist alone. Completion requires implementation paths/symbols, acceptance tests and command output, commit SHA, dependencies, security implications and unresolved gaps.
