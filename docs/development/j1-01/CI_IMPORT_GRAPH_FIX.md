# Focused CI repair — pre-existing baseline failure

Initial candidate `77b9f1fd7837a29417a90a65293ebba4a82f94a8`, run
[`44827087749`](https://github.com/nicsejara/Dation/actions/runs/44827087749):
impact/FAST passed; FULL stopped at Python regression (782 tests, one failure).
`test_frontend_import_graph.FrontendImportGraphTests` found exactly two unreachable
production modules: `cargo-editor.mjs` and `model-editor-mode.mjs`.

The same test was reproduced against an archive of exact baseline
`894f2fa46469ae9b040a550ecca357398c3171f3`, including all referenced template/static
dependencies. It failed on the same two files. Their bytes were unchanged by
J1.01. This is a **pre-existing obsolete-module defect**, not a new navigation,
physics or persistence regression and not a weaker-test opportunity.

Source/reference inspection found no imports, module URL consumers or test uses
of their exports. R6 uses `cargo-guided-editor`, `cargo-guided-state`, volume
coherence and the human historical projection. The old modules only exported
unused implementations; they did not register global runtime behavior.

Minimal repair: remove precisely those two unreachable modules. Do not add fake
side-effect imports or exceptions to the graph test. Do not change that test or
restore the retired technical editor. No other cleanup/refactor is included.

Re-run the focal import-graph test, then new publication/pinned-return and legacy
entry browser controls. The unchanged classifier still requires FULL on the
corrected PR head. The prior failed run remains reported, not overwritten as green.

Logs: `evidence/import-graph-baseline-red.txt`,
`evidence/import-graph-candidate-red.txt`, `evidence/import-graph-green.txt`, and
`evidence/import-fix-browser.txt`. Final run/SHA belong to the final PR report.
