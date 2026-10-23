# Foundation refactor summary

Base: `a8ebde935abaa28b6eb677a2e0e9c63a383dd9d8` (main/production before work).
Baseline tests ran against the unchanged original checkout; implementation and
final validation use the isolated `platform/foundation-implementation` worktree.

## Before

The platform already shared navigation, Case Context, approval and toolbar logic,
but mixed Case/navigation/Run/D1/D2 files in one directory. Case state projection
was mixed with database/HTTP orchestration. D1/D2 duplicated advanced disclosure
lifecycle. Unmounted Case-selector branches and retired final-action CSS remained.
Architecture notes and multiple old tests described superseded sagas.

## After

37 frontend modules are organized into `cases/`, `navigation/`, `runs/`,
`assignment/`, `scheduling/`. Existing platform/upload boundaries remain.
Eight pure Case functions move to `app/domain/decision_cases.py`; Home, Center
and the Case service share them directly. Normalized AST comparison proves the
extracted functions retain the original logic after explicit symbol renames.
Twelve captured projection vectors protect pending/error/current approval,
supersession, stale downstream, history counts and bounded current-approval reads.

The workspace remains the single route/draft/execution coordinator. No speculative
state-store rewrite or new repository abstraction was introduced. No product copy,
navigation rules, DOM hooks, algorithms, result schemas, API payloads or session
storage formats change.

## Renames

* `navigation.mjs` → `navigation/resource.mjs`.
* `case-navigation.mjs` → `navigation/case-flow.mjs`.
* `run-polling.mjs` → `runs/polling.mjs`.
* Case/Assignment/Scheduling modules retain precise filenames in domain folders.
* Active preparation mounting is `mountCasePreparation`.
* Pure state functions use `create_case_state`, `validate_case_state`,
  `project_case_history`, `run_history_item`, `utc_now`.

Public JSON/SQL identifiers, node keys, `DC-…` display IDs and historical fields
are preserved. Static HTTP redirects preserve old lazy module URLs. Case context
and config UI keep compatibility named exports that point to the same canonical
implementations; no duplicate forwarding modules are added.

## Components consolidated

* D1/D2 advanced-analysis expanded state, storage restore, lazy callback, target
  focus/scroll and cleanup → `dashboard-presentation.mjs`.
* Persisted-value result text → `result-summary.mjs`, independent of config.
* Actual Run execution status → `runs/execution-progress.mjs`.
* Actual approval-actor trace → `runs/approval-trace.mjs`.

Existing shared Hero, Case Context, Decision Navigator, action bar, review dialog,
toolbar, approval/continuation, chart palette and UI tokens remain canonical.
Assignment charts/tables and Scheduling calendar/SLA content stay domain-specific.

## Legacy removed

Confirmed unused `case-switcher.mjs`, its unreachable mounting variants, Map
callback/query for the absent dropdown, and retired D1/D2 final-action CSS.
Historical engines, renderer, APIs, URL readers, SQL aliases and operational gates
are retained because they still serve real compatibility needs.

Exhaustive validation also exposed a preexisting disposable-PostgreSQL volume leak.
Fixture and CI teardown now release their own anonymous volumes, including failed
startup. A real regression test verifies containers, networks, processes and volumes
are cleaned in both paths. Thirty-five verified synthetic volumes from this task
were removed; unrelated or active resources were preserved.

## Persistence

No migration, table/column/RPC rename, data reset or production business-data write.
All 53 protected engine/SQL files retain their baseline SHA-256. All 91 OpenAPI
paths and the complete schema remain identical. Versioned atomic attributes/Owner
Apply, Run admission/idempotency, approval/invalidation and tenant authority remain
in their existing transactions.

## Tests

Evidence lives under `/workspace/dation-audit/foundation/`. Full failure identities,
test locations and exception types were compared against the unchanged baseline.

