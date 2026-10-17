# OOSYS Requirements Register

**Status:** PARTIAL — reconciled against baseline `phase-00-02-starter` at `029fc55bd74a69a19532b5a25099fa65469c5403`.  
**Canonical CSV:** [`requirements_register.csv`](./requirements_register.csv)  
**Source UUID crosswalk:** [`REQUIREMENT_SOURCE_NODE_CROSSWALK.csv`](./REQUIREMENT_SOURCE_NODE_CROSSWALK.csv)

The register preserves 87 requirement rows, 14 columns and 87 stable IDs. Statuses remain 84 `missing` and 3 `partial`. “Missing” means no implementation was found in the audited branch snapshot, not that no work exists elsewhere.

## Traceability
Each row's `Source Location` points to the crosswalk and verified topic UUID. Match counts: exact_title=15, semantic_feature=34, semantic_parent=32, proxy_gap=3, duplicate_title_disambiguated=3. `proxy_gap` means the selected topic is related but not adequate direct traceability; the three affected requirements remain unresolved.

## Status rules
- `verified implemented`: code reviewed and acceptance evidence executed.
- `implemented, unverified`: implementation exists but acceptance verification is incomplete.
- `partial`: only part of the requirement is evidenced in the branch.
- `missing`: no implementation for the requirement exists in the audited branch snapshot.
- `blocked`: a concrete dependency/access issue prevents assessment or completion.
- `not verified`: evidence is insufficient to determine status.

Do not mark a requirement complete from a roadmap or documentation checklist alone. Completion requires implementation paths/symbols, acceptance tests and command output, commit SHA, dependencies, security implications and unresolved gaps.
