# Saga 01 — Initial Planning Workflow

Status: **IMPLEMENTATION COMPLETE — NOT DEPLOYED**.

Integration and current required-check status are tracked in
[PR #103](https://github.com/nicsejara/Dation/pull/103).
GCP Billing for `dation-510100` is intentionally disabled; production is not
updated or validated by this report.

Base: `nicsejara/Dation`, `main` at
`3e8712962ba7b444f47b44d5afa9887f4c2e4a10`.
Work branch: `feat/saga01-initial-planning-workflow`.
The pending repository hygiene PR and local hardening WIP were not imported.

## 1. Scope implemented

```text
DDA Logistics → Comenzar
→ 01 Logistics Model → 02 Data Contract → 03 Decision Case
→ Crear Decision Case → Decision Graph
→ Data Pack / readiness → configuration → Run → result/evidence → approval
→ D2 from the approved D1
```

The initial page has no file upload or operational-data reuse control. It has
one final primary action. A first-time workspace enters Model creation directly;
a recurrent workspace can select a published Model/version or create another.
The Data Contract is derived by the backend and includes canonical fields,
types, conditional requirements, validation rules and existing CSV templates.
Case identity, horizon, operating mode, goal, guardrails, preferences and owners
reuse their current controls. A read-only summary precedes creation.

## 2. Files/components changed

| Area | Files / responsibility |
|---|---|
| Frontend Model controls | `models/model-fields.mjs`: extracted existing fields, defaults and validation; `models/index.mjs`: uses the same component |
| Initial setup | `models/planning-model.mjs`: selection/creation, contract preview and retry orchestration; `cases/ultimate-case-setup.mjs`: composes Model/Contract/Case and summary |
| Landing/navigation | `models/entry.mjs`, `dispatch/workspace.mjs`, `app/templates/app.html`: one Comenzar action and context-first entry; obsolete technical landing card removed |
| Graph/data | `cases/ultimate-decision-map.mjs`: D1 input/config/status presentation and entry actions; `upload/ultimate-case-data.mjs`: current navigation/readiness copy |
| Layout | `app/static/css/ultimate-foundation.css`: scoped layout using existing tokens and controls |
| Backend | `app/models/ultimate_foundation.py`, `app/platform/ultimate_routes.py`, `app/services/logistics_model_service.py`: typed, read-only contract/template preview |
| Tests | `tests/test_saga01_planning.py`, `tests/browser/test_saga01_planning.py`; existing setup browser test updated for the final action label and automatically selected version |

Frontend module paths in the table are relative to
`backend/app/static/js/dispatch/`; backend/test paths are relative to `backend/`.
No schema migration, dependency, engine, result contract or runtime gate changed.

## 3. Reused components

The Model library/editor and initial page share `mountModelFields`. The existing
form/draft/error/CAS controls, horizon presets and Case policy/Owner controls are
retained. Contract preview and templates reuse `compile_contract` and
`template_csv`, the same functions used by Case ingestion. The existing dropcards,
validation drawer, compatible-input selector, upload journal, Pack publication
and history remain the single Data Pack implementation.

## 4. Contract mapping

| Requested concept | Current canonical implementation |
|---|---|
| Logistics Model | `LogisticsModelConfigurationV1`; immutable published versions through existing foundation RPCs |
| Modality/resources | `operating_role`, `transport_pattern=DIRECT`, `allowed_sources=OWN/EXTERNAL` |
| Units/capacity | `active_dimensions`, `primary_dimension`: pallets, weight_kg, volume_m3, units |
| Load/compatibility rules | `split_permitted`, `homogeneous_loads_declared`; explicit compatibility groups remain input data |
| Cost structure | `currency_policy`, `own_cost_model`, `external_cost_models`, `per_km_billing_bases`; actual rates remain operational inputs |
| Data Contract | Derived `transport_demand_v1` / `transport_resources_v1` descriptors; no new schema table or user-authored arbitrary schema |
| Decision Case | Existing `UltimateCaseCreate`: name/description, published Model version, dates, horizon_type, operating_mode, case_policy, Owner |
| Scope/instance rules | Existing horizon, mode, goal, guardrails and preferences; no new scope semantics |
| Data Pack | Existing Case Pack, immutable versions and canonical entries `transport_demand` / `transport_resources` |

Availability, distance and due-date fields come from the canonical input contracts.
No unsupported maximum-speed/distance Model setting, payment terms, resource
type or cargo/product field was invented. Stable structural options remain in
the Model; concrete tariffs, resources and operational dates remain inputs;
planning dates and objectives remain Case policy/context.

## 5. Persistence and failure behavior

For a new Model, the final action validates the whole form, saves the Model,
publishes its version through the existing APIs and creates a Case referencing
that version. Published Model selection performs no Model write.

The two new read-only endpoints are:

- `POST /api/platform/logistics-models/contract-preview`.
- `POST /api/platform/logistics-models/contract-preview/templates/{entity}`.

The request accepts either typed configuration or a Model/version pair. Published
versions are retrieved through the existing tenant-checked Model service; missing,
foreign or archived versions fail closed. A draft preview does not expose a fake
published version ID or ingestion contract hash. Preview does not persist anything.
The actual uploader continues to obtain its contract from the persisted Case.

Model, version and Case creation intents are saved in the existing scoped draft.
Retries preserve the original Model publication revision even after it advances
on publication. A partial failure keeps the configuration and identifiers for
recovery. Case creation failure never navigates to a fake graph. The browser test
injects a 503, reloads, retries and verifies exactly one Model/version.

No broad transaction architecture was added: Model and Case remain independent
objects. A valid published Model may remain if the later Case operation fails or
the user abandons setup; it stays reusable, while no usable partial Case is shown.

## 6. Navigation

New planning actions, including the Data Hub new-planning command, enter initial
configuration. A legacy upload URL without a Case redirects with replacement to
the canonical setup URL, avoiding an upload-first loop. Existing Case IDs continue
to open their graph or saved context directly.

Creating a Case goes directly to its graph with its empty Pack and authoritative
readiness. D1 exposes data/configuration/status and actions to load or reuse data;
both use the existing Case Data screen. Publication returns to the graph, which
retrieves fresh server readiness. Result, history, back/forward and reload retain
Case/node/Run identity. D2 retains its approved-D1 dependency.

## 7. Validation

The following records implementation-time focal checks, not the final complete
CI result. All of those focal checks passed; no tests were skipped. The resume
validation and deployment hold are recorded in section 11 and the PR checks.

| Check / command from `backend/` | Result |
|---|---|
| `../.venv/bin/python -m unittest discover -s tests -p test_ultimate_case_models.py -v` | 17 PASS |
| `../.venv/bin/python -m unittest discover -s tests -p test_saga01_planning.py -v` | 5 PASS |
| `../.venv/bin/python -m unittest discover -s tests -p test_ultimate_data_contracts.py -v` | 25 PASS |
| `node --test tests/test_ultimate_case_navigation.mjs tests/test_ultimate_data_navigation.mjs tests/test_ultimate_graph_navigation.mjs` | 3 PASS |
| Browser `test_saga01_planning.Saga01PlanningTests`, via `PYTHONPATH=tests/browser .browser-venv/bin/python -m unittest … -v` | 8 PASS: first-time, recurrent/version/template, new Model/validation, failed Case recovery, graph upload/reuse/revisit, mobile/legacy route, contract retry, Data Hub entry |
| Existing `test_ultimate_case_setup` scenarios 01, 02, 03, 07 | 4 PASS: editor/publish/create/reload, policy validation/draft/CAS, Viewer, versioned Model editing |
| Existing `test_ultimate_navigation.UltimateNavigationTests.test_03_history_new_run_back_forward_reload_keep_case_node_and_run` | 1 PASS over actual published D1/D2 packages |
| Existing `test_ultimate_d1_result.UltimateResultE2E.test_01_complete_publication_retrieval_review_human_approval` | 1 PASS |
| Existing `test_ultimate_d2_lineage.UltimateDayLineageTests.test_01_d2_publication_all_consumers_and_review_use_exact_source` | 1 PASS |
| Node 22 syntax on 8 affected modules, Python AST on 6 affected files, `git diff --check` | PASS |
| Diff against base for `backend/app/engines`, `backend/app/results`, `supabase/migrations` | Unchanged |

Total: 47 Python unit/contract checks, 3 Node tests, 13 browser scenarios and
2 focal E2E tests. Initial browser failures exposed a focus race while resolving
contracts and a publication-revision replay mismatch; both were corrected and
the affected scenarios passed again. The old setup test now expects the new
button and the selected published version rather than an empty option.

Browser/E2E use owned PostgreSQL/PostgREST/Auth/Storage/API/worker fixtures;
production credential bindings are removed from fixture environments. The
first-time/mobile screenshots and logs are under `/workspace/work/dation-saga01/`.
No T0–T12 reconstruction, whole-product audit or full T11 suite was run.
No separate lint/typechecker was introduced. Remote CI is not represented here
as a completed success; the PR runs the existing repository workflow normally.

## 8. Compatibility

Existing published Model versions, Cases, packs, approval lineage and legacy
result readers are unchanged. Case context editing retains its freeze/CAS and
Owner rules. No data was migrated or deleted. The model/library route remains.

New planning from a legacy Data Hub selection no longer opens a pre-Case uploader.
Legacy Orders/Fleet selections are not silently converted or bound to Ultimate
inputs. Reuse within a new Ultimate Case remains constrained by its published
Model/version and compiled contracts, through the existing compatible-input
selector in the graph's Data Pack flow. Existing legacy records remain readable.

## 9. Remaining risks / integration

The multi-operation setup preserves the existing non-atomic Model/Case semantics
described above; recovery is tested. Real production users and deployment were
not exercised. This branch is ready for review/integration; it does not modify
the pending hygiene PR or authorize its branch-deletion operations. No production
Supabase operations, token changes or manual deployment were performed.

## 10. Final status

**IMPLEMENTATION COMPLETE — NOT DEPLOYED**.

## 11. CI resumption and deployment hold — 2026-11-05

At resumption, PR #103 was open and mergeable at
`a97b5ac9e667dc581443549765c33f1e270ef675`, with the same `main` base recorded
above. The latest run, [40978859262](https://github.com/nicsejara/Dation/actions/runs/40978859262),
passed the automated stage but failed one of 298 browser tests:
`test_final_polish_stress_at_data_boundary_with_dev_only_toggle`, with
`Page.goto: net::ERR_ABORTED` while opening D2. PostgreSQL and E2E were skipped;
the original 65 focal checks were not a substitute for these missing gates.

The QA-only toggle awaits a Python binding and then calls `location.assign`.
The test previously continued directly into another dashboard navigation. It
now waits for the requested `ux_stress` URL, application readiness and the
matching D1/D2 dashboard after each mode change. No exception is suppressed,
business assertion relaxed or arbitrary delay added. The unmodified focal test
passed locally once, so the intermittent CI abort was not reproduced locally;
the correction follows its exact failed call sequence and fixture source.

On resumption, the complete `test_final_polish` file passed (9 tests), as did
the frontend/landing/Saga contract suites (38 tests), the three focused Node
navigation contracts and all eight Saga 01 browser scenarios over owned
API/SQL/Storage fixtures. These are 58 focal checks, not a completed full CI.

Reproduction commands from `backend/`:

```sh
PYTHONPATH=tests/browser .browser-venv/bin/python -m unittest test_final_polish -v
PYTHONPATH=tests ../.venv/bin/python -m unittest test_frontend_contract test_landing_navigation_contract test_saga01_planning -v
node --test tests/test_ultimate_case_navigation.mjs tests/test_ultimate_data_navigation.mjs tests/test_ultimate_graph_navigation.mjs
PYTHONPATH=tests/browser .browser-venv/bin/python -m unittest test_saga01_planning -v
```

The next complete run, [41962512563](https://github.com/nicsejara/Dation/actions/runs/41962512563)
at `b8dad5c`, passed 693 Python tests, 153 Node tests and all 298 browser tests.
It then exposed previously skipped SQL harness failures: the CI container lacked
the ownership labels required by the fixtures; mutable `sys.path` let an E2E
module shadow the same-named SQL pilot module; and the restore test could
snapshot the legacy tenant before its asynchronous reconciliation completed.
E2E was still skipped in that run. This was a new downstream blocker, not a
recurrence of the dashboard navigation error.

The CI fixture now creates its own labelled T2/T11 PostgreSQL container and
selects every SQL test module by its `tests.integration` name. Pilot helper
imports use that same namespace. Ownership guards remain unchanged. Restore
waits for the legacy tenant's reconciliation queue to drain before taking the
comparison snapshot, retaining the complete cross-tenant and catalog assertions.
The intermittent digest difference did not reproduce in the local pre-fix run;
that run instead reached the missing compatibility image prerequisite.

CI now builds an explicitly local Docker image from the checked-out source for
the existing legacy/Ultimate compatibility rehearsal. It also installs the
hash-locked Playwright dependencies in the backend interpreter used by E2E;
the pilot browser test uses the executable resolved by its owned fixture.
The E2E scale rehearsal explicitly selects that same local image through
`DATION_T11_R_IMAGE`, instead of relying on a historical, unprovisioned tag.
No image is published, and this local fixture build is not Cloud Build or a
Cloud Run deployment. The qualified SQL runner discovers 168 tests, and the
E2E runner discovers 121, with no import errors.
The job budget is 75 minutes: the observed automated/browser stages already
take about 30 minutes, SQL takes five minutes locally, and E2E exceeds twenty
minutes locally. This leaves room for the complete gates. No check is removed
or weakened to fit the previous 45-minute budget.

The complete local SQL suite passed all 168 tests in 306.202 seconds, including
ownership enforcement, rollout authority, restore, cross-tenant preservation
and actual compatibility-image API/worker operations. The workflow's qualified
module runner selects those same test IDs. Its invocation from `backend/` is:

```sh
# DATION_SQL_TEST_CONTAINER must identify the owned, labelled disposable fixture;
# DATION_T11_CANDIDATE_IMAGE must identify the local compatibility image.
PYTHONPATH=tests/integration python - <<'PY'
from pathlib import Path
import subprocess, sys
modules = ['tests.integration.' + p.stem for p in sorted(Path('tests/integration').glob('test_*.py'))]
raise SystemExit(subprocess.call([sys.executable, '-m', 'unittest', *modules, '-v']))
PY
```

The first full local E2E run executed 121 tests in 1305.820 seconds: 120 passed,
with no skipped tests or failed assertions. The remaining scale test had two
subtest errors because `dation-certification:t11-r-under-test` was not present;
Docker could not pull that unpublished historical tag. This is the missing
image prerequisite corrected by the explicit CI image selection above.
The targeted rerun then exposed a workspace-specific launcher permission:
source files here are mode `0600`, whereas the image correctly runs as UID
65532. The fixture now mounts a read-only `0444` copy from its owned temporary
directory. It does not change repository permissions, image user, CPU/memory
limits, the 90-second execution budget or expected result assertions.
With both prerequisites corrected, the targeted scale test passed in 230.326
seconds, including both cold-first-job repetitions. Admission-to-completion
times were 71.026 and 72.902 seconds; execution times were 69.126 and 70.830
seconds, with peak memory 762327040 and 762425344 bytes under the original
1 GiB limit. The full run's 120 passing methods and this targeted passing
method cover all 121 E2E cases locally; the complete remote job remains the
integration gate. Commands from `backend/`, with locked test dependencies:

```sh
python tests/e2e/run_suite.py
DATION_T11_R_IMAGE=dation-ci-compatibility:test python tests/e2e/run_suite.py --module test_ultimate_scale
```

Run [41970234194](https://github.com/nicsejara/Dation/actions/runs/41970234194)
at `617d578` again passed 693 Python and 153 Node tests, but found a different
browser race in `test_workflow_primitives_preserve_action_identity_states_and_token_overrides`.
Its strict viewport-fit assertion failed; image, SQL and E2E were consequently
skipped. The failure reproduced locally, including three failures in five
diagnostic repetitions. At a 1280 px viewport the root was 984 px wide, while
its inherited `--workflow-bar-width` still held 1144 px from the previous
1440 px viewport. The test had measured before the live resize handler's update.

The test now waits until the root's published width and left position exactly
match its current bounding rectangle before constructing the primitive probe.
The original strict fit, clipping, action identity, sizing, state and token
assertions remain intact; geometry is included in future failure diagnostics.
No product CSS or layout implementation changed.
After the correction, five consecutive executions of the failing method and
the two adjacent bar-sizing/progressive-action tests passed: seven executions
of three methods in 89.482 seconds. The focused command is:

```sh
PYTHONPATH=tests/browser .browser-venv/bin/python -m unittest \
  test_navigation.NavigationTests.test_workflow_primitives_preserve_action_identity_states_and_token_overrides \
  test_navigation.NavigationTests.test_workflow_bars_equalize_context_and_keep_a_wider_primary_action \
  test_navigation.NavigationTests.test_workflow_progressive_actions_share_styles_arrow_and_keyboard_focus -v
```

Run [41974345011](https://github.com/nicsejara/Dation/actions/runs/41974345011)
at `486337d` passed 693 Python and 153 Node tests and the corrected resize test.
Its only browser error was preparation for
`test_d1_v2_table_focus_reveals_partially_clipped_trip_control`: Playwright's
`later.scroll_into_view_if_needed()` timed out waiting for element stability
before reaching the focus assertions. The isolated test and three unchanged
local repetitions passed, so that CI timeout was not reproduced locally.

The test now waits for visible controls, clears the previous focus and performs
an instant DOM scroll for its setup. The first row starts at internal scroll
position zero for the horizontal probe; the fourth-row vertical probe keeps
its original clipping/reset/focus checks. All visibility, horizontal/vertical
bounds, unchanged page/internal scroll, reproduced clipping and no-business-write
assertions are preserved. Three corrected repetitions and the adjacent
low-viewport keyboard test passed: four executions of two methods in 29.092
seconds. No timeout was increased and no product code changed. Focused command:

```sh
PYTHONPATH=tests/browser .browser-venv/bin/python -m unittest \
  test_navigation.NavigationTests.test_d1_v2_table_focus_reveals_partially_clipped_trip_control \
  test_navigation.NavigationTests.test_d1_v2_essential_and_advanced_fit_low_viewports_and_keyboard -v
```

Run [41978123202](https://github.com/nicsejara/Dation/actions/runs/41978123202)
at `73ce773` passed 693 Python, 153 Node, 298 browser and 168 SQL tests,
including all browser synchronization corrections and the compatibility image.
E2E executed all 121 methods with no skips: 119 passed, including both scale
repetitions, and two failed. Data Hub timed out selecting its delete menu item
after archive/restore/archive. Decision Center received an optimistic-version
conflict when archiving immediately after approval while the worker could
still reconcile that Case. Both methods passed unchanged in a focused local
run (75.316 seconds), so the two CI failures were not reproduced locally.

The Data Hub journey now synchronizes each real mutation with its successful
HTTP response, native dialog close event, detached confirmation dialog and
refreshed drawer state before the next action. It still performs the actual
menu and confirmation clicks and verifies original CSV bytes, safe deletion
and lineage preservation. Decision Center waits for the Case-specific
reconciliation outbox acknowledgment before reading the version for its
archive request. The expected HTTP 200, CAS behavior and portfolio assertions
remain unchanged; no 409 retry or business-operation retry was added.

The corrected pair passed twice locally: two methods in 67.101 seconds and
the same two in 62.477 seconds, with no failures, errors or skips. Product
code, production infrastructure and test timeouts are unchanged. Command:

```sh
python tests/e2e/run_suite.py \
  --module test_data_hub.DataHubTests.test_06_real_browser_dda_upload_library_lineage_download_and_safe_delete \
  --module test_decision_center.DecisionCenterTests.test_04_portfolio_summary_is_global_actionable_and_read_only
```

Current full validation and the integrated SHA are
authoritative in [PR #103 checks](https://github.com/nicsejara/Dation/pull/103/checks).
Merge remains conditional on all required checks and repository protections.

No Billing activation, manual Cloud Build, Artifact Registry publication,
Cloud Run deployment/configuration change or production test is authorized or
performed. An automatic GCP trigger caused by a merge must be reported
separately; a Billing failure must not be retried or hidden. Supabase production
is untouched. Scale-to-zero infrastructure changes belong to a separate saga.
