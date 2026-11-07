# Runtime V2 infrastructure

Current target: **dation-runtime-v2-2026 / 332279365872 / us-west1**.
Canonical identity: `backend/app/cloud_identity.py`. Billing OFF; no deployment.

```sh
python scripts/zero_idle_release.py validate
python scripts/zero_idle_release.py plan
python scripts/runtime_v2_readonly.py
```

The first two commands validate/generate offline proposals only. The last prints
the scoped GET plan; `--cloud-shell` performs those reads using the owner's
existing login without printing credentials or enabling APIs.

`zero-idle/release.json` and generated `prepared-manifests.json` prepare the API,
two finite Jobs, distinct runtime/Scheduler accounts, resource-scoped IAM and
versioned Secret Manager references. Secret values are never included. Proposed
accounts/versions are not live inventory; image digest/release SHA must be resolved
and reviewed after authorization. Scheduler is disabled/not created by default;
creation can schedule immediately, so it requires its own activation GO.

No automatic Cloud Build/deployment trigger is created. Every deployment script
keeps its existing hard hold, even with an authorization flag. The retired
project is outside the scope of the current tools and activation.

[Activation, login, Supabase and rollback](../docs/runtime-v2/activation-runbook.md)
· [Access/read-only inventory](../docs/runtime-v2/readonly-and-access.md)
· [Costs](../docs/runtime-v2/costs.md).
