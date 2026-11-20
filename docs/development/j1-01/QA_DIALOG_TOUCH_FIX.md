# Final focal accessibility correction

A separate real-browser measurement found that the new model dirty-exit dialog
inherited 40 px platform buttons at 375 px. The shell screenshots had validated
44 px actions, but had not measured this transient dialog. This was a J1.01 QA
coverage gap, not a business/navigation regression.

Correction: include `.d-modal__actions` in the existing **library-scoped** 44 px
shell rule. No global design-system, R6 form geometry or dialog logic changes.
New browser test `ModelLibraryTests.test_12_dirty_dialog_touch_targets_at_every_viewport`
measures all three actions at 1440/1280/768/375, checks dialog overflow, records real
screenshots and verifies Escape preserves the draft.

The intermediate run `44828992939` at `45e6fd8a2ae44c44b5b5b2da74ef3cf95c4b6f32`
had passed automated Python/Node checks and was in browser regression. It was
cancelled because its candidate was being replaced, not reported as green. The
unchanged R3 classifier requires final FULL CI on the corrected head.

Evidence: `dialog-touch-red.txt`, `dialog-touch-green.txt`, `dialog-geometry.json`
and the four `dialog-*.png` under `evidence/`. This adds a thirteenth J1.01 browser
test; it does not remove or relax any assertion.
