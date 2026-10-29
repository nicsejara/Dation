# Saga 01 — Initial Planning Workflow

Status: **READY TO INTEGRATE**.

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

All final focal checks passed; no tests were skipped.

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

**READY TO INTEGRATE**.
