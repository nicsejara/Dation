# Foundation audit — 2026-10-22

## Executive Summary

Baseline: `main`, `a8ebde935abaa28b6eb677a2e0e9c63a383dd9d8`. Work proceeds on
`platform/foundation-stabilization`. This is an internal refactor, with no product,
engine, API, database or authentication redesign. The previous Apply-before-CSV
change is part of the protected baseline.

The product already has substantial shared infrastructure. Preserve it. The main
problems are feature files mixed in one frontend directory, presentation lifecycle
duplicated between D1/D2, unused old Case-selector branches, and documentation/tests
that describe earlier sagas. Do not mistake historical engine support or SQL
compatibility fields for dead code.

Evidence: `/workspace/dation-audit/foundation/baseline/` contains the source inventory,
OpenAPI, route list and unmodified-source test logs. Final results and reproducible
commands are recorded in [the summary](foundation-refactor-summary.md).

## Current Architecture

| Area | Actual entry/boundary | Responsibilities |
|---|---|---|
| HTTP application | `backend/main.py` | lifespan, telemetry, static cache policy, SPA/auth redirects, historical dataset/run/AI APIs |
| Platform API | `app/platform/*_routes.py` | Auth, Home, Data Hub, Center, Team, settings, activity, onboarding |
| Logistics API | `app/routes/dispatch.py` | CSV contracts/validation/preflight, Cases, admission, approval, exports |
| Tenant repository | `app/platform/repository.py` | authoritative workspace scope, RPC allowlists, Storage ownership |
| Platform RPC boundary | `app/platform/identity.py` | authenticated actor/workspace arguments and SQL error translation |
| Case service | `app/services/decision_case_service.py` | immutable input identity, state projection, durable history, reconciliation, approval validation |
| Run queue/worker | `dispatch_job_service.py`, `backend/worker.py` | idempotent admission, leases, retries, engine invocation, reconciliation |
| Engines | `app/engines/{assignment,scheduling,dispatch,logistics}` | deterministic domain algorithms; historical formats remain readable |
| Browser boot | template → `platform/session.js` → `platform/boot.mjs` | identity isolation, classic script prerequisites, workspace + platform shell |
| Logistics browser | `static/js/dispatch/workspace.mjs` | route generation, cancellation, preparation, execution and hydration orchestration |
| Platform browser | `static/js/platform/` | feature-local views/resources; shared `foundation.mjs`, components and shell |
| UI primitives | `dispatch/{shared,lifecycle,styles,decision-ui,decision-config-ui}.mjs` | escaping, recovery, charts, scope cleanup, stylesheet readiness, shared UI |
| CSS | tokens → design-system → shell/feature styles | current cascade and selector hooks are functional contracts |
| Persistence | baseline + ordered `supabase/migrations` | tenant/RLS boundary, Cases, Runs, append-only approval history, owner gates, queue and evidence |

No React, hooks framework, TypeScript compiler, npm build or configured Python
linter/typechecker exists. Native ES modules are served directly. Existing static
gates are Python compilation, JS syntax, frontend import reachability and contract
tests. Docker is the production build, not a frontend bundle.

### Baseline protection

Python: 378 tests, 6 failures and 1 error before edits. Node: 124 tests, 122 pass,
2 fail before edits. Compilation, all JS syntax, `pip check`, and SQL integration
pass. Browser/E2E results are retained independently, including preexisting failures.
An initial Docker build could not create its default configuration directory;
using a writable `DOCKER_CONFIG` solved that. The subsequent build exposed Docker
network DNS failure for PyPI. This is an environment limitation, not a source error.

The obsolete Python assertions expect old map/case markup or copy. The service
test tries to approve by updating cached state rather than mocking authoritative
Run history. Node tests expect the former independent approver and `data_preparation`
gate instead of canonical `data_owner`. Update tests to current behavior, preserving
or strengthening their assertions; do not restore obsolete product behavior.

## Domain Naming Issues

| Current | Target / treatment |
|---|---|
| `dispatch/` containing Case, navigation, both decisions and Runs | preserve public static root; organize domain subdirectories |
| `decision-case.mjs` | `cases/decision-case.mjs`, canonical state machine; no schema rename |
| `navigation.mjs` | `navigation/resource.mjs`, URL resource parsing/serialization |
| `case-navigation.mjs` | `navigation/case-flow.mjs`, vertical Case Flow |
| `run-polling.mjs` | `runs/polling.mjs`, concrete Decision Run lifecycle |
| `mountWorkflowContext` with several unreachable variants | Case preparation ownership; retain actual Map owner rendering separately |
| pure `_base_state`, `_validate_state`, `_state_with_history` mixed with I/O | explicit Case state module with creation/validation/history projection names |
| `data_steward`, `approver_user_id`, `approved_by` in SQL/historical payloads | KEEP FOR COMPATIBILITY; canonical operational names remain Data Owner / Decision Owner |
| `execution` in queue/solver stages | legitimate execution activity; do not mechanically rename every occurrence |
| `DC-…` displayed identifier | intentional human ID format; preserve |

