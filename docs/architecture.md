# Dation MVP Architecture

## Current milestone

The first technical milestone validates a complete cloud ingestion path before
implementing the real Logistics DDA.

```text
Browser
  |
  v
Cloud Run / FastAPI
  |
  +--> Supabase Storage (private bucket: dda-inputs)
  |
  +--> PostgreSQL (datasets)
  |
  v
Python decision engine
  |
  v
PostgreSQL (decision_runs.result_json)
```

## Repository responsibilities

- `backend/`: FastAPI API, validation, Supabase integration and DDA engines.
- `frontend/`: landing page and, later, the SaaS dashboard.
- `sample_data/`: synthetic datasets used for development and tests.
- `docs/`: architecture and Decision Asset contracts.
- `infra/`: deployment and infrastructure notes.

## Development sequence

1. Deploy a minimal FastAPI service to Cloud Run.
2. Connect the service securely to Supabase.
3. Upload and validate a CSV.
4. Store the raw CSV in Supabase Storage and metadata in `datasets`.
5. Run a simple Logistics Python engine.
6. Persist the structured result in `decision_runs`.
7. Build the results UI.
