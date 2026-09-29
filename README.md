# Dation

Dation is an experimental Decision Intelligence platform built around
**Decision Data Assets (DDA)**: repeatable, auditable decision processes that
combine structured data, deterministic analytics and human validation.

## MVP focus

The first Decision Asset is a simplified Logistics DDA.

Initial technical flow:

```text
CSV
 -> validation
 -> cloud ingestion
 -> Python engine
 -> structured JSON result
 -> Supabase
 -> dashboard
```

## Repository

```text
Dation/
├── backend/          FastAPI and Decision Asset engines
├── frontend/         Landing and future SaaS interface
├── sample_data/      Synthetic test datasets
├── docs/             Architecture and technical documentation
├── infra/            Cloud deployment notes
├── index.html        Existing landing page (temporarily preserved)
└── Logo.png          Existing landing asset (temporarily preserved)
```

## Current milestone

Deploy `backend/` to Google Cloud Run and verify:

- `GET /` returns the Dation Core service status.
- `GET /health` returns a healthy status.

After that, the next milestone is connecting Cloud Run to the existing Supabase
project for CSV ingestion.

## Security

Real credentials and `.env` files must never be committed. Only
`.env.example` belongs in the repository.