`approved_by_user_id` is the actual historical actor; it is not the current
Decision Owner. Assigned owner, Run creator and approval actor must stay distinct.

## Component Duplication

| Equivalent real component | Location before refactor | Use / inputs | Decision |
|---|---|---|---|
| Workflow Hero | `decision-config-ui::decisionHero` | Data, Map, Config D1/D2; title, metadata, panel items | keep shared |
| Context navigation | `platform/dda-navigation.mjs` | current DDA/Case/Decision resource | keep shared |
| Case Flow | `case-navigation::renderCaseFlow` | resource + prepared/persisted Case | move to navigation feature |
| Decision Navigator | `decision-nav::decisionRail` | Case, workflow, active node, view | move; keep one implementation |
| Case Context | `decision-config-ui::decisionCaseCard` | Map and both configs; metadata, Data Owner, files, hooks | preserve native disclosure |
| Case Attributes | `case-identity::mountCaseIdentity` | preparation state, save/persist callbacks | Case-local; preserve draft Apply |
| Data Pack readiness | `upload/index::finalState`, action bar | Orders/Fleet/attributes/Owner | preserve four checks |
| Decision cards/progress | `decision-map` | node state, readiness, history callbacks | Case-local |
| Result summary | `decision-config-ui::decisionResultSummary` | D1/D2 persisted value segments, support text | extract from config dependencies |
| Run toolbar/approval | `dashboard-toolbar`, `dashboard-actions` | run + Case actions/continuation | already shared; move to runs |
| Advanced analysis disclosure | D1 and D2 `*-dashboard-shell` bind functions | run-specific storage, lazy chart draw, scroll target | consolidate lifecycle, retain domain markup |
| Execution status | bottom of `workflow-context` | real backend stage | isolate under runs |
| Approval trace | `workflow-context::decorateDashboardHero` | concrete run, bounded actor lookup | isolate under runs |
| Buttons/cards/status | `dation-design-system.css`, `platform/components`, `decision-ui` | tokens, existing hooks | retain; no new component framework |
| Error/loading | `shared::errorBox`, run polling and recovery | error kind/status, retry, AbortSignal | already shared; retain semantics |

D1 charts/tables/packing interpretation and D2 calendar/timeline/SLA remain
feature-specific. Their shell markup, classes, labels and section order differ
intentionally. Share their repeated lifecycle, not a configurable mega-template.

## Routing / State Issues

* URL resource is `{view, caseId, nodeId, runId}`. `resourceUrl` preserves unrelated
  query parameters, accepts old `view`, `dda`, `inicio`, history/library aliases,
  and writes canonical paths. Keep all read compatibility.
* Map intentionally omits `node_id` in its canonical URL; transient node context
  still focuses the Decision Owner editor. Config/Dashboard retain node context.
* Persisted Run lineage wins over selected tab/cache. Preserve `runContext`.
* `workspace.mjs` owns route generations, aborts, shared polling and draft storage.
  Splitting this orchestration solely by size would increase race risk. Keep its
  control flow; improve imports/domain boundaries first.
* Session keys `dation.dispatch.workspace.v5` and `dation.dispatch.drafts.v1` are
  compatibility contracts. Applied preparation is a session snapshot until both
  CSVs are valid; it is not an empty persisted Case.
* The old recent-Case dropdown has no live mounting caller: the only actual
  `mountWorkflowContext` caller supplies `showCase:false`. Its Map callback queries
  a nonexistent dropdown. Remove only after reference checks and browser coverage.

## Backend / API Issues

| Operation | Browser → API → service/RPC |
|---|---|
| Create Case | workspace → `POST /api/decision-cases` → `ensure_case` → tenant `decision_cases` |
| Apply attributes + Data Owner | session snapshot before valid CSV, otherwise `PUT /api/platform/decisions/{id}/attributes` → `platform_apply_case_attributes` (atomic metadata + Owner CAS) |
| Change Data Pack | `PUT /api/platform/decisions/{id}/data-pack` → validate typed inputs → `platform_replace_case_data_pack` (immutable fork) |
| Owner assignment | responsibility selector → `PUT …/responsibilities/{stage}` → `platform_workflow_responsibilities` |
| Configuration gates | `GET …/workflow-readiness?node_id=…` → typed preflight + `platform_validate_decision_stage` |
| Create Run | config → `POST /api/runs?run_id=…` → queue enqueue → `platform_rpc` → admission trigger |
| Read result/history | `GET /api/runs/{id}`, Case/run history endpoints → bounded reads + authoritative SQL summaries |
| Approve Run | `POST /api/runs/{id}/approve` → validation + `approve_decision_run_version` |
| Downstream invalidation | new admission → `decision_runs_reopen` → `invalidate_run_lineage`; history retained |
| Archive | Center → versioned Case PATCH → `platform_update_case` |
| Export | shared run export → authenticated CSV/JSON endpoints; historical formats retained |

