# Infrastructure

Infrastructure notes and deployment configuration for Dation.

## MVP services

- Google Cloud Run: Python/FastAPI compute.
- Google Cloud Build: build and deploy from GitHub.
- Google Secret Manager: backend secrets.
- Supabase: PostgreSQL and private object storage.

No infrastructure-as-code is required for the first MVP milestone. Terraform or
similar tooling can be introduced after the deployment model stabilizes.
