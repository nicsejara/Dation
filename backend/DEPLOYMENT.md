# Dation Decision Workspace

Expected deployed API version: 0.6.0

Primary application URL:
- /app

Compatibility URL:
- /upload (serves the same Decision Workspace)

## Current MVP capabilities

- Private workspace protected with HTTP Basic authentication.
- CSV ingestion and logistics schema validation.
- Immutable raw input stored in Supabase Storage.
- Dataset metadata and deduplication in PostgreSQL.
- Existing dataset reuse from the workspace.
- Deterministic Logistics Decision Engine on Cloud Run.
- Baseline, minimum-cost and minimum-trip scenario comparison.
- Persistent DecisionResult JSON in decision_runs.
- Decision Interpreter knowledge base versioned in GitHub.
- Groq-backed executive explanation and contextual decision chat.
- Persistent AI explanations and messages in Supabase.
- Dataset library and decision history.
- Trace view with run, engine and raw DecisionResult evidence.

## Frontend structure

- app/templates/app.html: application shell.
- app/static/css/tokens.css: design system tokens.
- app/static/css/app.css: responsive product UI.
- app/static/js/api.js: backend API client.
- app/static/js/state.js: client workspace state.
- app/static/js/ui.js: rendering and formatting.
- app/static/js/app.js: interactions and orchestration.

The frontend intentionally remains dependency-free HTML/CSS/JavaScript for the MVP.
The backend API remains the migration boundary for a future Next.js frontend.