Pure state creation/validation/history projection is entangled with HTTP in the
737-line Case service. Extracting that pure boundary improves review and coverage
without moving tenant authority or introducing a new repository abstraction.
`api.js` is the historical UI client, `shared::api` is the current JSON/error client,
and `session.js` wraps authenticated fetch. They have different error contracts;
merging them during a behavior-preserving refactor is unjustified.

## Persistence

Core relationships: workspace → datasets / decision_cases / decision_runs;
Case → immutable Orders/Fleet; Run → Case + node + optional upstream Run;
approval events → concrete Run; assignments → Case/node/member; jobs → Run.
Private workflow assignments and member responsibilities retain historical aliases.
Storage references are dataset bucket/path, checked through the tenant repository.
The partial unique index allows only one current approval per Case/node. Admission
and approval share locks; queue idempotent replay must not invalidate twice.

Read the SQL baseline and ordered migrations, especially `20261022020000`,
`20261022030000`, `20261022040000`. Fresh PostgreSQL tests reconstruct this schema.
**No database migration is required or justified by this refactor.** Do not replay
applied migrations or rename fields for aesthetics.

## Legacy / Dead Code

| Candidate | Classification | Evidence / handling |
|---|---|---|
| `case-switcher.mjs`, its CSS and never-mounted workflow branch | SAFE TO DELETE | one caller explicitly disables it; current golden checks absence |
| Map `onSelectCase` callback for that absent dropdown | SAFE TO DELETE | renderer no longer offers this action |
| `.assignment-final-actions`, `.scheduling-final-actions` rules | SAFE TO DELETE | no runtime markup since Saga 4 |
| Old Map context/selector CSS | REVIEW | remove only selector groups with no markup/generator references; preserve shared file cards |
| classic `app.js`, `ui.js`, `dashboard-stage.js`, interpreter | KEEP FOR COMPATIBILITY | historical runs, library and old schemas still supported |
| historical Dispatch/Logistics engines and API | KEEP FOR COMPATIBILITY | persisted results and tests depend on them |
| SQL approver/Steward aliases and workflow release gates | KEEP FOR COMPATIBILITY | upgrade/history compatibility and operational control |

## UI System Issues

Colors, radii, spacing, typography and status palette already live in `tokens.css`.
`dation-design-system.css` centralizes actions/cards; `workflow-context.css`
centralizes current Case Context, execution and result hierarchy. Many old sheets
contain layered overrides. A global CSS rewrite could alter specificity and is
out of scope. Remove proven dead selectors, preserve stylesheet order and computed
styles, and use existing tokens when consolidating exact repeated values. No new
palette, spacing scale or chart theme is needed.

## Risks / Priority

* **P0:** tenant isolation, current approval vs cached state, rerun invalidation,
  atomic Apply/CAS, asynchronous navigation cancellation. Protect with real SQL/API
  and browser journeys; do not change authority or transaction boundaries.
* **P1:** obsolete regression expectations hide current behavior; native import
  moves can break lazy modules, template references and deployed URLs. Resolve all
  consumers and run reachability/syntax + full critical journeys.
* **P1:** D1/D2 duplicated presentation lifecycle risks divergent cleanup and lazy
  rendering. Consolidate with tests for both storage namespaces and disposal.
* **P2:** frontend feature boundaries, backend pure Case state, semantic naming,
  obsolete architecture documentation.
* **P3:** historical monoliths and broad CSS cascade cleanup. Keep where active;
  future work requires historical-renderer parity, not deletion by age/size.

## Functional regression checklist

- [ ] Home, Center, DDA Overview and direct authenticated routes
- [ ] New preparation; Apply before CSV; edit/revert; reload; four readiness checks
- [ ] Both CSVs → one persisted Case; atomic attributes/Owner; Map and Owner edits
- [ ] D1 configuration → Run → result → approval → D2 configuration
- [ ] D2 Run → result → approval → Case complete
- [ ] New D1 Run retires approval and invalidates D2, with history/evidence intact
- [ ] Same Data Pack retains Case; changed Data Pack creates another Case
- [ ] Decision Navigator, Case Flow, Config ↔ Dashboard, browser back/forward
- [ ] Error/retry/loading, archived Case, viewer/admin/operator/tenant boundaries
- [ ] Heroes/disclosures/actions, exports, AI fallback, responsive/reduced motion

Completion evidence is linked from `foundation-refactor-summary.md` rather than
rewriting this baseline as if preexisting failures had never happened.
