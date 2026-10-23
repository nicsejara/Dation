# Dation architecture

Dation serves native HTML/CSS/ES modules from FastAPI, backed by Supabase Auth,
tenant-scoped Postgres/Storage and a durable Cloud Run worker. The deterministic
engines produce immutable results; dashboards and AI explain that evidence.

## Find a responsibility

Paths are relative to `backend/`.

| Question | Canonical location |
|---|---|
| Where is Decision Case state? | `app/domain/decision_cases.py`; browser `app/static/js/dispatch/cases/decision-case.mjs` |
| Where is Case persistence? | `app/services/decision_case_service.py` |
| Where is Data Pack ingestion? | `app/static/js/dispatch/upload/`, `app/services/dispatch_service.py`, `app/validators/contracts.py` |
| Where are Case Attributes / Data Owner? | `dispatch/cases/case-identity.mjs`, `cases/workflow-context.mjs`, atomic attributes API/RPC |
| Where is Decision Owner? | `dispatch/cases/workflow-responsibility.mjs`, Map mounting in `cases/workflow-context.mjs`; SQL eligibility/authority |
| Where is a Run admitted/executed? | `app/routes/dispatch.py` → `app/services/dispatch_job_service.py` → `worker.py` |
| Where is a Run approved? | `POST /api/runs/{run_id}/approve` → Case service → `approve_decision_run_version` |
| Where is downstream invalidation? | SQL `decision_runs_reopen` / `dation_private.invalidate_run_lineage` |
| Where is Case Context? | `dispatch/decision-config-ui.mjs::decisionCaseCard`; global `workflow-context.css` |
| Where is dashboard shell behavior? | `dispatch/dashboard-presentation.mjs`, `dispatch/runs/dashboard-{toolbar,actions}.mjs`; feature shell markup stays in D1/D2 |
| Where is Assignment? | `dispatch/assignment/`, `app/engines/assignment/`, `app/models/assignment_config.py` |
| Where is Scheduling? | `dispatch/scheduling/`, `app/engines/scheduling/`, `app/models/scheduling_config.py` |

## Frontend

```text
app/templates/app.html
  → platform/session.js (verified identity, isolated tab caches, authenticated fetch)
  → platform/boot.mjs (classic prerequisites, native module boot)
  → dispatch/workspace.mjs + platform/shell.mjs

static/js/platform/           Home, Center, Data Hub, Team, settings, onboarding
static/js/dispatch/
  cases/                     Case state, attributes, Map, ownership
  navigation/                URL resource, Case Flow, Decision Navigator, targets
  assignment/                D1 configuration/content/selectors/evidence
  scheduling/                D2 configuration/content/calendar/rules
  runs/                      polling, toolbar, approval actions, trace, export/status
  upload/                    typed Orders/Fleet ingestion
  workspace.mjs              one route/preparation/execution coordinator
  decision-config-ui.mjs      shared config/context/review primitives
  dashboard-presentation.mjs  shared advanced-analysis disclosure lifecycle
  result-summary.mjs         escaped persisted-value presentation
  lifecycle.mjs              scopes, abort/cleanup, focus
  styles.mjs                 stylesheet readiness and retry
  shared.mjs                 current API errors/recovery/format/charts
```

No bundler, npm package build, React or TypeScript toolchain is introduced. Classic
UI and historical renderers remain because old result schemas are supported.
Styles retain their current order, selectors and tokens. Feature files own business
interpretation and charts; shared components own actual repeated behavior.

The URL identifies Case → Decision → Run. Persisted Run lineage overrides cached
selection. The workspace owns route generations, AbortSignals and session drafts;
late responses cannot replace another route. Applied preparation before valid CSV
is a session snapshot, promoted through the existing atomic API once inputs exist.

Moved native modules have explicit redirects in
`app/static/contracts/foundation-module-redirects.json`. FastAPI resolves old lazy
URLs directly to canonical source with revalidation. Compatibility named exports
in Case context/config UI delegate to the same implementation, preserving imports
from already-open tabs without duplicate components.

## Backend and authority

```text
browser → authenticated route/model → service/platform operation
        → tenant repository or checked platform RPC
        → Supabase database / private Storage / durable job queue
        → worker → deterministic engine → persisted result
```

`app/domain/decision_cases.py` is pure creation/validation/history projection. It
has no HTTP, tenant context or database dependency. Home, Center and the Case service
reuse this projection. Services own persistence and orchestration. Transport models
and the 91-path OpenAPI contract remain compatible.

`platform/context.py` binds verified user/workspace authority. `platform/repository.py`
scopes REST/Storage operations and checked RPC allowlists. `platform/identity.py`
handles platform RPCs and SQL error translation. A browser-provided owner/workspace
ID is not authority. SQL revalidates membership, eligibility, archive state, object
ownership and optimistic versions in the transaction.

`dispatch_job_service.py` owns admission/idempotency, job leases and reconciliation.
`worker.py` is deployed independently from the API. Admission and approval share
locks; new Runs retire current approvals and invalidate downstream lineage without
deleting results or historical actors. Case state JSON is an eventually consistent
projection, never an independent approval source.

Assignment stays non-temporal. Scheduling consumes the current approved Assignment
handoff, preserving trips, loads and vehicles. Historical Dispatch/Logistics engines
remain available for old Runs. AI does not optimize, recalculate or select the plan.

## Persistence and compatibility

Case → immutable Orders/Fleet; Run → Case/node/upstream Run; approval events → Run;
assignment → Case/node/member; durable job → Run. Private responsibility aliases
and older engine/JSON fields remain for upgrade/history compatibility. The partial
approval index, locks, tenant constraints and RLS remain unchanged. Foundation
stabilization adds no SQL migration and performs no business-data rewrite.

## Verification and related documents

The configured static gates are Python compilation, JS syntax and import/contract
checks. There is no configured TypeScript/Python static typechecker or standalone
linter; do not describe compilation as type inference. Docker is the production
build. Hash-locked offline wheels can validate the same container when local Docker
cannot resolve PyPI; the production Dockerfile is unchanged.

See [domain](domain-model.md), [navigation](navigation.md),
[components](component-map.md), [Runs](decision-runs.md),
[naming](naming-conventions.md), [audit](foundation-audit.md),
[migration/rollback](foundation-migration-plan.md) and
[verification/debt](foundation-refactor-summary.md).
The former incremental architecture notes are preserved in
[the historical archive](archive/architecture-dispatch-evolution.md); they describe
earlier phases and do not override current code or these canonical contracts.
