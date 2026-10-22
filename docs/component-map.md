# Shared component map

Paths below are relative to `backend/app/static/js/dispatch` unless qualified.
The frontend uses render/mount functions, native elements and ES modules.

| Component | Purpose / main inputs | Location | Used by / why not duplicate |
|---|---|---|---|
| Workflow Hero | metadata, title, description, optional decision panel | `decision-config-ui.mjs::decisionHero` | Data, Map, D1/D2 Config; common escaping and hierarchy |
| Case Context | native disclosure, Case name/ID, Data Owner, immutable file cards, change/copy hooks | `decision-config-ui.mjs::decisionCaseCard`, `bindCaseContext` | Map, D1/D2 Config; identical fields and keyboard behavior |
| Data file card | filename, kind, validated count | `decision-config-ui.mjs::decisionDataFileCard` | Map and configs; shared safe truncation/full title |
| Case Flow | resource/state → Data/Map/Config/Dashboard targets | `navigation/case-flow.mjs` | all Case screens; one gate/context policy |
| Decision Navigator | Case, active node/view, workflow | `navigation/decision-nav.mjs` | Config and dashboards; preserves current navigation level |
| Context navigation | current DDA, Case and Decision | `../platform/dda-navigation.mjs` | application shell; never mount a second Case selector |
| Case Attributes | preparation state, persistence and Apply callback | `cases/case-identity.mjs` | Data screen only; feature-local form |
| Case preparation ownership | Data Owner draft/snapshot and save notification | `cases/workflow-context.mjs::mountCasePreparation` | Data form only; reuses the canonical selector |
| Decision Owners | Case node cards, workflow snapshot and callback | `cases/workflow-context.mjs::mountMapResponsibilities` | Map only; backend eligibility and CAS remain authority |
| Responsibility selector | stage, snapshot, caseId, optional deferred draft | `cases/workflow-responsibility.mjs` | Data Owner and Decision Owner; one candidates/permissions/conflict contract |
| Workflow action bar | readiness, items, action callback | `workflow-action-bar.mjs` | Data and Config D1/D2; shared responsive four-check behavior |
| Review dialog | rows, hooks and validated execute callback | `decision-config-ui.mjs::executionReviewDialog`, `bindConfigReview` | D1/D2; one focus/escape/double-submit policy |
| Result summary | escaped value segments + supporting text | `result-summary.mjs` | D1/D2 Hero; presentation only, no result recalculation |
| Dashboard presentation | run-specific storage key, toggle/content, lazy callback, scroll target | `dashboard-presentation.mjs` | D1/D2 shells; shared expanded state and disposal |
| Run toolbar | persisted Run, Case actions, export and details | `runs/dashboard-toolbar.mjs` | D1/D2; one approval, rerun, drawer/export lifecycle |
| Approval/continuation | latest continuation resolver + callbacks | `runs/dashboard-actions.mjs` | dashboards; resolve after approval and again before navigation |
| Execution progress | real backend stage | `runs/execution-progress.mjs` | D1/D2 pending screen; indeterminate, no invented percentage |
| Approval trace | concrete Run + Case/owner context | `runs/approval-trace.mjs` | D1/D2 Hero; actual historical approval actor |
| Run polling | read, onRun, onError, interval/grace | `runs/polling.mjs` | workspace execution/recovery; one owned polling lease |
| Error recovery | typed error, retry action | `shared.mjs::errorBox` | feature views; consistent session/missing/permission/network handling |
| Scope | root, listeners, timers, observers | `lifecycle.mjs` | all interactive views; cleanup and late-response suppression |
| Stylesheet readiness | identity/path/version | `styles.mjs` | lazy feature styles; one loading/retry identity |
| Chart wrapper | existing palette/options + root | `shared.mjs::chart` | charts; shared SVG rendering, resize/disposal/reduced motion |

Assignment content lives under `assignment/`: scope, objectives/resources,
packing/vehicle interpretation, comparison and evidence. Scheduling content lives
under `scheduling/`: source handoff, calendar/SLA rules, timeline and validation.
Their shell markup stays domain-specific; shared stateful behavior belongs to the
components above. Historical renderer/engines remain compatibility consumers.

UI colors, spacing, radii, typography, action heights and status tokens remain in
`static/css/tokens.css`; action/card patterns in `dation-design-system.css`;
Case Context/execution/result text patterns in `workflow-context.css`. Preserve
stylesheet order and selector hooks when extending these components.
