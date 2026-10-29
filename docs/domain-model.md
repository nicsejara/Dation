# Domain model

## Current Ultimate concepts

See the [master baseline](MASTER_DEVELOPMENT_BASELINE.md) and
[current architecture](architecture.md). These concepts coexist with retained
compatibility contracts:

| Concept | Current meaning / authority |
|---|---|
| Logistics Model / version | Versioned operating model, dimensions and policies used by a Case. |
| Ultimate Decision Case | Operational context tied to model/version, planning horizon, Case policy, graph and owners. |
| Progressive Data Pack / version | Published, versioned `transport_demand` and `transport_resources` inputs and canonical read-set identity. A Run pins its input version. |
| D1 / D2 | `logistics_assignment` produces Transport Plan; `logistics_scheduling` produces Day Scheduling from approved D1 without reassigning it. |
| Result Package | Published `DecisionResultPackageV1`, bound to runtime identity, input/result fingerprints, immutable artifacts and evidence. |
| Approval Copilot | `decision_context_v1` and published references for explanation; it cannot optimize or approve. |

Preserve the release/workspace/pilot gates. Known schemas do not imply an enabled
runtime. The following table and preparation rules describe the legacy
Orders/Fleet contract, including its immutable dataset-pair behavior and future
D3 placeholder; they do not define an active third Ultimate engine.

## Orders/Fleet compatibility concepts

| Concept | Meaning / authority |
|---|---|
| DDA | Decision Data Asset: a repeatable domain decision chain. Logistics is active; future DDAs remain disabled. Registry: `backend/app/static/contracts/foundation-v2.json`. |
| Decision Case | One operational context bound to immutable Orders/Fleet dataset IDs. It contains attributes, Data Owner and decision history. |
| Case Attributes | Name, category and optional description. Applying edits never creates a replacement Case. |
| Data Pack | The typed Orders + Fleet pair, validation and readiness evidence. It is immutable once attached to a persisted Case. |
| Data Owner | One active eligible member responsible for Case data. Applied jointly with Case Attributes through a versioned transaction. |
| Decision | A node of the DDA chain: D1 Assignment, D2 Scheduling, future D3 Final Assignment. This is not a Run. |
| Decision Owner | One eligible member per Case/Decision. That owner or an actual workspace administrator can execute/approve, subject to current gates. A viewer cannot mutate. |
| Decision Configuration | Domain-specific options/weights/filters for the next Run. Browser drafts are session state; admitted configuration is immutable evidence. |
| Decision Run | One concrete admitted intention with an ID, configuration, engine identity, input/result fingerprints and lifecycle. Multiple Runs belong to the same Case/Decision. |
| Decision Result | Persisted deterministic engine output of a completed Run. Dashboards and AI consume this evidence; neither changes the calculation. |
| Decision Approval | A human action on a concrete Run. Current approval is SQL authority, with immutable historical actor/evidence and append-only events. |

Before CSV registration, applying attributes saves an existing session preparation
snapshot. Four checks remain independent: Orders, Fleet, applied attributes and
eligible Data Owner. Once typed inputs are valid, one Case is registered and the
applied snapshot is promoted through the atomic attributes/Owner API.

Reconfiguration or a new Run stays in the same Case. Changing either dataset ID
uses the existing immutable Data Pack replacement contract to create/reuse a new
Case. Re-selecting the same pair through that contract returns the same Case;
creating an unrelated new operational Case can deliberately reuse datasets.

Operational status and data readiness are different dimensions. `available`,
`running`, `review`, `approved`, `locked`, `needs_data`, `error`, `stale` describe
Decision state. A historically approved Run may remain readable after its approval
is superseded. Archived Cases remain consultable with mutation guards.

SQL compatibility fields such as `data_steward`, `approver_user_id`, `approved_by`
are not additional operational roles. Actual Run creator, current assigned owner
and historical approval actor are separate facts and must not be conflated.
