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
