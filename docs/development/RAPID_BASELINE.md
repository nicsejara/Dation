# Dation Rapid Development — baseline (2026-11-13)

Read-only focused baseline:
- Repository nicsejara/Dation; initial main SHA 81512f9cfbb13159ebcda325a9b29a9151c7fbaf.
- Runtime V2, dation-runtime-v2-2026, us-west1, dation-core; owner-reported live revision dation-core-00002-m4z with 100% traffic.
- Prior backend-tests.yml ran Python, Node, Chromium, Docker, PostgreSQL and full E2E for every PR.
- Prior runtime-v2-publish.yml was pinned to a single application SHA.
- This branch is repository-only: no writes to GCP, Billing, IAM, Cloud Build, Supabase, Jobs or engines.

## Risk policy
R0 docs => FAST.
R1 isolated CSS => FAST/static structure.
R2 JS/DOM/forms/navigation => FAST plus targeted browser/API smoke.
R3 backend/data/auth/SQL => FAST and FULL.
R4 workflows/release/security/dependencies => FAST and FULL.

Unknown or mixed paths elevate risk; consult tests/impact-map.json and
scripts/ci/impact.py. The required-gate job reports PASS only if its FAST
and necessary FULL dependencies pass. Repository changes cannot by themselves
enable branch protection; enforce the published required check in GitHub
Settings before treating checks as mandatory for all writers.

## Limits
The initial workflow-changing PR may incur the old FULL CI once. Browser
fixture requires isolated local PostgreSQL/Docker on the runner. The release
helper tests revision READY passively, not HTTP through a tagged revision.
Production authorization remains separate.