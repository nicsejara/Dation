# J1.01 — G0 baseline audit

Started 2026-11-20 18:34:59 America/Buenos_Aires (21:34:59 UTC).
Base: `894f2fa46469ae9b040a550ecca357398c3171f3`, PR #132 merged;
branch `feat/j1-01-models-library`. Initial worktree clean.
All 33 supplied manifest entries match their size and SHA-256.

## Current flow and bounded target

Current: Core → Case-bound R6 creation/publication/selection → preparation →
Case → Graph. Separate existing `models/index.mjs` uses the older V1 editor.
Target: the **same models entry point**, behind a default-off server capability,
offers Library → R6 draft → explicit save/publish → exact-version Review/History.
Core and Graph retain their current order and pinned versions. No J1.02 selector
or J1.03 preparation redesign is included.

## Verified implementation contracts

- `model-fields-v2.mjs` is the actual R6 five-block editor, including cargo,
  confirmation signatures, volume coherence and server compilation.
- `model-published-review.mjs` currently assumes a real Case. Add an explicit
  library context to this projection, rather than constructing a fictitious Case.
- Existing checked SQL supports N families/workspace, one mutable draft/family,
  immutable version snapshots, workspace locking, revision CAS, creation intent
  replay and publication replay before mutable-draft validation.
- Model writes are admin-only; read permissions and workspace identity are
  checked by RPC. URL intent is not authorization.
- List search supports name only. UI must not promise description search.
- API configuration validation requires a valid domain model, so incomplete R6
  drafts cannot be claimed as server-saved. Use scoped durable browser recovery
  and explicit browser-save copy; valid drafts use existing checked API writes.
- The existing `model.new` session key is unsuitable for parallel new drafts.
  New working-copy UUIDs must never touch `case.new` or change its candidate.
- No schema migration, production inventory or infrastructure change is needed.

## Evidence

Main FAST run `44648963789`: completed/success. Existing deployment workflows
were read only; none invoked. Local baseline browser: 3/3 passed in 40.500 s:
legacy library/version editing, R6 geometry, R6 derived-Case preservation.
Source reviewed: API schemas/routes/service, original model SQL and Saga10 V2
wrapper, RLS/checked actor functions, router/history, scoped lifecycle and forms.
Local SQL contract regression: 25/25 PASS in 24.026 s. It used a labelled, owned PostgreSQL 17 Alpine sandbox. Open PR #102 is unrelated; it was not modified.

## Risks and decisions communicated before implementation

Default-off application capability is required: cosmetic gating is insufficient.
Its backend change requires the existing classifier to determine FULL CI.
Partial drafts are browser-local and clearly labelled. Server CAS never silently
refreshes an expected revision. Publish retries retain their original UUID and
revision. Review GETs do not normalize or write published snapshots. Historical
configurations not representable by R6 stay read-only; no automatic conversion.

No merge, deployment, production SQL, Billing, Jobs, Scheduler or engine activation
is authorized. Package J1.02 documentation is a future interface contract only.
