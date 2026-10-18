# OOSYS Requirements Register

**Status:** PARTIAL — Phase 00 traceability artifact; implementation status is not inferred from the roadmap.  
**Canonical CSV:** [requirements_register.csv](./requirements_register.csv)  
**Source UUID crosswalk:** [REQUIREMENT_SOURCE_NODE_CROSSWALK.csv](./REQUIREMENT_SOURCE_NODE_CROSSWALK.csv)

The live register contains 87 requirement rows, 14 columns and 87 unique stable IDs. Implementation statuses remain 80 `missing` and 7 `partial`. “Missing” means no implementation was found in the audited branch snapshot, not that no work exists elsewhere. Phase 01 foundation tests do not implement the 87 business/platform requirements. Phase 02 implementation evidence is recorded for identity/tenant requirements CORE-001, CORE-002, CORE-003 and CORE-006 as partial with CI evidence (37 tests and 93% app.identity coverage on code commit 0a238a6926ab6b1296c42c2096dbcbb5922bc40e); requirements remain partial where scope is incomplete. CORE-004 organisation hierarchy remains missing.

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
