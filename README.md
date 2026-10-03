# Dation

Dation is an experimental **Decision Intelligence** platform built around
**Decision Data Assets (DDA)**: repeatable and auditable decision processes
that combine structured data, deterministic analytics, configurable priorities
and human validation.

## Current MVP

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

Phase 2 adds a session-persistent Decision Case, a visual Decision Map and explicit human approval states. Changing Orders or Fleet starts a new case and marks the predecessor STALE. Executed runs persist `decision_case_id` and `decision_node_id` as lineage metadata without changing the deterministic solver fingerprint.

## Current versions

- Workspace / API: **1.0.0**
- Dispatch engine: **2.2.0** (`dispatch_v2`, SLA-first + cost/time/own-fleet/CO₂ objectives); historical engine **0.2.0** retained
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


## Dispatch 1.0 activation

The new flow requires the additive Supabase migration applied manually by the owner.
Until then the UI reports the missing activation and offers the legacy workflow.
See [deployment](backend/DEPLOYMENT.md), [architecture](docs/architecture.md),
[data contracts](docs/data-contracts.md), [model ADR](docs/adr/0001-dispatch-decision-model.md),
[validation](docs/validation-dispatch-v1.md) and [CSV test guide](sample_data/v1/README.md).
