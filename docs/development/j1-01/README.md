# J1.01 — Logistics Models Library & Journey Foundation

Base: `894f2fa46469ae9b040a550ecca357398c3171f3` (R6 / PR #132).
Branch: `feat/j1-01-models-library`. One review PR; no merge or deployment.

The existing Models route now provides a gated independent library, the unchanged
R6 wizard, explicit draft saves, immutable publication, exact-version Review and
History. Models never select themselves into a Case. Existing Core/Graph order,
pinned versions, approvals, physics and execution flags remain unchanged.

## Gates and evidence

| Gate | Result / evidence |
|---|---|
| G0 | [Actual baseline, SQL and compatibility](G0_BASELINE_AUDIT.md) |
| G1 | [Decisions](G1_DESIGN_DECISIONS.md), fail-first evidence under `evidence/g1-red-*` |
| G2 | Existing `models/index.mjs` entry point, real list/search/filter/pagination and errors |
| G3 | R6 controller, independent durable working copies, honest browser/server save status |
| G4 | Exact snapshots, same-model successors, fixed publish intents, protected legacy reads |
| G5 | Typed return tokens, model dirty dialogs, router-owned Back/Forward, Case draft preservation |
| G6 | [Test report](G6_TEST_MATRIX_REPORT.md), [83 criteria](ACCEPTANCE.md), [visuals](VISUALS.md) |
| G7 | Open PR and actual required checks recorded in the integration report; no merge/deploy |

## Review and activation

`DATION_J101_LIBRARY_ENABLED` defaults to false. The server capability also requires
the existing foundation, Saga10 schema and Saga10 UI gates. Preview fixture enables
it only in owned local infrastructure. New-mode deep links fail closed when off;
the original library and production Core journey continue to work.

In preview, open `/app/ddas/logistics/models` or **Abrir biblioteca de modelos**
from Core. **Continuar a Decision Case** resumes the existing Core flow without
model selection. Contextual return preserves the existing Case draft or pinned
Case/Graph route. It does not implement J1.02's reordered steps/manual selector.

[Focused baseline CI repair](CI_IMPORT_GRAPH_FIX.md) · [Architecture/contracts](ARCHITECTURE.md) · [Future J1.02 interface](HANDOFF_J102.md)
· [Manual activation and rollback](RELEASE_ROLLBACK.md).

Browser recovery contains model configuration, not credentials. It is scoped to
authenticated user/workspace, survives tab closure, and is intentionally erased
on logout or identity change. Incomplete drafts are explicitly browser-local;
valid server saves/publications use the existing checked API and SQL.

No SQL migration, engines, Supabase production, IAM, workflows, Billing, Cloud Run,
Scheduler, Jobs, image publication or traffic changes are part of this PR.
