# Manual activation and rollback — not executed

This PR requires review and separate owner GO to merge. No image publication, Cloud Run operation, Supabase change or engine activation belongs to implementation.

1. Verify final PR head and actual required-gate success. Obtain explicit merge GO; verify main CI after merge.
2. Recompute the real UX autopilot policy. This diff includes cargo-editor/model-fields-v2/guided-ui/wizard-ui, outside the allowlist: **NO_AUTO_DEPLOY**. Do not expand policy to bypass this restriction.
3. With separate publication GO, use the current `runtime-v2-publish.yml` workflow manually on main, fixed integrated application_sha and confirm_publish=true. Record run, receipt and immutable digest. Do not reuse a moving ref or rebuild blindly.
4. Follow `docs/development/README_RELEASE.md` and `scripts/release/dation_release.py` current interfaces for status, prepare and passive smoke. Save previous revision/digest first. Smoke does not prove real login.
5. Obtain traffic GO, promote approved revision, check login and five blocks; test new homogeneous data, historical direct and catalog versions, draft reload and generated two/three CSV contracts.
6. Keep scale-to-zero, Scheduler OFF and production engines disabled. No SQL migration is required.

Rollback: obtain explicit rollback GO and restore the recorded previous compatible Saga10/10.5 revision/digest using the existing helper and required confirmation. Never roll back to a pre-Saga10 reader if V2 models exist. No database reset/down migration/deletion. Recheck login, immutable models, drafts and Data Contract. If publication partially succeeds, reconcile receipts/revisions rather than rerunning blindly.

Future read-only reverse review is independent of technical rollback and is only documented in FUTURE_REVIEW_ONLY.md.
