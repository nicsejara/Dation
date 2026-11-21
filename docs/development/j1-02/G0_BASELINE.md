# J1.02 G0 — verified baseline

- Repository `nicsejara/Dation`; branch `feat/j1-02-decision-case-v2`.
- Main `a41d644c4e25c7c9b85a8b9881ab3f4fb61989fc`.
- PR #133 merged at `f1e2e4a2077790f0fadd68173562b02f437d0a9a`, verified ancestor.
- Delta since #133: #134 only changes `backend-tests.yml` to separate the existing browser and backend E2E jobs. It preserves required-gate and assertions. No application delta.
- Main CI `44902633460` terminal success; subsequent publication `44906521051` visible but no live production state claimed or queried.
- Package integrity: all 33 manifest entries match size and SHA-256. Product/master, technical, design, QA and prior-source precedence read; real J1.01 handoff confirmed.
- Local contracts PASS; J1.01 real browser/API/PG17 **14/14 PASS (100.961s)**. First fixture launch used the host Python without OR-Tools; corrected only environment `DATION_RUNTIME_PYTHON` and `CHROMIUM_EXECUTABLE`, no product fix.

## Localized architecture findings

`ultimate-case-setup.mjs` owns legacy Model→Data→Case. `mountCorePreparation`/`decision_journey_service.finalize` freezes an idempotent Case creation body before recoverable Case/Pack publication. Model selection is currently embedded in that legacy setup. J1.01 library and return tokens must remain independent. Resource normalization is solely `navigation/resource.mjs`.

`CasePolicy` V1 and `NodePolicy` enforce typed hard bounds; `transport_policies.PolicySearch` adds real HIGH primary-dimension coverage constraints to CP-SAT. Existing solver fixes priority coverage lexicographically before its selected goal. Monetary costs are integer minor units; a subsequent exact own-load stage can preserve proven minimum cost in that established admissible coverage frontier. No epsilon or new cost function.

There is no persisted Decision Case definition-revision history. Existing Case `workflow_version=2` is NOT the new J1.02 definition schema. A separate versioned definition and additive private append-only history are required; legacy snapshots must not be reinterpreted or backfilled.

Frozen context and run inputs already have semantic hashes. The optional binding remains absent for legacy inputs. For V2, business and acceptance policy enter the mathematical projection; revision UUID/hash remain in full Run/context/artifacts but are excluded from that projection so metadata-only edits do not change mathematical identity. D2 uses the exact approved D1 binding.

## Gates / boundaries

G0 PASS. G1 design precedes SQL/UI. No productive Supabase/GCP/IAM/Billing/deployment action or productive engine activation. The package authorizes the focal, tested solver adaptation in source code. R6 physical code stays unchanged. New writes are dual-gated; flag OFF preserves old routes and V2 history remains readable after a future pilot. Every later gate needs executed evidence, not this audit alone.
