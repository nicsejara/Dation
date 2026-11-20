# J1.01 — Real browser evidence

Actual application, synthetic authenticated local API/PostgreSQL fixtures. These are not the supplied offline prototype. Original PNG bytes are preserved. Geometry JSON records viewport, scroll width, control targets and card placement.

| Scene | 1440 | 1280 | 768 | 375 |
|---|---|---|---|---|
| library | [1440](evidence/library-1440.png) | [1280](evidence/library-1280.png) | [768](evidence/library-768.png) | [375](evidence/library-375.png) |
| editor | [1440](evidence/editor-1440.png) | [1280](evidence/editor-1280.png) | [768](evidence/editor-768.png) | [375](evidence/editor-375.png) |
| review | [1440](evidence/review-1440.png) | [1280](evidence/review-1280.png) | [768](evidence/review-768.png) | [375](evidence/review-375.png) |
| history | [1440](evidence/history-1440.png) | [1280](evidence/history-1280.png) | [768](evidence/history-768.png) | [375](evidence/history-375.png) |
| error | [1440](evidence/error-1440.png) | [1280](evidence/error-1280.png) | [768](evidence/error-768.png) | [375](evidence/error-375.png) |
| dialog | [1440](evidence/dialog-1440.png) | [1280](evidence/dialog-1280.png) | [768](evidence/dialog-768.png) | [375](evidence/dialog-375.png) |

All six scenes: zero document overflow at each width; visible controls ≥44 px. Library is two columns at 1440, one at 375. [Integrity IDs/hashes](evidence/version-integrity.json) prove actual synthetic versions and pinned Case invariance.

The editor and Review reuse R6. Mobile screenshots are long full-page captures of real forms; they were not composited, edited or replaced with mockups.

Text evidence normalization removes trailing whitespace only. SHA-256 inventory: [SHA256SUMS](evidence/SHA256SUMS).
