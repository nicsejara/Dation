# Naming conventions

Use product concepts where they disambiguate a boundary. Keep short local names
when the enclosing function already establishes the concept. Do not mechanically
rename `data`, `state`, `result` or `execution` across unrelated domains.

| Use | Avoid / compatibility exception |
|---|---|
| Decision Case / `decisionCase`, `case_id` | new `DC` abbreviations; retain displayed `DC-…` IDs |
| Decision / `nodeId`, `node_id` | calling a node a Run; node keys are existing API contracts |
| Decision Run / `runId`, `run_id` | interchangeable execution/result IDs |
| Decision Result / `result_json` | treating a dashboard as calculation authority |
| Data Owner | new operational Data Steward names; SQL aliases remain readable |
| Decision Owner | new independent executor/approver assignments |
| actual approval actor / `approved_by_user_id` | replacing historical actor with currently assigned owner |

JavaScript modules use existing kebab-case names and native named exports. Render
functions begin `render`, mounting/binding functions begin `mount`/`bind` and own
their scope cleanup. Feature-local content stays in its feature directory; shared
helpers require actual callers in multiple features. No hooks/factories framework.

JavaScript uses camelCase, Python snake_case. Existing transport payloads, SQL
signatures, DOM data attributes, CSS classes and session keys retain their formats.
Boolean names should express predicates (`isApproved`, `hasDecisionOwner`) for new
ambiguous APIs, without renaming clear existing status/enabled/hidden fields.
Callbacks remain `onApprove`, `onRerun`, `onOpenNode`; handlers should name their
actual action. A permission boolean is not authorization without backend checks.

Service methods describe operations (`ensure_case`, `approve_run_version`);
pure domain functions describe transformation (`create_case_state`,
`validate_case_state`, `project_case_history`). Pure functions cannot query HTTP,
tenant context or the database. Do not merge historical and current clients solely
because both call `fetch`: their error/response contracts differ.
