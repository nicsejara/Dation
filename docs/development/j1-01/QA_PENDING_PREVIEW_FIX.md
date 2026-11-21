# Pending mutation / late preview regression

A focused latency test against the real API reproduced a J1.01 synchronization
defect: a delayed contract-preview response could call the shared R6 field
renderer while model Save was pending and re-enable 29 controls. The mutation
intent stayed fixed, so edits made through those re-enabled controls would not
belong to the submitted snapshot. This was a frontend state regression, not a
backend, physics, authorization or persisted-version defect.

Minimal correction in the library wrapper only:

- Ignore preview success **and error** callbacks during a busy/pending mutation.
- Keep the form frozen until the exact Save intent resolves.
- Revalidate after a local-only save when compilation is still needed. A server
  save remounts its canonical working copy and validates there as before.

No changes to R6 field implementations, API contracts, SQL, engines or workflows.
The new real-browser regression holds actual preview/save responses, tests both
success and 503 preview outcomes, requires zero enabled form controls while Save
is pending, then verifies the server-acknowledged name after release. No sleeps,
assertion relaxation or mutation retries are introduced.

`ModelLibraryTests.test_13_late_preview_success_or_error_cannot_unlock_a_pending_save`
adds a fourteenth J1.01 case. Evidence: `pending-preview-red.txt`,
`pending-preview-green.txt`, `pending-save-preview.json`, and the final integrated
J1.01 browser log under `evidence/`.

Run `44832136047` at `07a2d0b6ec52b7b8cb20cead0682d3643d808273` had passed
Python/Node, browser regression and PostgreSQL validation. It was cancelled during
the final E2E block after the defect was reproduced, because its candidate had to
be replaced. It is not reported as a terminal green run. Final R3 FULL CI must
validate the corrected head.
