# Shared component map

Paths below are relative to `backend/app/static/js/dispatch` unless qualified.
The frontend uses render/mount functions, native elements and ES modules.

## Current Ultimate surfaces

| Surface | Canonical location relative to the path above |
|---|---|
| Case setup | `cases/ultimate-case-setup.mjs` |
| Progressive Case Data | `upload/ultimate-case-data.mjs` |
| Decision graph / map | `navigation/ultimate-graph.mjs`, `cases/ultimate-decision-map.mjs` |
| Result Package presentation | `results/mount.mjs`, `results/dashboard.mjs`, `results/package.mjs`, `results/details.mjs`, `results/visuals.mjs` |

These consume the authoritative Ultimate APIs and published packages described in
[architecture](architecture.md). The remaining foundation map describes shared
primitives and compatibility surfaces; its historical Orders/Fleet and
Assignment/Scheduling 1.0 descriptions do not replace the current Result Package
contracts. Development entrypoint: [master baseline](MASTER_DEVELOPMENT_BASELINE.md).

## Foundation and compatibility surfaces

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

## Feature-local inventory

These components deliberately retain domain responsibility. The shell/primitive
column above identifies what they reuse instead of recreating it.

| Feature / component | Location | Purpose and main inputs | Consumers / boundary |
|---|---|---|---|
| D1 configuration | `assignment/assignment-config.mjs` | scope filters, priorities, resource policy; state + execution callbacks | Config D1; domain rules stay local |
| D1 shell | `assignment/assignment-dashboard-shell.mjs` | exact D1 section markup; Run + Case actions | dashboard router; shared presentation/toolbar/navigation |
| D1 result Hero | `assignment/assignment-summary.mjs` | persisted load/trips/own-fleet values and narrative | D1; shared result summary |
| D1 essential | `assignment/assignment-essential.mjs` | operational KPIs, insights, resources, preview/scenarios | D1 result; persisted evidence |
| D1 advanced | `assignment/assignment-advanced.mjs` | frontier/comparison/utilization/corridors | D1 disclosure; lazy domain charts |
| D1 evidence | `assignment/assignment-evidence.mjs` | vehicle/trip/load evidence and full plan | D1; schema-specific rows |
| D1 filters | `assignment/assignment-filter-collapse.mjs` | native filter disclosure/focus | Config D1 |
| D1 validation | `assignment/assignment-validation.mjs` | consistency/warnings from result | D1 result |
| D1 AI summary | `assignment/assignment-ai-summary.mjs` | saved explanation/evidence and retry | D1 result; shared chat/explanation infrastructure |
| D2 configuration | `scheduling/scheduling-config-v2.mjs` | approved Assignment, window, temporal rules, options | Config D2; scheduling-specific validation |
| D2 rule editor | `scheduling/scheduling-focus-rules.mjs` | rule draft, overlaps/impact, save/cancel | Config D2; shared rule-card primitive |
| D2 shell | `scheduling/scheduling-dashboard-shell.mjs` | exact D2 section markup; Run + Case actions | D2 result; shared presentation/toolbar/navigation |
| D2 essential | `scheduling/scheduling-essential.mjs` | persisted dates/service/KPIs/resources/preview | D2 result; shared result summary |
| D2 timeline | `scheduling/scheduling-timeline.mjs` | dated trips, vehicle occupancy | D2 result; domain calendar |
| D2 advanced | `scheduling/scheduling-advanced.mjs` | full timeline, SLA margins, waits and evidence | D2 disclosure; lazy domain content |
| D2 validation | `scheduling/scheduling-validation.mjs` | unavailable/infeasible/consistency evidence | D2 result |
| D2 AI summary | `scheduling/scheduling-ai-summary.mjs` | persisted explanation and unavailable/retry state | D2 result |
| Data Pack screen | `upload/index.mjs` | typed files, preparation state, four checks, actions | Datos del Case; owner/attributes mounted inside form |
| Dropcard | `upload/dropcard.mjs` | file selection/reuse/upload state | Orders and Fleet; shared typed upload presentation |
| File library | `upload/library.mjs` | typed rows, paging/search, selected file | Orders and Fleet reuse |
| Validation report | `upload/validation-report.mjs` | actual validator findings and downloadable report | Data screen; not engine optimization |
| Preflight | `upload/preflight-panel.mjs` | server readiness, relations and warnings | Data screen |
| CSV guide | `upload/guide-drawer.mjs` | backend contracts/templates and focus lifecycle | Data screen |
| Availability banner | `upload/system-banner.mjs` | actual backend activation/connectivity state | Data screen |
| Traceability dialogs | `traceability-ui.mjs` | bounded Run history and legacy Case chooser data/callbacks | history/compatibility; distinct from removed recent-Case dropdown |
| Historical dashboard | `dashboard.mjs`, `hero.mjs`, `assignment/assignment.mjs`, `review.mjs` | dispatch/logistics historical result schemas | retained compatibility, not new D1/D2 shells |
| Home | `../platform/home.mjs` | authorized recent work, attention and catalog | platform Home |
| Decision Center | `../platform/decision-center.mjs`, `decision-center-actions.mjs` | resource filters, detail, owner/archive actions | global portfolio; checked platform API |
| Data Hub | `../platform/data-hub.mjs`, `data-resource.mjs` | typed library, detail, packs, persisted resource | global data management |
| Team | `../platform/team.mjs`, `invitations.mjs` | membership/roles/invitations and optimistic versions | Team/settings/Auth invitation entry |
| Workspace settings | `../platform/workspace-settings.mjs`, `settings-resource.mjs` | workspace preferences, free plan, resource tab | workspace settings |
| Profile | `../platform/shell.mjs` | current identity form, version-independent profile API, identity refresh | authenticated profile view |
| Activity | `../platform/activity.mjs` | actual audited events and exports | activity surfaces / Case detail |
| Onboarding | `../platform/onboarding.mjs` | real exploration/demo state and callbacks | Home/settings; existing workflow entry |
| Auth/session/shell | `../platform/auth-page.mjs`, `session.js`, `shell.mjs` | verified identity, refresh/session isolation and route mounting | application boundary; never feature-owned auth |

The baseline machine inventory also records every named module export, Python
definition and file size in `dation-audit/foundation/baseline/inventory.json` in the
execution artifacts. The table maps those technical modules to product concepts;
it does not promote every exported selector/helper into a shared UI component.

UI colors, spacing, radii, typography, action heights and status tokens remain in
`static/css/tokens.css`; action/card patterns in `dation-design-system.css`;
Case Context/execution/result text patterns in `workflow-context.css`. Preserve
stylesheet order and selector hooks when extending these components.
