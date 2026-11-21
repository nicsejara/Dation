# J1.02 G1 — implementation contract

## Entities and routes

Keep CasePolicy V1 byte-compatible. `DecisionCaseDefinitionV2` wraps six blocks, model family/version/config/contract hashes, manual approval, own-fleet cost tie and one coverage KPI, explicit Case work/source IDs. A V2 Case create subtype carries that definition through the existing preparation creation intent. Ordinary create retains its V1 DTO and exact defaults.

Private immutable definition revisions store canonical server snapshots, hash, previous revision, mutation ID, actor and lineage. The current pointer is the highest revision; no destructive restoration. Model version remains immutable. Derived Cases have new IDs and reference an authorized exact source revision (or explicitly legacy source). CAS and mutation replay use existing workspace locks. All writes go through service-only checked RPCs.

Versioned opt-in resource `journey_version=v2` on the existing Case route uses typed `case_view`, `case_mode`, `case_work_id`, `definition_revision_id`; legacy `core_step` never changes meaning. No policy/PII in URL. J1.01 `rememberReturn`/`resolveReturn` is reused. Graph opens server-backed Review; explicit edit/derive only.

## Mathematical decision

Preserve the established lexicographic HIGH/MEDIUM/LOW maximum-service frontier. On that frontier minimize integer minor-unit cost, then, ONLY after OPTIMAL cost proof, maximize canonical primary-dimensional quantity allocated to OWN, then deterministic stable tie. This does not trade service for cheaper omissions. Secondary preference is supported only with MINIMIZE_COST and without goal override; otherwise reject, never ignore it. Incomplete candidate scope/timeout marks proof unverified. Existing hard critical guardrail is reused, tested independently, and displayed NOT_APPLICABLE with zero HIGH denominator.

KPI uses D1 canonical demand-resolution quantities in the pinned primary dimension, validated lineage and result fingerprints; never counts boxes+pallets as unrelated objects. Catalog quantities use existing physical normalizers, unchanged. Zero/invalid/incomplete/infeasible/unknown/mismatched basis is NOT_EVALUABLE. PENDING before a run, MEETS/MISSES after a valid result. D2 only references D1; evaluation never changes approvals.

The full revision UUID/hash is pinned in Run/context/artifacts. Only these two administrative identifiers are excluded from the mathematical input projection, in both SQL and Python. Business rules and acceptance policy remain included. Metadata-only revision cannot invalidate identical mathematical inputs or rebind an already approved D1/D2 pair.

## Thin data bridge

Confirmed definition remains a browser working draft. Existing Core Preparation receives only the explicitly selected published version and compiler contracts. It persists stable session, Case intent and full V2 definition before finalize. Begin freezes the whole body; atomic Case+initial definition creation occurs inside checked SQL, with recoverable Pack publication as already designed. Model changes require a new preparation and preserve the old session/candidates. Session recovery cannot import another definition intent.

## Safety / rollback

`DATION_J102_ENABLED=false` plus database release flag false and existing cohort/foundation/data gates. Writes fail closed, independently of DOM. V1 reads stay unchanged; V2 readers remain available when writer flag goes OFF. SQL proposed in repository and tested on isolated PostgreSQL17 only. No production migration/merge/release. Rollback stops writers and preserves revision/Run data; never DROP history.
