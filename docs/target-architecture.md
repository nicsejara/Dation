# Target architecture — Foundation stabilization

Designed against `a8ebde9` before runtime changes. Native ES modules and FastAPI
remain. Public HTTP/SQL payloads, storage keys, DOM hooks and CSS cascade remain.

## Frontend boundaries

```text
static/js/
  platform/                 existing platform features, Auth/session, shell
  dispatch/
    workspace.mjs           route/preparation/run orchestration; one state owner
    cases/                  state machine, attributes, map, ownership
    navigation/             URL resource, Case Flow, Decision Navigator, targets
    assignment/             D1 configuration, dashboards, selectors and evidence
    scheduling/             D2 configuration, dashboards, timeline and rules
    runs/                   polling, toolbar/actions, export, status and trace
    upload/                 existing typed Data Pack ingestion components
    dashboard-presentation.mjs  shared D1/D2 disclosure lifecycle
    result-summary.mjs      shared persisted result text, independent of config
    decision-config-ui.mjs  existing shared configuration/context primitives
    shared.mjs              existing recovery/format/chart helpers, not a new API
    lifecycle.mjs           resource disposal / focus
    styles.mjs              stylesheet identity/readiness/retry
```

Retain filenames for feature content where already precise. Rename only ambiguous
navigation/run entry names (`navigation` → `resource`, `case-navigation` →
`case-flow`, `run-polling` → `polling`). Update imports by resolving real source
paths, including lazy imports and browser tests. Do not leave forwarding modules.

Shared D1/D2 UI already exists: `decisionHero`, `decisionCaseCard`, `decisionRail`,
`renderDashboardToolbar`, `bindDashboardActions`. Preserve those boundaries.
Extract the duplicate advanced-analysis storage/disclosure/cleanup behavior into
one small binder. D1 and D2 keep exact domain markup, selectors, charts, narratives,
KPI calculations and section order. Result summary gets its own dependency-light
module. Execution progress and approval trace move out of Case preparation.

## Backend boundaries

```text
app/
  domain/decision_cases.py  pure Case state creation, validation, history projection
  services/decision_case_service.py  persistence and transaction/RPC orchestration
  routes/dispatch.py       current typed transport contract
  platform/               current identity, tenant repository and platform features
  engines/                unchanged deterministic and historical engines
```

The Case service consumes pure domain functions; the domain never imports FastAPI,
httpx, Supabase, config or tenant context. Existing public service methods and API
models stay intact. Tests exercise pure projection directly and the service through
mocked authoritative history and real disposable PostgreSQL/API workflows.

## State and authority

1. URL selects Case → Decision → Run; Run lineage overrides a stale tab selection.
2. `workspace.mjs` owns mutable browser state, generation cancellation and drafts.
3. Applied pre-CSV preparation is a session snapshot. Registration/promotion and
   owner eligibility stay exactly as implemented, including version checks.
4. SQL owns current approval, downstream invalidation, membership/owner authority,
   queue idempotency and atomic attributes + Data Owner Apply.
5. Case state JSON is a projection/cache, never an alternative approval authority.

## Compatibility and non-goals

No schema changes, migrations, dependency additions, new framework, global CSS
rewrite or algorithm modifications. Keep old URL readers, historical engines,
legacy result renderers and persisted aliases. Remove code only when all actual
callers, generated DOM and regression coverage prove it unused.

Static analysis uses the project's real toolchain: Python compile, JS syntax,
import graph/reachability, API schema comparison and domain dependency checks.
There is no configured TypeScript or Python static typechecker; do not present a
syntax check as type inference. Container build + HTTP smoke verifies deployment
packaging. Full existing suites and current golden workflows establish behavior.
