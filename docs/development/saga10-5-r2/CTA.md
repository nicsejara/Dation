# CTA audit and state contract

`evidence/cta-audit.json` is captured from the real browser DOM at five widths. It records id, label, visible/disabled, role/type, component, width/height, rightGap and coverage reference. `geometry.json` compares the five confirmation CTAs (same class/tokens) and the two toolbar buttons, with 1 px maximum tolerance. Hidden/disabled actions are recorded, not asserted to be operable.

| Action | Effect / guards | Verification |
|---|---|---|
| Select existing | Opens verified version picker; preserves new draft; disabled for pending publication/locked context; no implicit publish. | Legacy wizard version/cancel/viewer tests; Saga01 recurrent tests. |
| Create new | Returns to retained draft from published selection; focuses current draft if already editing. Disabled while publishing, pending intent or locked; hidden for non-admin. | Legacy create-another/reuse/draft regressions (label updated only). |
| Confirm identity / operation / resources / money | Local review signature only. Invalid data exposes error/focus; edits invalidate applicable confirmation. Never API create/publish. | Ultimate 01/02/06; guided missing-sources regression. |
| Confirm cargo | Only current successful parent preview can enable it. Local confirmation only; pending/stale/error cannot unlock global publication. Double-click does not trigger preview/create. | Ultimate 01/06/07. |
| Global save/publish and retry | Existing explicit Model + Version intent, idempotent IDs, expected revision/CAS and lost-ACK recovery retained. | Legacy wizard 12 tests; Saga10 publish/data contract regressions. |
| Compatible editor | Explicit confirmation before preserving draft and opening advanced contract editor. Cancel leaves current state unchanged; never converts published snapshots. | Guided helper public flow; old guided mode preservation tests. |
| Add unit / presentation / product | Adds a new blank object with unique ID, not a completed example; respects limits and actual references. New guided presentations have one component. | Ultimate 01/04/07; guided boundary test09. |
| Select support / presentation / product | Uses real catalog IDs. A support can serve multiple homogeneous presentations; selecting a shared product locks editing until duplication. | Ultimate 04/07; guided ID regressions. |
| Change support type | Confirm first; cancel restores prior choice; preserves physical data and references for explicit reconciliation. | Ultimate 03. |
| Duplicate product / support / presentation | Creates new IDs, safe labels/code and explicit selection; preserves source. Shared product cannot be mutated through another presentation. | Ultimate 07; guided 04/10. |
| Delete presentation | Modal Cancel/accept; cancel keeps identity/data; published versions never affected. | Ultimate 07. |
| Delete referenced product/support | Disabled with dependency explanation; compatible editor can reassign before deletion. | Ultimate 07; previous guided tests04/10, wizard test01. |
| Co-load pairs / categories | Explicit policy controls retained; hidden controls disabled; no silent uniformity. | Previous guided test10; physical compiler contract tests. |
| Compatible search/filter/edit panels | UI navigation only, allowed for published viewing. Search is the only enabled input in the immutable catalog fixture; no payload mutation. | Previous guided product test04; Ultimate 04 explicitly checks all mutable inputs disabled. |
| Enter in model text input | Does not submit the containing Case form or publish a model. Textareas/native radio keyboard semantics retained. | Ultimate 06; geometry/keyboard test05. |
| Retry contract | Existing parent preview only; preserves all fields; errors reached by a button focus the validation region. | Ultimate 06; guided 08; Saga01 contract-failure test07. |

Five local CTAs use one footer helper, one selector and one geometry token set. Top Create/Select are sibling buttons of equal dimensions. Only global publish writes Model/Version. No redundant Change Model button, no internal Back/Continue in the three-step view, no intermediate check or cargo-review checkbox there. Historical compatible editor preserves its old seven-step contract explicitly.
