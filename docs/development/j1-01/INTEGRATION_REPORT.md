# J1.01 integration evidence

This repository evidence is part of the immutable candidate. **Final PR number,
validated head SHA, GitHub run ID, terminal FAST/FULL/required-gate results and
completion time are recorded in the associated PR description after CI**. Updating
the candidate merely to embed its own CI result would change the validated SHA
and require another full run. No such circular validation is used.

J101-078 is PASS: PR #133 is open on the dedicated branch with no conflicts or
automerge. J101-080 (actual terminal CI) remains PENDING in the committed matrix
until resolved by the final PR report at the same head SHA. A local result never implies CI_GREEN.

## Candidate scope

- Base main: `894f2fa46469ae9b040a550ecca357398c3171f3`.
- Runtime implementation commit: `90f239a0e5bebd0200c63b714f1abbaba151a1af`.
- Branch: `feat/j1-01-models-library`; one PR to main, **NOT_MERGED**.
- Final dialog touch correction: [measured cause and test](QA_DIALOG_TOUCH_FIX.md).
- Focused pre-existing import-graph repair: [cause/evidence](CI_IMPORT_GRAPH_FIX.md).
- Risk: **R3**, unmodified classifier; FULL CI mandatory.
- G0 started 2026-11-20 18:34:59 America/Buenos_Aires.
- Integrated J1.01 browser: **12/12 PASS in 84.317 s**; final dialog target + dirty guard **2/2 PASS in 21.370 s**, bringing J1.01 coverage to 13 cases.
- Existing R6 browser: **9/9 cases PASS** (see combined-run caveat in test report).
- Model SQL: **25/25 PASS in 24.026 s**.
- Saga10 physical/Data Contract/D1/D2 consumers: **59/59 PASS in 2.425 s**.
- Backend capability/contracts: **19/19 PASS**.
- Pure state/controller/session: **4 + 4 + 2 PASS**; existing router tests PASS.
- Static checks and unchanged impact-classifier tests PASS.
- Screenshots: 24 original PNGs, six scenes at 1440/1280/768/375.

## Protected boundaries

No migration or production operation. No backend business contract change beyond
the additive default-off capability. No engine, physical calculation, SQL,
Supabase, IAM, Cloud Run, Billing, Scheduler, Jobs or workflow modifications.
Existing Case/Graph navigation and exact published pins remain intact. Browser
lock/recovery and mutation intents are scoped independently of Case drafts.

## Residual limits

Incomplete drafts are browser-local, cleared intentionally at logout/identity
change, and do not sync devices. A compatible browser with Web Locks is required
for editing. Unknown publication outcomes retain their original intent; a real
revision conflict needs deliberate reconciliation, never a blind new UUID.
List changes during pagination request a refresh rather than hiding missing rows.
Preview flag stays closed for ordinary traffic. J1.02/J1.03 are not implemented.

## Final declaration rule

Only the actual successful required checks of the PR head permit
`CODE_READY — CI_GREEN — NOT_MERGED — NOT_DEPLOYED`. A failing or pending check
keeps that declaration blocked. PR final report is the authoritative closure of
the two external criteria and contains the actual elapsed duration.
