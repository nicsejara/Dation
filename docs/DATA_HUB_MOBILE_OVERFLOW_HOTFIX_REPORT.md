# Data Hub mobile overflow hotfix

## Scope and baseline

This is a separate post-merge hotfix on `hotfix/data-hub-mobile-overflow`,
based on `main` at `fbc2a9986aefebcfd2784ea00207bfb65f6abad8`.
Saga 01 remains integrated; its implementation and report are unchanged.
Only the affected Data Hub browser journey and this report change.

[Main run 42052751164](https://github.com/nicsejara/Dation/actions/runs/42052751164)
passed Python, Node, browser and SQL. Its E2E stage executed 121 methods:
120 passed and only the Data Hub real-browser journey failed. At 390 px,
the theme probe reported `overflow: true`, with no contrast failures.

## Evidence and classification

The original diagnostic artifact is `13432666502`. Its Data Hub screenshots
and summaries were extracted without rerunning tests in
[read-only diagnostic run 42126490886](https://github.com/nicsejara/Dation/actions/runs/42126490886),
artifact `13462205164`. That diagnostic branch is outside this hotfix.
The original 390 px full-page screenshot is 1,130 px wide, with a 390 px
drawer and a large empty region to the right. The 768 px screenshot fits.

One unchanged local journey passed in 54.252 seconds. Three subsequent
focused repetitions all reproduced the 390 px overflow in 58.997 seconds.
Failure geometry showed a 390 px viewport/document client width but a
1,130 px document scroll width: the background table retained its desktop
`min-width: 1040px` at x=90 while responsive layout was changing.

A further diagnostic run still failed the original assertion (105.532
seconds), but the immediate following measurement already showed a 390 px
document, a 298 px table with `min-width: 0px`, and a 390 px drawer. Three
following animation frames preserved those dimensions. No CSS changed.
This identifies a test synchronization problem during responsive style
application; no persistent Data Hub layout defect was demonstrated.

## Correction

The journey replaces its fixed two-animation-frame wait with an explicit
condition: the CSS media query must match the requested viewport, the table
must have its expected desktop/mobile display mode, and mobile must have
applied its zero minimum width. It then performs the original independent
overflow and contrast audit at all five widths: 1440, 1280, 1024, 768, 390.

The condition never waits for `overflow == false`. Persistent unexpected
overflow still fails the original assertion; a broken responsive CSS mode
fails the readiness condition. No timeout increases, arbitrary sleeps,
business-operation retries, skips, forced clicks or product CSS changes
were introduced. Failure-only JSON geometry and reload diagnostics preserve
future evidence without converting failures to successful results.

Upload/fork persistence, original/fork immutability, dataset reference guards,
archive/restore, actual download bytes, XSS protection and safe deletion
remain asserted. D1/D2 and their navigation/approval rules are untouched.

## Focused validation

Run from `backend`, using the repository's isolated Docker/PostgreSQL/API/
worker/Storage fixtures; inherited production credentials are cleared by
the sandbox. The affected journey repeated three times uses:

```sh
hub_case_test=test_data_hub.DataHubTests.test_06_real_browser_dda_upload_library_lineage_download_and_safe_delete
DATION_E2E_ARTIFACTS=/tmp/dation-hub-focus \
  ../.venv/bin/python tests/e2e/run_suite.py \
  --module "$hub_case_test" --module "$hub_case_test" --module "$hub_case_test"
```

The first corrected batch had two complete passes and one timeout waiting
for the table after the final reload; all three passed the overflow audit.
The next batch had two complete passes and one fixture HTTP 503 while
uploading the unused dataset, before browser execution. Thus five reached
and passed the corrected visual audit, with four complete passes. These
two additional local failures are recorded separately and are not counted
as successful journeys or used to change authentication/product behavior.

Related Data Hub controls use:

```sh
DATION_E2E_ARTIFACTS=/tmp/dation-hub-class \
  ../.venv/bin/python tests/e2e/run_suite.py --module test_data_hub
```

The complete Data Hub class passed locally: 11 methods in 64.636 seconds,
with no failures, errors or skips, including the corrected real-browser
journey and its final reload. This does not erase the earlier local failures.

The [remote focused check 42128412988](https://github.com/nicsejara/Dation/actions/runs/42128412988)
passed all three repetitions in 60.021 seconds, with no failures, errors or
skips. It checked out hotfix code at `9340da9244b31b48023d70f6bf62a7529fbfe2a8`
and used Python 3.13 plus the required CI's hash-pinned Playwright and Chrome
for Testing 153.0.8010.12 (Chromium revision 1243). The complete original
journey passed, including mobile audit, library operations and final reload.
The isolated diagnostic workflow is outside this hotfix's diff/history.

The complete required candidate gate remains unchanged and must approve
before integration. The hotfix PR records its run link, tested SHA,
integrated `main` SHA and final post-merge check state; this avoids a further
documentation-only push after validating the candidate.

## Operations boundary

GCP Billing remains intentionally disabled. No manual Cloud Build, image
publication, Cloud Run deployment/configuration or production test is run.
Supabase production is unchanged. Any automatic post-merge GCP check is
observed only and reported without retries or Billing activation.
Saga 02 / Zero-Idle-Cost remains a separate task.
