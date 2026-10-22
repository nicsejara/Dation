# Navigation and state

```text
Home → DDA Logística → Datos del Case → Decision Map
                                        ↓
                 Config D1 → Run → Dashboard → Approval
                                        ↓
                 Config D2 → Run → Dashboard → Approval → Case complete
```

The authenticated SPA is served at `/app` and its subpaths. The public entry
redirects to the app; unauthenticated requests redirect to login while preserving
the requested resource. Business APIs require verified workspace authority.

## Three navigation responsibilities

* Context navigation (`platform/dda-navigation.mjs`) identifies DDA / Case /
  Decision. Its Case link returns to that Case's Map.
* Case Flow (`dispatch/navigation/case-flow.mjs`) is the vertical sequence: Data,
  Map, Configuration, Dashboard. It uses actual readiness/owner/state gates and
  does not invent a result or implicit approval.
* Decision Navigator (`dispatch/navigation/decision-nav.mjs`) switches D1/D2 at
  the current Config/Dashboard level. Config remains Config; Dashboard requires a
  concrete canonical Run. Future D3 remains visible and disabled.

## Resource contract

`dispatch/navigation/resource.mjs` reads/writes `{view, caseId, nodeId, runId}`.
Canonical paths include `/app/decisions`, `/app/data`, `/app/ddas/logistics`,
`/app/ddas/logistics/data`, `/app/ddas/logistics/decisions`,
`/app/ddas/logistics/configure`, `/app/ddas/logistics/dashboard`.
Keep old `view`, `dda`, `inicio`, library/history aliases readable. Preserve
unrelated query parameters. The Map intentionally omits `node_id` from the URL;
transient node context can focus an owner editor. Config and Dashboard carry it.
Only Dashboard serializes `run_id`.

`navigation/decision-target.mjs` chooses approved or candidate Runs from actual
state. Persisted Run lineage takes precedence over the browser's active selection.
History explicitly opens the chosen historical Run. A return to Configuration
keeps Case/Decision, restores configuration and never admits a Run itself.

`workspace.mjs` owns route generations, AbortSignals and shared polling. Late
responses may not replace another route's state. `dation.dispatch.workspace.v5`
and `dation.dispatch.drafts.v1` retain their existing formats and tab isolation.
Browser back/forward, reload and BFCache recovery use the same resource resolver.

After approval, continuation resolves again against authoritative readiness:
eligible next owner → next Config; missing owner → same Case Map; completed final
implemented Decision → existing Decision Center action. Opening a route never
substitutes for backend permissions, version checks or approval.
