# Dation Decision Workspace v0.2

Expected deployed API version: **0.7.0**

Expected Logistics engine version: **0.2.0**

Primary application URL:
- `/app`

Compatibility URL:
- `/upload` (serves the same workspace)

## Experience architecture

The application is a vanilla HTML + CSS + JavaScript SPA with four primary areas:

1. **Inicio**
   - Decision Data Asset selector.
   - DDA Logística is the only active Decision Asset.
2. **DDA Logística**
   - Dataset selection / upload / profile.
   - Preset decision modes.
   - Custom cost/trips weighting.
   - Deterministic execution.
3. **Dashboard de decisión**
   - Run context.
   - KPIs and baseline impact.
   - Dataset context.
   - Sensitivity against 100/0 and 0/100 extremes.
   - Assignment drivers.
   - Model assumptions.
   - AI interpretation, export and contextual chat.
4. **Trazabilidad**
   - Datasets.
   - Decision history.
   - Technical evidence.

## Decision API

Primary execution endpoint:

`POST /api/runs/{dataset_id}`

Body:

```json
{
  "mode": "custom",
  "objective": "custom",
  "weights": {
    "cost": 0.7,
    "trips": 0.3
  }
}
```

Presets use canonical weights:

- `min_cost` → cost 1.0 / trips 0.0.
- `min_trips` → cost 0.0 / trips 1.0.

Legacy calls that use `?objective=min_cost` or `?objective=min_trips` remain supported.

## Engine v0.2

The custom mode uses per-shipment Min-Max normalization:

```text
normalized_cost = (cost - min_cost) / (max_cost - min_cost)
normalized_trips = (trips - min_trips) / (max_trips - min_trips)

decision_score =
    cost_weight * normalized_cost
  + trips_weight * normalized_trips
```

When max equals min, the normalized value is 0.

The exact extremes reuse the preset selectors, guaranteeing:

- 100/0 == `min_cost`
- 0/100 == `min_trips`

The DecisionResult preserves:

- baseline,
- min_cost,
- min_trips,
- custom (when applicable),
- configuration,
- sensitivity metadata,
- model assumptions,
- deterministic assignment evidence.

## Data profile

`GET /api/datasets/{dataset_id}/profile`

Profiles the raw stored CSV on demand without a new Supabase migration. It returns validation, dataset metadata, operational summary and a small record preview.

## AI Interpreter

The interpreter remains downstream from the deterministic engine.

It receives:

- mode,
- weights,
- selected scenario,
- baseline,
- sensitivity extremes,
- major changes,
- model assumptions.

It never recalculates the decision.

Historical explanations and chat messages can be restored with:

`GET /api/runs/{run_id}/interpretation`

## Compatibility

The implementation preserves:

- HTTP Basic authentication,
- CSV upload,
- deduplication,
- Supabase Storage,
- Postgres persistence,
- Cloud Run,
- Groq,
- `/app`,
- `/upload`,
- engine 0.1 historical runs.

Historical runs with only:

```json
{"objective": "min_cost"}
```

are reconstructed as the canonical 100/0 preset.

## Automated tests

Run from `backend/`:

```bash
python -m unittest discover -s tests -v
```

The suite covers:

- custom 100/0 equivalence with min_cost,
- custom 0/100 equivalence with min_trips,
- deterministic 70/30 behavior,
- baseline preservation,
- custom score serialization,
- weight validation,
- legacy configuration reconstruction.


## Home hotfix — simplified DDA selector

Latest UI hotfix on main:
- Inicio contains only a hero and two Decision Data Assets.
- DDA Logística is the only interactive home CTA.
- Its CTA routes to `logistics-config`.
- DDA Producción is visible but disabled / upcoming.
- The previous oversized inline SVG illustration was removed from Inicio.


## Home v3 — professional DDA selector

Final main-state for the current deployment:
- Professional executive hero inspired by the dashboard reference.
- Visual decision tiles in the hero; no inline SVG artwork.
- Two Decision Data Assets on Inicio.
- DDA Logística is the only interactive CTA and routes to `logistics-config`.
- DDA Producción is visible and disabled.
- CSS and JavaScript URLs are cache-busted from `app.html`.


## Journey navigation hotfix — 2026-09-30

- Topbar simplified to a clickable decision journey.
- Inicio shows only "Inicio".
- Logistics flow shows: Inicio > DDA Logística > Cargar data > Configurar decisión > Dashboard decisión.
- Previous stages are clickable and navigate/scroll back.
- Sidebar buttons use the same resilient global navigator.
- MVP badge, service verification status and avatar were removed from the topbar.
- app.js delegates view changes to the global journey navigator so programmatic transitions stay synchronized.


## Logistics overview flow — 2026-09-30

Navigation now follows:
- Inicio
- DDA Logística overview
- Cargar data
- Configurar decisión
- Dashboard decisión

The new DDA Logística overview explains:
- decision purpose,
- baseline and alternatives,
- sensitivity,
- required input data,
- decision outputs,
- current MVP scope and limits.

The home card and sidebar open the overview.
The overview CTA starts the process at the data-loading stage.


