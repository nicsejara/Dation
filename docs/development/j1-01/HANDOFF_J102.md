# Future J1.02 contract — NOT IMPLEMENTED

Base for this work is R6 main `894f2fa46469ae9b040a550ecca357398c3171f3`;
the J1.01 PR records the final validated SHA separately.

Public route stays `/app/ddas/logistics/models`. Parameters:
`model_id`, `model_view=library|edit|review|history`, `model_version_id`,
`model_work_id`, `model_return_id`. Review uses exact family/version IDs. Typed
return context uses the existing `resource.mjs` serializer, not a parallel router.

Exports reusable by a later Case selector:

- `modelRoute`, `rememberReturn`, `resolveReturn`, `browserIdentity` from
  `model-library-state.mjs`; these never write Case state.
- `mountPublishedReview(..., {reviewContext:'library'})` for a standalone snapshot;
  default `case_pinned` requires a real Case and retains derivation rules.
- Existing list/get/preview/templates API and immutable model/version identifiers.
- `libraryFooter` composes four semantic zones without changing other footers.

J1.02 must own the manual candidate selection in an independent Case draft. It
must never interpret library publication or `model_id` navigation as selection.
Persisted Cases retain their exact published version/hash. Existing preparation
and legacy Core order stay unchanged until their separately approved successors.

Browser fixture `version-integrity.json` records actual synthetic A/B/v1/v2/Case
IDs and invariance results. No production migration or historical reconciliation
was performed. New features must continue to respect existing model/Case roles,
server CAS, immutable publication, leases, approval and execution guardrails.
