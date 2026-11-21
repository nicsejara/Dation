# J1.01 — G1 contracts

1. One `mountModels` entry point. `models_library_enabled` is returned by the
   backend only when `DATION_J101_LIBRARY_ENABLED=true` **and** existing foundation
   and Saga10 UI/schema gates permit it. Default false retains the legacy route.
2. Reuse `mountModelFields` with V2 R6 defaults and the real contract-preview API.
   No changes to physics, wizard confirmation logic or cargo representation.
3. Working-copy UUID ≠ model UUID ≠ version UUID ≠ Case draft. Durable recovery
   is scoped to authenticated workspace/user. Browser saves are explicit and
   labelled; valid server saves use existing create/update RPCs.
4. Persist exact mutation intents before requests. Creation retries use the same
   body; update retries use the same revision; publication retries use the same
   version UUID. Unknown outcomes must be reconciled before editing/new intents.
5. Review context is explicit (`library` / `case_pinned`). Library Review gets an
   exact model/version pair from GET and never fabricates Case metadata.
6. Routes carry validated IDs and a bounded mode. Return tokens refer only to
   normalized same-application resources in user/workspace-scoped session storage,
   never arbitrary URLs or authority. Existing Case draft keys remain untouched.
7. Async model dirty guard offers Save / Discard / Continue editing. Existing
   router owns browser history and reverts cancelled Back/Forward transitions.
8. Library continuation resumes its stored Core/Graph context or opens the
   unchanged legacy Core flow without model selection. It does not implement
   the future J1.02 step order or candidate selector.
9. Initial invariant tests precede implementation; evidence retains the expected
   RED result. Full required CI runs once the candidate is stable.
