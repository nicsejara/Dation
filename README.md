# Dation — Decision Intelligence

Dation is a **Decision Intelligence** platform built around
**Decision Data Assets (DDA)**: repeatable and auditable decision processes
that combine structured data, deterministic analytics, configurable priorities
and human validation.

Start with the [master development baseline](docs/MASTER_DEVELOPMENT_BASELINE.md).
The current `main` is the development source of truth. The
[repository hygiene report](docs/FINAL_REPOSITORY_HYGIENE_REPORT.md) records branch
classification, retained unique work and environment cleanup actions.

## Access and workspaces

The platform uses Supabase Auth (email/password, confirmation and recovery), workspace memberships and Bearer-protected business APIs. Shared HTTP Basic credentials are retired. Sign in at `/login`; new users create a workspace after confirmation. Existing data belongs only to the explicitly authorized legacy administrator. See [Auth and migration](docs/platform-mvp/10-phase2-auth-tenancy.md) and [platform navigation](docs/platform-mvp/11-phase3-shell-navigation.md).

The backend keeps refresh tokens HttpOnly, validates asymmetric JWTs and scopes service-key queries/RPCs/Storage by workspace. Browser code never receives the service key. Production migrations require the controlled backup/drain/deploy/admissions sequence; do not run them during normal setup.

## Current Ultimate MVP

```text
DATA → ENGINE → RESULT → EVIDENCE → IA → HUMAN APPROVAL
```

Logistics Models and their versions define the operating context. A Decision Case
pins its model, progressive Data Pack version and policy. Published inputs feed
deterministic Runs and immutable Result Packages:

| Decision | Node ID | Engine / version | Result schema |
|---|---|---|---|
| D1 · Transport Plan | `logistics_assignment` | `transport_plan` / `2.0.0` | `transport_plan_v1` / 1 |
| D2 · Day Scheduling | `logistics_scheduling` | `day_scheduling` / `2.0.0` | `day_scheduling_v1` / 1 |

D2 consumes the approved D1 result and preserves its trips, allocations and
resources. The frontend presents persisted results; the Approval Copilot explains
published evidence through `decision_context_v1`. Neither recalculates decisions.
Runtime admission follows the existing SQL release/workspace/pilot gates; a known
schema or engine identity alone does not establish availability.

`assignment_v1`, `scheduling_v1`, `dispatch_v2`, Orders/Fleet adapters and their
readers remain compatibility paths. The earlier three-step chain below describes
that historical implementation, not an additional active Ultimate decision.

### Historical Orders/Fleet chain

The first active domain is **DDA Logística**. Its data layer is now organized as a progressive **Logistics Data Pack**:

```text
Orders V3 + Fleet V3
        ↓
technical validation
        ↓
Decision Readiness
        ↓
Decision Case + Decision Map
        ↓
01 Assignment       AVAILABLE → RUNNING → REVIEW → APPROVED
02 Scheduling       LOCKED → AVAILABLE after Assignment approval
03 Final Assignment LOCKED → depends on Scheduling approval
```

The templates are deliberately complete, but users only need the core columns required for the first decision. Optional fields can be added later to the same two datasets to unlock scheduling, SLA analysis, cost/CO₂ objectives and physical-vehicle assignment.

Fleet V3 contains **one row per real truck**. There is no user-facing pool concept.

Phase 4 activates the second engine in the chain. Assignment 1.0.0 still decides **what vehicle carries what load** without dates. Once a human approves that result, Scheduling 1.0.0 consumes the immutable `scheduling_input_v1` handoff and decides **when each approved trip can run**, respecting ready dates, vehicle availability and non-overlapping round-trip occupancy. Scheduling emits `final_assignment_input_v1` for Decision 03. Dispatch 2.2 remains readable for historical runs.

## Compatibility versions

- Workspace / API: **1.0.0**
- Legacy Assignment engine: **1.0.0** (`assignment_v1`, non-temporal)
- Legacy Scheduling engine: **1.0.0** (`scheduling_v1`, fixed Assignment + temporal sequencing)
- Historical Dispatch engine: **2.2.0** (`dispatch_v2`, temporal) retained for prior runs; engine **0.2.0** also retained
- Frontend: HTML + CSS + vanilla JavaScript
- Runtime: Google Cloud Run
- Data / storage: Supabase
- AI Interpreter: Groq-backed, with versioned knowledge in GitHub

## Repository

```text
Dation/
├── backend/
│   ├── app/
│   │   ├── domain/        pure Case state and authoritative history projection
│   │   ├── engines/       deterministic DDA engines
│   │   ├── knowledge/     interpreter knowledge base
│   │   ├── models/        typed decision configuration
│   │   ├── services/      data, runs, profiles and AI
│   │   ├── static/        workspace CSS + JavaScript
│   │   └── templates/     application shell
│   └── tests/             engine compatibility tests
├── frontend/              commercial landing assets
├── sample_data/           synthetic logistics inputs
├── docs/                  architecture documentation
├── infra/                 deployment notes
├── index.html             existing commercial landing
└── Logo.png
```

## Design principle

The deterministic engine is the source of truth.

The LLM does **not** optimize, recalculate or override the decision.
It explains the DecisionResult produced by the engine using a versioned
business knowledge base.

## Security

Real credentials and `.env` files must never be committed.
Runtime secrets remain in Google Secret Manager / Cloud Run.


## Architecture and verification

Current documentation: [master baseline](docs/MASTER_DEVELOPMENT_BASELINE.md),
[architecture](docs/architecture.md),
[domain model](docs/domain-model.md), [component map](docs/component-map.md),
[navigation](docs/navigation.md) and [Decision Runs](docs/decision-runs.md).
[Foundation stabilization](docs/foundation-refactor-summary.md) records the baseline,
validation commands, compatibility boundaries and intentionally retained debt at
that historical foundation milestone. Execution reports under
`docs/execution/ultimate/t0` through `t12` are historical evidence; their original
PASS/HOLD statements describe their recorded commits and are preserved unchanged.

Normal production delivery is `main → Cloud Build → Artifact Registry → Cloud Run
worker → Cloud Run API`. GitHub Actions runs CI separately. See
[deployment](backend/DEPLOYMENT.md). Normal setup does not replay migrations or
use manual GCP OAuth tokens.

For ordinary changes, run tests for the affected component. The following full
regression commands are available from `backend/` when their scope is justified:

```sh
python -m unittest discover -s tests -v
node --test tests/test_*.js tests/test_*.mjs
.browser-venv/bin/python -m unittest discover -s tests/browser -v
python tests/e2e/run_suite.py
```

Browser tests use synthetic APIs; E2E uses owned disposable PostgreSQL 17,
PostgREST, Storage/Auth fixtures, actual API/worker and engines. Never target those
fixtures at production. SQL integration also requires an owned PostgreSQL container
via `DATION_SQL_TEST_CONTAINER`. Production packaging uses `docker build .`.
See [deployment](backend/DEPLOYMENT.md) for operational prerequisites; normal setup
must not replay already-applied production migrations.
