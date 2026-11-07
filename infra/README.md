# Infrastructure

Infrastructure notes and deployment configuration for Dation.

## Current delivery

`GitHub main → Google Cloud Build → Artifact Registry → Cloud Run Worker → Cloud Run API`.

Cloud Build owns the existing external trigger. The root `Dockerfile` builds the
shared API/worker image; `.github/workflows/backend-tests.yml` runs CI separately.
No Cloud Build trigger configuration is checked into this repository. See the
[current deployment guide](../backend/DEPLOYMENT.md) and
[master baseline](../docs/MASTER_DEVELOPMENT_BASELINE.md).

Manual `GCP_ACCESS_TOKEN` / `GCP_ROLLOUT_ACCESS_TOKEN` bindings in Codex are not
dependencies of this delivery path. Keep operational credentials out of Git.

## MVP services

- Google Cloud Run: Python/FastAPI compute.
- Google Cloud Build: build and deploy from GitHub.
- Google Secret Manager: backend secrets.
- Supabase: PostgreSQL and private object storage.

No infrastructure-as-code is required for the first MVP milestone. Terraform or
similar tooling can be introduced after the deployment model stabilizes.
