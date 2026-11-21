# J1.01 manual activation and rollback — NOT EXECUTED

This PR is for review only. Merge, image publication, deployment and promotion
require a separate explicit GO. Do not use the existing G6 automation to bypass
its risk classification: this change is R3 and requires FULL CI.

## Later controlled activation

1. Review PR diff, exact candidate SHA, FAST/FULL/required-gate and the 83 criteria.
   Confirm the current `main` base and any intervening changes before authorizing
   merge. No migration is required.
2. After explicit merge/publication GO, follow the existing
   [repository release runbook](../README_RELEASE.md), with a validated immutable
   digest and a private/no-traffic revision first. Record actual SHA, digest,
   service revision and prior rollback revision; none is invented here.
3. Keep `DATION_J101_LIBRARY_ENABLED` absent or `false` on ordinary production
   traffic. Existing Core/Graph remains the default. Enabling preview requires a
   separate approved environment configuration change; no such change was made.
4. In authorized preview, the server additionally requires existing foundation,
   Saga10 schema/UI gates. Test the library URL, A/B creation, local incomplete
   saves, valid server save, v1/v2 History, Case-pinned v1, browser Back and viewer
   permissions. Keep all optimization/admission/Scheduler/zero-idle guardrails at
   their previous values. Do not turn on J1.02/J1.03 implicitly.
5. Only a later release decision may expose the new entry flow to ordinary
   traffic. Its final Case step order/manual selection belongs to J1.02, not this
   preview. No GCP/Supabase/IAM command is required to review this code locally.

## NO-GO

Failing/pending required checks; wrong SHA; Case pin/hash changes; automatic Case
creation/selection; loss of a working copy; permission bypass; duplicate versions;
unresolved mutation intent; unsupported browser without Web Locks; responsive
overflow; unintended engine/infra activation. Preserve evidence and recovery state.

## Rollback

- Disable only the real J1.01 application flag in an authorized future rollout,
  preserving its prior value. No traffic/config change was performed by this PR.
- Or revert the J1.01 PR through the normal reviewed process and reuse the known
  prior immutable image/revision via the release runbook after explicit GO.
- Retain model families, published snapshots, Cases, packs, runs and approvals.
  There is no destructive SQL rollback and no production data cleanup.
- Preserve pending browser intents until reconciled with exact model/version IDs.
  Do not clear all storage to repair a failed publication.
- Verify the original Models route, Core setup and Case/Graph pinned Review after
  rollback. Default-off behavior has a dedicated browser test.

Browser-local drafts are not a cloud backup or cross-device synchronization. They
survive tab closure under the same account and are intentionally cleared by logout
or identity change. Inform users before logout; use a valid server save when ready.