| Gate | Unchanged baseline | Current verified result |
|---|---|---|
| Python unit/contracts | 378; 6 failures, 1 error | 383 pass |
| Node | 124; 2 failures | 124 pass |
| Current Saga UI / Apply-before-CSV | included in full browser baseline | 14 pass |
| New shared lifecycle/native module compatibility UI | new characterization | 3 pass |
| SQL integration | 46 pass | 46 pass |
| Full browser | 210; 28 failures, 65 errors; 63 affected methods | 213; 27 failures, 64 errors; 61 affected methods; no new failure identities/sites/types |
| Full API/worker/PostgreSQL E2E | 81; 26 failures, 1 error | 82; same 26 failures and 1 error at the same test locations; no skips |
| Static/contract checks | compile/syntax/dependencies pass | 101 JS modules parse; compile/pip check pass; OpenAPI + engine/SQL hashes identical |
| Production container | build + 6 HTTP checks/non-root pass with hash-locked offline wheels | build/smoke pass; 243 packaged application files exactly match source; all static files and 37 old module URLs verified |
| Dependency audit | unchanged lockfiles | backend/browser pip-audit: no known vulnerabilities |

The current golden workflow passes: six actual Runs, approval and downstream
invalidation, immutable Data Pack fork, nine surfaces and 45 responsive probes across
five viewport widths. The current 17 UI scenarios and all Saga 3/5 API scenarios pass.
The two browser baseline failures no longer reproduced are recorded as such, not
presented as intentionally redesigned product behavior.

One final E2E attempt exhausted disk space because of the fixture volume leak.
That attempt remains under `final/disk-exhaustion/`. After fixing and verifying
owned-resource cleanup, the complete E2E suite was rerun to the result above.
The domain dependency guard was rechecked after allowing legitimate standard-library
imports while continuing to reject infrastructure dependencies.

Commands run from `backend/`: `python -m unittest discover -s tests -v`,
`node --test tests/test_*.js tests/test_*.mjs`,
`.browser-venv/bin/python -m unittest discover -s tests/browser -v`,
`python tests/e2e/run_suite.py`, SQL integration with an owned PostgreSQL 17
container. Static gates mirror CI: `compileall`, all native JS syntax, import
reachability and complete OpenAPI comparison. No configured static typechecker or
standalone linter exists; these checks are not claimed as type inference.

The normal Docker build cannot resolve PyPI in this environment. The verified
alternative downloads the exact hash-locked wheels and changes only the local QA
installation source to `--no-index --find-links`; production Dockerfile/dependencies
remain unchanged. The image includes the actual API, app assets and sample packs.
The audit CLI emits generic `--no-deps` guidance; the repository already fully pins
and hashes its dependency lockfiles. Python/Node code and OpenAPI remain compatible.

## Release and rollback

Release uses the existing GitHub → Cloud Build → API/worker Cloud Run pipeline.
The merge must have the exact tested tree; production checks record source SHA,
build steps, both revisions/traffic, exact static content, legacy module redirects,
OpenAPI and protected-route behavior in `release/production-checks.json` in the
execution artifacts. No synthetic production account, Case, Run or personal session
is used. Rollback redeploys the previous source/image and reloads the native module
graph; unchanged database/session contracts require no data rollback.

## Known debt

Global CI was already red: older browser/API suites expect retired independent
Steward/approver roles, selectors, approval boxes and navigation. Those failures
remain visible. Baseline identities are compared with the full final runs so new
failures cannot be hidden behind the existing count. Obsolete unit/Node assertions
touching the extracted boundaries were updated to current contracts, including
authoritative history instead of manufacturing approval from cached Case state.

Large active historical renderers, the central workspace orchestrator and layered
CSS remain intentionally. Splitting by size or rewriting specificity without a
separate compatibility contract would risk functional drift. Existing tokens and
button/card patterns already cover the shared design system; no new scale is needed.

## Next steps

Future UX/UI changes should start from the canonical component map and keep their
own acceptance criteria. A Data Pack upgrade belongs at typed validators and the
immutable replacement contract. Engine upgrades require versioned schema/handoff
and invariant tests. BI/dashboard upgrades should consume persisted evidence and
leave calculations in the engines. Reconcile the remaining historical test fixtures
as a dedicated compatibility task, without restoring retired product behavior.