## Dedicated data ingestion stage — 2026-09-30

The Logistics flow now separates data ingestion from decision configuration:

- DDA Logística overview
- Cargar data
- Configurar decisión
- Dashboard decisión

Cargar data now includes:
- blue drag & drop CSV area,
- reuse of previously stored datasets,
- selected evidence summary,
- automatic validation results,
- schema / required columns / empty required cells / duplicate shipment checks,
- dataset profile and preview,
- explicit "Configurar decisión" CTA enabled only after validation succeeds.

The top journey navigation unlocks Configurar decisión only when the dataset profile is ready.


## Resilient data ingestion controller — 2026-09-30

Root cause fixed:
- a frontend module syntax error prevented the workspace JavaScript from booting,
  which left file selection, drag & drop and dataset library interactions inactive.

Hardening added:
- standalone classic `data-stage.js` controller for the complete Cargar data flow;
- file picker binding;
- drag & drop binding with guided overlay;
- dataset library loading and selection;
- upload to `/api/datasets/upload`;
- profile validation through `/api/datasets/{id}/profile`;
- bridge event `dation:dataset-ready` to synchronize the main workspace state;
- downloadable `Dation_Logistics_Template.csv` with 14 required columns and 6 simulated rows;
- explicit structure guidance in the UI.

Final frontend checks:
- app.js syntax OK;
- ui.js syntax OK;
- data-stage.js syntax OK;
- all data-stage DOM IDs resolved;
- template contains 14 required columns.


## Decision configuration stage v2 — 2026-09-30

The decision configuration stage is now isolated from the legacy workspace bindings.

Flow:
- validated dataset is persisted in session storage;
- decision-stage.js restores the dataset independently;
- three starting presets are available:
  - min_cost = 100% cost / 0% trips;
  - min_trips = 0% cost / 100% trips;
  - balanced = custom 50% / 50%;
- both Cost and Trips have linked sliders;
- moving either slider automatically adjusts the other so total weight always remains 100%;
- all non-extreme weights are submitted as mode=custom, objective=custom;
- execution requires an explicit review modal;
- the confirmation modal displays dataset, mode, weights and engine version;
- confirmed execution POSTs to /api/runs/{dataset_id};
- successful runs are bridged back to the main workspace and rendered in Decision Dashboard.

Hardening:
- stale legacy upload and decision binders removed from app.js;
- stale legacy decision UI renderer removed from ui.js;
- validated dataset persisted across stages;
- GitHub Actions now runs on main pushes and validates data-stage.js + decision-stage.js syntax;
- frontend contract tests cover stage DOM/API contracts.


## Enterprise Decision Dashboard v2 — 2026-09-30

Root cause fixed:
- execution previously awaited the synchronous POST /api/runs/{dataset_id}
  before entering Dashboard;
- rendering also occurred before navigation, so a rendering exception could
  prevent navigation completely.

Execution flow now:
- the browser generates a UUID for the run;
- POST /api/runs/{dataset_id}?run_id={uuid} starts with that persisted ID;
- Dashboard opens immediately in an execution/loading state;
- the request continues while Dashboard polls GET /api/runs/{run_id};
- run_id is stored in the URL and sessionStorage to recover after reload;
- completed runs replace skeletons with the real dashboard;
- errors, timeout and cancelled client waiting have explicit UI states and retry actions.

Dashboard v2 includes:
- decision hero and semantic KPIs;
- honest indeterminate execution progress and skeletons;
- impact chart vs baseline;
- reference selector and decision comparison table;
- relative comparison chart;
- drivers, context, sensitivity and assumptions;
- AI executive summary using the existing /explain endpoint;
- contextual chat using the existing /chat endpoint.

Known backend gaps intentionally not simulated:
- no granular execution-progress endpoint, so no fake percentages are shown;
- no server-side cancellation endpoint; "Detener espera" cancels client waiting only;
- no token streaming endpoint for LLM responses; the UI states this explicitly.


## Persistent dashboard + interpreter ownership — 2026-09-30

Navigation:
- Sidebar primary navigation exposes only Inicio.
- DDA Logística remains in the Decision Data Assets section.
- DDA overview exposes two explicit paths:
  - Iniciar nueva decisión.
  - Analizar mi última decisión.

Decision persistence:
- The latest completed run is resolved from Supabase decision_runs through /api/runs.
- The run summary is resolved to the full run before rendering.
- Dashboard availability remains unlocked after a completed run.
- Dashboard can be reconstructed after leaving the view or reloading the page.

Interpreter hardening:
- interpreter-stage.js owns LLM status, executive explanation, saved interpretation recovery and contextual chat.
- The interpreter no longer depends on app.js activeRun timing to make its buttons work.
- Generated explanation is synchronized back to app.js only for export state.

Custom-decision semantics:
- Engine behavior was verified: custom runs persist mode=custom, objective=custom and recommended_scenario=custom.
- If a custom assignment equals min_cost and/or min_trips, it remains labeled Configuración personalizada.
- Equality with an extreme is communicated as sensitivity equivalence rather than a renamed objective.
- Interpreter knowledge/prompt version is now v0.3.
