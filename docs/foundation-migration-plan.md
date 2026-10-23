# Foundation migration plan

Baseline: `a8ebde935abaa28b6eb677a2e0e9c63a383dd9d8`. Each batch is independently
reviewable/revertible. No migration writes to Supabase. Never rerun old release
scripts with fixed PR/source SHAs.

| Phase / batch | Current → target; affected files | Risk / dependencies | Validation | Rollback |
|---|---|---|---|---|
| 0 Baseline | Record branch/SHA, inventory, OpenAPI, existing CI commands and failures outside runtime | none; isolate synthetic tests from production | compile, syntax, unit/Node, browser, SQL/API/E2E, container | no runtime changes |
| 1 Audit | real references/components/routes/SQL → `foundation-audit.md` | do not infer dead code from age | source/caller inventory, migration and contract inspection | docs-only revert |
| 2 Target | existing toolchain → documented feature boundaries | preserve runtime/model invariance | review `target-architecture.md` against actual call graph | docs-only revert |
| 3 Plan | explicit small batches, rename table, regression gates | no blanket string renames | this plan + baseline failure ledger | docs-only revert |
| 4a Structure | flat dispatch modules → cases/navigation/assignment/scheduling/runs directories; explicit static redirects for already-open tabs | import/lazy path breakage; no implementation changes in moved files | resolver, complete JS syntax, all Node/unit tests; old URLs return canonical source; browser critical routes | revert whole move/import batch |
| 4b Backend boundary | pure Case state/projection in service → `app/domain/decision_cases.py` | authoritative history and error semantics | parity vectors incl stale lineage, actual Case/Run API and SQL | revert extraction; SQL untouched |
| 5 Naming | imprecise internal navigation/preparation names → domain names | do not rename public URL/JSON/SQL/DOM/storage keys | OpenAPI equality, unit routing/ownership checks | revert local names/imports |
| 6 Consolidation | duplicate advanced-disclosure lifecycle → shared binder; result summary/status/trace separated by responsibility | lazy charts, storage restore, scope disposal | D1/D2 expanded/restored/closed states, chat/actions/export, responsive parity | revert binder/extraction and caller changes |
| 7 Cleanup | unreachable Case dropdown, callback, final-actions CSS → removed | prove no active markup/client/route references; retain compatibility | reachability, source references, current golden absence checks | restore removed batch |
| 8 Documentation | historical architecture text → current canonical docs + links | retain ADR/history links | verify documented paths and public contracts | docs-only revert |
| 9 Regression | stale fixtures/assertions → actual baseline contracts; full validation | never weaken security/ownership or skip failing tests | full Python/Node/browser/SQL/E2E, build/smoke, API parity, engine/SQL hashes | fix or revert failing batch; no rollout before gate |
| 10 Report / rollout | concrete evidence and retained debt → final summary and existing GitHub deployment | main source/worker must match tested tree | review diff, exact merge source, deployed assets/cache/health/auth and worker revision | redeploy previous known source/image; no DB rollback necessary |

## Explicit rename table

| Current | Target |
|---|---|
| `dispatch/navigation.mjs` | `dispatch/navigation/resource.mjs` |
| `dispatch/case-navigation.mjs` | `dispatch/navigation/case-flow.mjs` |
| `dispatch/run-polling.mjs` | `dispatch/runs/polling.mjs` |
| `dispatch/case-identity.mjs` and Case/map modules | same precise filenames under `dispatch/cases/` |
| `dispatch/assignment*.mjs` | same filenames under `dispatch/assignment/` |
| `dispatch/scheduling*.mjs` | same filenames under `dispatch/scheduling/` |
| `mountWorkflowContext` (one live preparation caller) | `mountCasePreparation` |
| `_base_state`, `_validate_state`, `_state_with_history` | pure `create_case_state`, `validate_case_state`, `project_case_history` |
| persisted `case_id`, `node_id`, `run_id`, SQL function signatures and `DC-` | unchanged |

## Verification policy

Run dependent changes sequentially. Capture failures at baseline before correcting
stale tests. Add meaningful characterization around extracted state and shared
presentation; preserve expected values rather than snapshotting the implementation.
Use disposable PostgreSQL/API/worker/browser fixtures, never synthetic production
Cases or invitations. Full local equivalent of CI is required; remote CI need not
be polled for duplicate evidence. Retry tests only for a diagnosed fixture/timing
problem or after a correction. Build networking limits require an explicit recorded
alternative, not a claim that the production image was built when it was not.

An exhaustive run exposed anonymous PostgreSQL volumes retained by test teardown.
The additional infrastructure batch changes only owned-fixture cleanup (`rm -f -v`)
and registers attempted containers before startup. Its regression test covers normal
and failed startup. The disk-exhausted attempt is retained and the complete E2E gate
is repeated after verified disposable-volume cleanup; browser/product code is unchanged.

Rolling back to the pre-refactor image requires reloading open tabs to restore that
image's native module graph. URL resources and session draft formats remain compatible;
no database rollback or user-data restoration is required.
