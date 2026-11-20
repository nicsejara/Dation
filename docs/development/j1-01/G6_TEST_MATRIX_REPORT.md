# J1.01 — Verification index

All runtime tests use synthetic data and owned loopback API/Auth/Storage/PostgreSQL
fixtures. No production query, write, migration, engine activation or deployment.
Actual terminal candidate CI is recorded in `INTEGRATION_REPORT.md` and PR checks;
local PASS does not substitute for GitHub CI.

## Evidence identifiers

| ID | Test / evidence | Contract |
|---|---|---|
| B01 | `ModelLibraryTests.test_01_incomplete_drafts_are_independent_durable_and_never_create_cases` | Multiple isolated browser drafts, reload, second tab, no model/Case writes |
| B02 | `...test_02_publish_two_models_review_history_successor_and_pinned_case` | A/B, real v1/v2/hash, pinned Case/pack/run invariance, History, no auto-selection |
| B03 | `...test_03_dirty_back_cancel_discard_and_reload` | Dirty browser Back, cancellation, discard/checkpoint recovery |
| B04 | `...test_04_get_error_is_not_empty_and_exact_version_never_falls_back` | Error/retry, legacy read, missing exact version, zero writes in Review |
| B05 | `...test_05_core_return_preserves_draft_candidate_graph_and_read_only_permissions` | Core draft attributes/candidate, viewer controls, forced API writes and tenant isolation |
| B06 | `...test_06_real_library_editor_review_history_errors_responsive_and_keyboard` | Five real scenes × four widths, touch geometry, focus, keyboard dialog, search |
| B07 | `...test_07_real_pagination_search_archive_and_non_mutating_history_back` | 51 API-created families, pages 25/25/1, archive and exact History, Back/Forward no writes |
| B08 | `...test_08_two_tabs_server_cas_preserves_local_copy_and_requires_explicit_reload` | Concurrent model drafts, server 409, copy retained, explicit reload |
| B09 | `...test_09_lost_publish_response_recovers_same_intent_without_second_version` | Real server commit + aborted response, exact UUID retry, only one version |
| B10 | `...test_10_graph_pinned_review_library_v2_and_return_keep_original_resources` | Graph/Core pinned v1 → Library v2 → pinned v1/Graph, no resource mutation, static header focus |
| B11 | `...test_11_same_working_copy_is_locked_across_tabs_without_losing_recovery` | Browser lock protects same copy; release permits later recovery |
| B12 | `DefaultLibraryGateTests.test_default_closed_retains_legacy_library_and_rejects_new_mode_links` | Real default-closed route and legacy compatibility |
| U01 | `tests/test_model_library_state.mjs` | 4 pure identity/storage/route/return invariants |
| U02 | `tests/test_model_library_controller.mjs` | 4 mutation/replay/CAS/advanced-create-revision invariants |
| U03 | `tests/test_model_library_session.mjs` | 2 fresh-tab/authenticated scope/logout clearing VM tests |
| U04 | `tests.test_model_library_gate`, `tests.test_ultimate_case_models` | 19 backend capability and existing contract tests |
| SQL | `tests.integration.test_ultimate_case_models.UltimateCaseSQLTests` | 25 real SQL permission, locking, immutable snapshot, archive and Case invariants |
| R6 | `test_saga10_5_r6.R6Tests` | 9 existing geometry, physics, confirmations, historical/Case Review and navigation cases |
| DOMAIN | Six `tests.test_saga10_*` modules | 59 physical/domain/Data Contract/D1/D2 consumer regressions |
| NAV | `tests/test_navigation.mjs` | Existing resource/router invariants |
| IMPACT | `tests/operations/test_rapid_impact.py`, `evidence/impact.json` | Classifier unchanged, R3 / FULL required |
| STATIC | `scripts/ci/static_check.py` | Changed JS/Python/CSS/JSON checked using existing checker |

Browser tests live in
[`backend/tests/browser/test_model_library_j101.py`](../../../backend/tests/browser/test_model_library_j101.py)
(repository path; evidence IDs above identify complete method names).
Logs and original PNG/geometry outputs are indexed by [VISUALS](VISUALS.md).

## Commands

Run from `backend` using the existing isolated dependencies:

```bash
python -m unittest tests.test_model_library_gate tests.test_ultimate_case_models -v
node tests/test_model_library_state.mjs
node tests/test_model_library_controller.mjs
node tests/test_model_library_session.mjs
node tests/test_navigation.mjs
python -m unittest tests.test_saga10_domain_physical tests.test_saga10_assignment tests.test_saga10_scheduling tests.test_saga10_data_contracts tests.test_saga10_industries tests.test_saga10_result_consumers -v
.browser-venv/bin/python -m unittest discover -s tests/browser -p test_model_library_j101.py -v
```

Use the repository's owned PostgreSQL 17 integration harness for SQL; never point
its container variable at foreign infrastructure. Actual local commands used the
existing shared Python/Chromium installations, recorded in the evidence logs.
CI uses the unmodified checked-in workflows and creates its own fixtures.

## Corrections established by evidence

- Fresh-tab session cleanup originally deleted durable model copies. Exact
  authenticated prefix preservation fixes recovery; logout/identity clearing is
  explicitly tested. No token handling or permissions were broadened.
- Initial status select had no matching default; setting `all` fixes an empty
  filtered list despite real returned rows.
- Base platform button specificity overrode the new footer touch target. Scoped
  shell controls now measure at least 44 px; R6 internal button rules are retained.
- An initial fixture used non-existent table/constant names and the older picker
  helper tried a deliberately hidden R6 version select. Corrected test setup uses
  real schema/API and visible current R6 actions; no business assertion removed.
- The first combined R6 run passed all nine R6 tests but its new Graph scenario
  lacked a test helper. The final J1.01 run includes the corrected real Graph
  scenario. Do not report that earlier combined command as an overall PASS.

Published Case context deliberately includes mutable family metadata. Integrity
checks assert the Case, exact model version/hash, pack, responsibilities and run
resources; they do not claim the family's name/revision cannot change on a new
draft. The full original v1 snapshot is compared byte-for-value after v2.
