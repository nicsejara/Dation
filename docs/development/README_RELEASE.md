# Rapid Release — manual GitHub publish and Cloud Shell activation

No automatic deployment or change of traffic.

## One-time Cloud Shell bootstrap
After the release helper merges into main, obtain a trusted checkout of the
reviewed main commit (do not execute a moving-branch script blindly):

    git clone https://github.com/nicsejara/Dation.git "$HOME/dation-ops"
    cd "$HOME/dation-ops"
    git fetch origin main
    git checkout --detach <TRUSTED_MAIN_SHA>

Future update: git fetch origin main && git checkout --detach <TRUSTED_MAIN_SHA>.

## Development
1. Assistant implements small PR, searches related UI selectors and tests.
2. FAST CI classifies real diff and checks selected tests; R3/R4 run FULL.
3. Merge only with the exact required gate green. Check the merged main
   SHA itself gets a successful required-gate.

## Image publication
In GitHub Actions run workflow Runtime V2 - manual Gate C image publication,
branch main. Enter exact full application_sha (40 lowercase hexadecimal
characters) and check confirm_publish. The workflow checks that the exact
SHA is a main ancestor and has the green required-gate; reuses an existing
matching immutable image or builds once. It publishes only Artifact Registry
and produces the gate-c-RUN_ID receipt; it does NOT deploy Cloud Run.
Never blindly retry an ambiguous failed build.

## Cloud Shell fallback — short release controls

    python3 scripts/release/dation_release.py status
    python3 scripts/release/dation_release.py prepare --sha <APP_SHA>
    python3 scripts/release/dation_release.py smoke --sha <APP_SHA>

Smoke checks READY/image/settings passively; it does NOT perform HTTP
revision tests while the revision receives zero traffic. Tagged revision HTTP
smoke would require separate controlled exposure and authorization.

After separate explicit traffic authorization:

    python3 scripts/release/dation_release.py promote --sha <APP_SHA> --confirm PROMOTE_100

Rollback to verified, saved previous revision:

    python3 scripts/release/dation_release.py rollback --sha <APP_SHA> --confirm ROLLBACK_100

The helper uses private per-SHA local receipts in HOME/.dation-releases-v2.
Interrupted prepare is recoverable only when the exact digest can be identified;
no repeated build/deploy or silent reassignment of a different revision.

## Scope and honest limitations
- Fixed Runtime V2 project dation-runtime-v2-2026 / us-west1 / dation-core.
- Autoscaling must remain min 0 / max 1–2; the helper checks identity/config.
- Cloud Run and registry can generate usage charges within or beyond free tier.
- No Cloud Build, Scheduler, Jobs, Supabase or Billing changes.
- GitHub Actions receipts remain in its artifacts; the minimal Cloud Shell
  helper verifies registry tag/digest but does not authenticate an Actions
  receipt artifact cryptographically. Close this gap before claiming
  end-to-end receipt attestation.