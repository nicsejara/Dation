# Dation — Master Development Baseline

Reference date: 2026-10-29 (`America/Buenos_Aires`).

## Product

Dation — Decision Intelligence.

```text
DATA → ENGINE → RESULT → EVIDENCE → IA → HUMAN APPROVAL
```

## Source of truth

- Repository: `nicsejara/Dation`.
- Branch: `main`; update it from `origin/main` before starting an incremental task.
- Consolidated product bookmark: annotated tag
  `ultimate-mvp-production-20261029`, commit
  `3e8712962ba7b444f47b44d5afa9887f4c2e4a10`.
- The existing master development chat is the ongoing development context.
- The [hygiene report](FINAL_REPOSITORY_HYGIENE_REPORT.md) records the retained
  local unique-work exception and branch cleanup awaiting approval.

Use current code and documentation. Execution reports T0–T12/T12-R remain
historical evidence, including original HOLD statements; they are not instructions
to repeat those phases or replay production operations.

## Decisions

| Decision | Stable node ID | Engine identity | Result schema |
|---|---|---|---|
| D1 · Transport Plan | `logistics_assignment` | `transport_plan` / `2.0.0` | `transport_plan_v1` / 1 |
| D2 · Day Scheduling | `logistics_scheduling` | `day_scheduling` / `2.0.0` | `day_scheduling_v1` / 1 |

Models, model versions, Case policy and versioned progressive Data Packs define
the frozen input context. D1 publishes a Transport Plan. D2 schedules the approved
D1 trips and resources without changing their allocations. Result Packages bind
results, fingerprints, provenance and evidence; `decision_context_v1` supplies the
LLM explanation layer. Historical schemas retain their original readers.

Existing SQL release/workspace/pilot capabilities govern admission. Preserve those
gates; the public runtime registry deliberately distinguishes known identities
from available execution capabilities.

## Runtime and implementation

- FastAPI; Python 3.13 / Pandas / OR-Tools; native HTML/CSS/JavaScript modules.
- Supabase Auth, tenant-scoped PostgreSQL and private Storage.
- Cloud Run API and durable worker, Cloud Build and Artifact Registry.
- LLM explanation layer / Approval Copilot over published evidence.

In the existing workspace, use `/workspace/Dation/.venv/bin/python` (3.13) and
the project Node 22 toolchain under `/workspace/.dation-cloud/node/`; the default
shell currently selects Python 3.12 / Node 24. Old phase-specific start/smoke
instructions are historical, including the retired Basic-auth smoke helper.

| Responsibility | Canonical location |
|---|---|
| Logistics domain and frozen context | `backend/app/domain/logistics/` |
| Result contracts, identity and validation | `backend/app/results/` |
| D1 | `backend/app/engines/assignment/transport_plan.py` and `transport_policy_result.py` |
| D2 | `backend/app/engines/scheduling/day_scheduling.py` |
| Admission and worker adapter | `backend/app/services/ultimate_run_service.py` |
| Published packages and artifacts | `backend/app/services/result_package_service.py`, `result_artifact_service.py` |
| Result consumers and Copilot | `backend/app/services/result_consumer_service.py`, `ultimate_decision_context.py` |
| Case/graph/data APIs | `backend/app/platform/ultimate*_routes.py` |
| Current result UI | `backend/app/static/js/dispatch/results/` |

Normal delivery: `main → Cloud Build → Artifact Registry → Cloud Run worker →
Cloud Run API`. GitHub Actions provides separate CI. The existing external build
trigger owns deployment; ordinary development does not need manual GCP tokens.
See [deployment](../backend/DEPLOYMENT.md) and [schema history](../supabase/README.md).

## Development rule

Real usage → issue → focal analysis → fix → focal tests → main → production.

For each task, update `main`, understand the affected component, make the focused
change, validate its boundaries, report and integrate through normal delivery.
Use an isolated task branch when changing files. Keep scratch assets under
`/workspace/work/`, outside the repository. Do not use old branches as architecture
context or automatically import their changes.

## Non-negotiables

- The deterministic engine owns decisions.
- The frontend does not recalculate results.
- AI does not optimize, approve or override decisions.
- D2 does not reassign D1.
- Preserve provenance, evidence, fingerprints and human approval.
- Preserve node IDs, result schemas, contracts, RPCs and certified ABIs.
- Use focal tests for ordinary fixes; broad audits require a specific task.
- Already-applied migrations remain immutable; normal setup does not replay them.
- Keep credentials out of code, logs and chat. Production is not a QA fixture.
