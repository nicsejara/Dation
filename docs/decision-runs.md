# Decision Runs, approval and invalidation

## Current Ultimate Runs

An Ultimate Run pins the Case's Logistics Model/version, published Data Pack
version, read set, Case/node policies and context hash. Admission and the private
worker adapter live in `backend/app/services/ultimate_run_service.py`; exact
runtime identities are resolved through `backend/app/results/registry.py`.

D1 publishes `transport_plan_v1`; D2 publishes `day_scheduling_v1` bound to the
approved source Run and result fingerprint. D2 preserves D1 trips, allocations
and resources. Packages, artifacts and evidence are read through
`result_package_service.py`, `result_artifact_service.py` and
`result_consumer_service.py`; `ultimate_decision_context.py` supplies the
reference-bound Approval Copilot. These service paths are under
`backend/app/services/`.

Existing SQL release/workspace/pilot gates govern admission and approval. The
public runtime catalog deliberately retains its availability distinction; do not
change it merely because an Ultimate schema is known. See the
[master baseline](MASTER_DEVELOPMENT_BASELINE.md) and [architecture](architecture.md).

## Retained Orders/Fleet Run contract

The following documents the compatible `assignment_v1` / `scheduling_v1` flow and
its immutable dataset-pair behavior. Its safeguards remain meaningful for those
Runs; the Ultimate versioned input/package contract above governs new Ultimate
execution.

One Case/Decision supports multiple Runs. A rerun is a new admitted intention,
not a new Case. The queue fingerprints the request and resolves an idempotent
`run_id` replay before mutable upstream checks. Replaying the same intention must
not create another Run or invalidate history again.

The Run stores Case/node/upstream IDs, immutable configuration, actual creator,
engine/version/schema, input/result fingerprints, execution stages and result.
Assignment is non-temporal; Scheduling consumes the currently approved Assignment
handoff and preserves its trips/loads/vehicles. Historical Dispatch/Logistics
schemas remain readable and exportable.

## Approval authority

Approval is by concrete Run, through `approve_decision_run_version`. The current
eligible Decision Owner or actual workspace administrator can approve; viewers
cannot. Historical `approved_by_user_id` is the approving actor, not a projection
of today's assignment. Only one non-superseded approval exists per Case/node.

`decision_cases.state_json` is a cache. The pure Case history projection and SQL
history summaries derive current state from Runs. A reconciliation callback must
never restore approval from stale cached `approved_at` or frontend status.

## Rerun admission

```text
D1 approved + D2 approved
  → new D1 Run admitted
  → D1 approval retired; new Run pending/running/review
  → D2 invalidated/stale
  → old Runs, results, fingerprints, actors and approval events retained
```

Invalidation occurs at admission, including when execution later errors. SQL
`decision_runs_reopen` / `dation_private.invalidate_run_lineage` own the transition,
with shared workspace/Case locks against concurrent approval. The worker updates
execution and requests reconciliation; it does not manufacture approval.

## Data Pack identity

The persisted Orders/Fleet pair cannot be rebound. The replacement RPC returns the
same Case for unchanged inputs and a deterministic new Case for changed inputs.
Original Runs/approvals stay attached to the original Case. Owners are not silently
copied as if newly assigned; metadata edits and owner reassignment alone do not
change immutable inputs or mathematical results.

## Implementation locations

* `app/services/dispatch_job_service.py`: admission, idempotency, worker lifecycle.
* `app/domain/decision_cases.py`: pure state validation/history projection.
* `app/services/decision_case_service.py`: Case persistence/history/approval checks.
* `supabase/migrations/20261022020000_decision_run_reopening.sql`: admission invalidation.
* `supabase/migrations/20261022030000_case_ownership_readiness.sql`: canonical owner/gates.
* `supabase/migrations/20261022040000_case_attributes_apply.sql`: atomic attributes/Owner Apply.
* `static/js/dispatch/runs/`: polling, execution status, toolbar, trace and export.

These migrations are already part of the upgrade history. A code refactor does not
require replaying them in production.
