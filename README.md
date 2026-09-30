# Dation

Dation is an experimental **Decision Intelligence** platform built around
**Decision Data Assets (DDA)**: repeatable and auditable decision processes
that combine structured data, deterministic analytics, configurable priorities
and human validation.

## Current MVP

The first active Decision Asset is **DDA Logística**.

Current end-to-end flow:

```text
CSV / stored dataset
        ↓
validation + dataset profile
        ↓
decision configuration
(preset or weighted)
        ↓
Python deterministic engine
        ↓
DecisionResult JSON
        ↓
decision dashboard + sensitivity
        ↓
AI interpretation / contextual chat
        ↓
traceability + export
```

## Current versions

- Workspace / API: **0.7.0**
- Logistics engine: **0.2.0**
- Frontend: HTML + CSS + vanilla JavaScript
- Runtime: Google Cloud Run
- Data / storage: Supabase
- AI Interpreter: Groq-backed, with versioned knowledge in GitHub

## Repository

```text
Dation/
├── backend/
│   ├── app/
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
