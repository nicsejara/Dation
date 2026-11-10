# Runtime V2: Gate C por GitHub Actions manual, después D/E

Estado: implementación propuesta por PR; **WIF/IAM, merge y dispatch pendientes de autorización específica**. No se aplicó configuración live desde este PR. Gate A y B permanecen PASS; migración remota `20261109215204`, no reaplicar. La imagen contiene exclusivamente `792470ff8cce54cb32b81240b206fdbcb7078ea2`; el commit del workflow/control es distinto y queda registrado por separado. No se modifican motores, UX ni el workflow de regresión.

## Única ruta de publicación

`.github/workflows/runtime-v2-publish.yml` sólo admite `workflow_dispatch`, confirmación explícita y rama main. No `push`, `pull_request`, workflow_run, cron, auto-deploy ni Cloud Build. Su Docker build reutiliza el Dockerfile y contexto de la CI existente; `--require-hashes`/pip check del Dockerfile se conservan. Añade AMD64, etiqueta revision exacta, imagen ≤ 2 GiB, pip check e imports sin red/1CPU/512MiB. Un solo build de hasta 20 minutos, job de hasta 30 minutos, concurrencia exclusiva sin cancelar la ejecución activa.

Control y aplicación se descargan a carpetas separadas. Auth OIDC no crea archivo de credenciales Google; el login de Artifact Registry guarda únicamente un access token efímero en RUNNER_TEMP fuera del contexto Docker y de los artefactos, eliminado siempre al terminar. Ningún secreto Supabase entra al runner ni a la imagen.

El publicador canónico es `scripts/runtime_v2_publication.py`; no se requiere ningún script de los intentos Cloud Shell anteriores. Comprueba el tag exacto y versiones de dation-core con respuestas JSON; 401/403/error ambiguo nunca significan ausencia. Si encuentra una única versión válida, la verifica y reutiliza sin reconstruir; varias versiones o identidad distinta producen NO-GO. Si no hay imagen, el historial de pasos de Actions impide otro build cuando un intento anterior ya alcanzó el paso de construcción. Las ejecuciones que fallaron antes de ese paso pueden volver a despacharse después del diagnóstico; no usar Re-run (run_attempt>1 se rechaza). Historial inaccesible/incompleto: NO-GO. No borrar historial para saltar el control.

El manifiesto se publica por digest con crane 0.22.1 fijado por checksum oficial, después se crea el tagSHA mediante tags.create atómico. No PATCH ni sobrescritura, incluso si otro actor crea el tag durante el build. Un fallo posterior a la publicación puede recuperarse con otro dispatch que verifica la versión existente y completa tag/recibo sin construir otra imagen.

Artefacto `gate-c-RUN_ID`, retención de 30 días: `GATE_C_RECEIPT.json`, estado sanitizado y manifiestos finales de API/Jobs/rol. Sin credenciales, imagen.tar, configs Docker ni binarios. PASS exige digest remoto, config-ID idéntico al verificado localmente, AMD64, revisión y dependencias/imports correctos. Registrar por separado SHA de aplicación y SHA del workflow.

## Trust propuesto e IAM mínimo — requiere GO nuevo

Pool dedicado `dation-github-publish`, provider `github-main-manual`, issuer GitHub oficial, audiencia exacta del provider. Subject Google = `assertion.repository_id` (ID inmutable 1114679650). El binding de la cuenta usa `principal://…/subject/1114679650`, no un pool completo. El provider exige simultáneamente nombre+ID del repo, owner ID 249153366, main, workflow_dispatch, sub de rama y ruta exacta del workflow. Una bifurcación, PR, tag, workflow distinto o repo recreado no cumple el trust.

Cuenta existente `dation-image-builder`: sólo Writer del repositorio dation-runtime. No Editor/Owner/TokenCreator, permisos Run/Jobs/SecretManager ni Cloud Build. El GO propuesto incluye retirar únicamente sus grants obsoletos documentados de logWriter de proyecto y Viewer del bucket fuente de Cloud Build; se preservan bucket/datos y el Cloud Build Service Agent. No se toca runtime/scheduler ni el proyecto anterior. Grants o herencia inesperados detienen la configuración en lugar de ampliarla.

APIs necesarias: IAM ya habilitada; habilitar sólo STS e IAM Credentials si faltan, dentro del GO nuevo. Son APIs de identidad, sin cómputo permanente. No habilitar Cloud Build/Scheduler ni cambiar Billing, cuotas o presupuesto. El bloque verifica Cloud Build OFF sin llamar ni habilitar su API. Una API/lista no verificable no se interpreta como inventario vacío.

## Único bloque Cloud Shell para configurar identidad, sin builds

**Propuesta para aprobación; no ejecutar antes del GO específico.** Tras autorización, establecer `DATION_WIF_GO=GO_RUNTIME_V2_GITHUB_OIDC` en esa sesión y ejecutar este único bloque. Sin esa variable termina antes de cualquier consulta/mutación. Usa el login gcloud del propietario, nunca solicita tokens o claves por chat. Se puede repetir después de un fallo de configuración: verifica/reutiliza sólo recursos que coinciden exactamente; no reemplaza providers inesperados.

```bash
python3 - <<'PY'
import json, os, subprocess, urllib.error, urllib.request
PLAN = {'project': 'dation-runtime-v2-2026', 'project_number': '332279365872', 'region': 'us-west1', 'pool_id': 'dation-github-publish', 'provider_id': 'github-main-manual', 'provider': 'projects/332279365872/locations/global/workloadIdentityPools/dation-github-publish/providers/github-main-manual', 'issuer': 'https://token.actions.githubusercontent.com', 'audience': 'https://iam.googleapis.com/projects/332279365872/locations/global/workloadIdentityPools/dation-github-publish/providers/github-main-manual', 'attribute_mapping': {'google.subject': 'assertion.repository_id'}, 'attribute_condition': "assertion.repository == 'nicsejara/Dation' && assertion.repository_id == '1114679650' && assertion.repository_owner_id == '249153366' && assertion.ref == 'refs/heads/main' && assertion.event_name == 'workflow_dispatch' && assertion.workflow_ref == 'nicsejara/Dation/.github/workflows/runtime-v2-publish.yml@refs/heads/main' && assertion.sub == 'repo:nicsejara/Dation:ref:refs/heads/main'", 'expected_claims': {'repository': 'nicsejara/Dation', 'repository_id': '1114679650', 'repository_owner_id': '249153366', 'ref': 'refs/heads/main', 'event_name': 'workflow_dispatch', 'workflow_ref': 'nicsejara/Dation/.github/workflows/runtime-v2-publish.yml@refs/heads/main', 'sub': 'repo:nicsejara/Dation:ref:refs/heads/main'}, 'service_account': 'dation-image-builder@dation-runtime-v2-2026.iam.gserviceaccount.com', 'principal': 'principal://iam.googleapis.com/projects/332279365872/locations/global/workloadIdentityPools/dation-github-publish/subject/1114679650', 'repository_resource': 'projects/dation-runtime-v2-2026/locations/us-west1/repositories/dation-runtime', 'required_apis': ['iam.googleapis.com', 'iamcredentials.googleapis.com', 'sts.googleapis.com'], 'obsolete_source_bucket': 'dation-runtime-v2-2026-build-src-usw1-332279365872'}

def need(ok, reason):
    if not ok: raise SystemExit('NO_GO: ' + reason)

need(os.environ.get('DATION_WIF_GO') == 'GO_RUNTIME_V2_GITHUB_OIDC',
     'requires explicit owner GO for this exact WIF/IAM plan; no changes performed')
p = PLAN['project']; number = PLAN['project_number']; sa = PLAN['service_account']
member = 'serviceAccount:' + sa

def gc(*args):
    r = subprocess.run(['gcloud', *args, '--project=' + p, '--billing-project=' + p,
        '--quiet', '--format=json'], capture_output=True, text=True)
    need(r.returncode == 0, 'gcloud ' + ' '.join(args[:3]) + ' failed; do not grant Owner/Editor as workaround')
    return json.loads(r.stdout or 'null')

def get(url):
    r = subprocess.run(['gcloud','auth','print-access-token','--project=' + p], capture_output=True, text=True)
    need(r.returncode == 0, 'operator credentials unavailable')
    req = urllib.request.Request(url, headers={'Authorization':'Bearer ' + r.stdout.strip()})
    try:
        with urllib.request.urlopen(req, timeout=30) as response: return json.load(response)
    except urllib.error.HTTPError as error:
        try: detail = json.loads(error.read(65536)).get('error', {})
        except (ValueError, AttributeError): detail = {}
        if error.code == 404 and isinstance(detail,dict) and detail.get('code') == 404:
            if detail.get('status') == 'NOT_FOUND': return None
            if url.startswith('https://storage.googleapis.com/') and any(e.get('reason') == 'notFound' for e in detail.get('errors',[]) if isinstance(e,dict)): return None
        raise SystemExit('NO_GO: targeted read HTTP ' + str(error.code) + '; absence not established')

def grants(policy, who):
    found = [b for b in (policy or {}).get('bindings',[]) if who in b.get('members',[])]
    need(not any(b.get('condition') for b in found), 'unexpected conditional grant; inspect, do not replace')
    return {b['role'] for b in found}

identity = gc('projects','describe',p)
need((identity.get('projectId'),identity.get('projectNumber'),identity.get('lifecycleState')) == (p,number,'ACTIVE'), 'project mismatch')
need(not identity.get('parent'), 'organization/folder inheritance needs targeted review')
services = gc('services','list','--enabled')
enabled = {s.get('config',{}).get('name') for s in services}
need('cloudbuild.googleapis.com' not in enabled, 'Cloud Build must stay OFF; do not change it in this block')
need('iam.googleapis.com' in enabled, 'unexpected IAM API state')
account = gc('iam','service-accounts','describe',sa)
need(account.get('email') == sa and not account.get('disabled',False), 'publisher account missing/disabled')
need(not gc('iam','service-accounts','keys','list','--iam-account=' + sa,'--managed-by=user'), 'unexpected permanent service-account keys')
project_policy = gc('projects','get-iam-policy',p)
project_roles = grants(project_policy,member)
need(project_roles <= {'roles/logging.logWriter'}, 'unexpected publisher project role; no automatic removal or broad grant')
need(not any(set(b.get('members',[])) & {'allUsers','allAuthenticatedUsers'} for b in project_policy.get('bindings',[])), 'public project IAM broadens effective permissions')
repository = get('https://artifactregistry.googleapis.com/v1/' + PLAN['repository_resource'])
need(repository and repository.get('format') == 'DOCKER', 'existing Docker repository not verified')
repo_policy = gc('artifacts','repositories','get-iam-policy','dation-runtime','--location=' + PLAN['region'])
need(grants(repo_policy,member) <= {'roles/artifactregistry.writer'}, 'unexpected repository grant')
sa_policy = gc('iam','service-accounts','get-iam-policy',sa)
for binding in sa_policy.get('bindings',[]):
    need(binding['role'] == 'roles/iam.workloadIdentityUser' and
        set(binding.get('members',[])) <= {PLAN['principal']} and not binding.get('condition'),
        'unexpected existing account impersonation policy')
bucket_url = 'https://storage.googleapis.com/storage/v1/b/' + PLAN['obsolete_source_bucket']
bucket = get(bucket_url)
bucket_roles = set()
if bucket:
    need(str(bucket.get('projectNumber')) == number, 'source bucket belongs to another project')
    bucket_policy = get(bucket_url + '/iam')
    bucket_roles = grants(bucket_policy,member)
    need(bucket_roles <= {'roles/storage.objectViewer'}, 'unexpected source-bucket grant')
pool_resource = 'projects/' + number + '/locations/global/workloadIdentityPools/' + PLAN['pool_id']
pool_url = 'https://iam.googleapis.com/v1/' + pool_resource
pool = get(pool_url)
if pool:
    need(pool.get('state') == 'ACTIVE' and not pool.get('disabled',False), 'existing pool inactive/deleted')
    providers = gc('iam','workload-identity-pools','providers','list','--location=global','--workload-identity-pool=' + PLAN['pool_id'])
    need(all(v.get('name') == PLAN['provider'] for v in providers), 'dedicated pool contains another provider')
provider = get('https://iam.googleapis.com/v1/' + PLAN['provider']) if pool else None

def verify_provider(value):
    need(value and value.get('state') == 'ACTIVE' and not value.get('disabled',False), 'provider not active')
    need(value.get('attributeMapping') == PLAN['attribute_mapping'] and
        value.get('attributeCondition') == PLAN['attribute_condition'] and
        value.get('oidc',{}).get('issuerUri') == PLAN['issuer'] and
        value.get('oidc',{}).get('allowedAudiences') == [PLAN['audience']], 'provider differs from reviewed trust; do not overwrite')

if provider: verify_provider(provider)
# All relevant reads precede configuration. No builds, deployments, keys or triggers.
new_apis = [a for a in PLAN['required_apis'] if a not in enabled]
if new_apis: gc('services','enable',*new_apis)
if not pool:
    gc('iam','workload-identity-pools','create',PLAN['pool_id'],'--location=global',
       '--display-name=Dation manual Gate C only')
if not provider:
    gc('iam','workload-identity-pools','providers','create-oidc',PLAN['provider_id'],'--location=global',
       '--workload-identity-pool=' + PLAN['pool_id'],'--issuer-uri=' + PLAN['issuer'],
       '--allowed-audiences=' + PLAN['audience'],'--attribute-mapping=google.subject=assertion.repository_id',
       '--attribute-condition=' + PLAN['attribute_condition'])
if 'roles/logging.logWriter' in project_roles:
    gc('projects','remove-iam-policy-binding',p,'--member=' + member,'--role=roles/logging.logWriter','--condition=None')
if 'roles/storage.objectViewer' in bucket_roles:
    gc('storage','buckets','remove-iam-policy-binding','gs://' + PLAN['obsolete_source_bucket'],
       '--member=' + member,'--role=roles/storage.objectViewer','--condition=None')
if 'roles/artifactregistry.writer' not in grants(repo_policy,member):
    gc('artifacts','repositories','add-iam-policy-binding','dation-runtime','--location=' + PLAN['region'],
       '--member=' + member,'--role=roles/artifactregistry.writer','--condition=None')
if not any(b.get('role') == 'roles/iam.workloadIdentityUser' and PLAN['principal'] in b.get('members',[]) for b in sa_policy.get('bindings',[])):
    gc('iam','service-accounts','add-iam-policy-binding',sa,'--member=' + PLAN['principal'],
       '--role=roles/iam.workloadIdentityUser','--condition=None')
verify_provider(get('https://iam.googleapis.com/v1/' + PLAN['provider']))
need(not grants(gc('projects','get-iam-policy',p),member), 'publisher still has direct project roles')
need(grants(gc('artifacts','repositories','get-iam-policy','dation-runtime','--location=' + PLAN['region']),member) == {'roles/artifactregistry.writer'}, 'repository writer not verified')
final_sa = gc('iam','service-accounts','get-iam-policy',sa)
need(any(b.get('role') == 'roles/iam.workloadIdentityUser' and b.get('members') == [PLAN['principal']] and not b.get('condition') for b in final_sa.get('bindings',[])), 'exact federated subject binding not verified')
if bucket: need(not grants(get(bucket_url + '/iam'),member), 'obsolete bucket grant remains')
print(json.dumps({'status':'WIF_CONFIGURATION_VERIFIED_METADATA','project':p,'provider':PLAN['provider'],
    'publisher_account':sa,'federated_principal':PLAN['principal'],'expected_claims':PLAN['expected_claims'],
    'repository_role':'roles/artifactregistry.writer','direct_publisher_project_roles':[],
    'apis_enabled_if_missing':new_apis,'cloud_build_modified':False,'builds_submitted':0,
    'cloud_run_modified':False,'supabase_modified':False,'scheduler_modified':False,
    'next_gate':'Actual GitHub OIDC authentication and one manual publication'},indent=2))
PY
```

La salida acredita configuración/IAM de metadata; la prueba efectiva de STS/impersonación ocurre en Auth del workflow. Si falla, conservar la razón exacta y diagnosticar esa autenticación antes de más cambios; no conceder TokenCreator por especulación. Una autenticación fallida no construye imagen.

## Orden posterior al GO

1. Autorizar y fusionar el PR de estos controles, sin cambiar el SHA de aplicación ni desbloquear apply. El workflow nuevo no publica al merge. La CI general no se solicita nuevamente; los commits de preparación llevan `[skip ci]` por instrucción del propietario y el workflow existente permanece intacto.
2. Propietario aplica exclusivamente el bloque WIF anterior y devuelve su JSON sanitizado. Codex puede leer GitHub y ejecutar el dispatch manual mediante la integración; no pedir al propietario construir/push desde Cloud Shell.
3. Despachar el workflow en main con confirm_publish=true una vez. Seguir por transiciones/terminal, descargar el artefacto y validar recibo/digest/SHA. Si hay versión previa válida, reutilizarla y verificarla; nunca fabricar un PASS por un tag ni por una ejecución verde sin recibo.
4. Con Gate C PASS, continuar el GO WEB D/E existente. El publisher no puede desplegar: su SA no tiene esos permisos. D requiere al operador GCP porque la credencial de Codex devuelve401; preparar un único bloque finito con el digest real del recibo, sin nueva configuración WIF ni build. Reutilizar [runbook aprobado](activation-runbook.md), sección3, con los manifiestos `manifests/` del artefacto: executor con 1 CPU/1 GiB/1800 s y recovery con 1 CPU/512 MiB/120 s, una tarea, paralelismo 1 y cero reintentos, crear sin ejecutar; rol personalizado de tres permisos únicamente en ambos Jobs; API con 1 CPU/512 MiB/concurrencia 8/timeout 300 s, min0/max2 en servicio y revisión, CPU por request/sin boost, Secret Manager versión 1, ejecución cloud en false. PolicyDB enabled/admissions false; no Scheduler.
5. API inicialmente privada: confirmar revisión/digest/SA/entorno y Auth de negocio sin Bearer mediante acceso de plataforma autorizado; sólo después allUsers con run.invoker en dation-core, nunca Jobs. Leer URL HTTPS real de Run, no deducirla ni reutilizar la antigua. El cap de Cloud Run existente se conserva y su ámbito se confirma antes del startup.
6. Codex puede aplicar el PATCH de Auth mínimo autorizado mediante Supabase una vez conocida esa URL: site_url=/app y callbacks /auth/callback,/auth/callback/recovery, preservando redirects previos. Sin cambiar claves/SMTP/proveedores/usuarios/passwords. Validar navegador real, login/logout y Comenzar → Model → Data Contract → Decision Case → Grafo, desktop y 390 px; sin D1/D2 ni altas de datos fuera del GO. Sólo declarar WEB_LIVE con acceso/login comprobados. Si hace falta sesión del usuario, pedir únicamente esa intervención, no su contraseña/token por chat.

`/ready`503/activation_unavailable con cómputo cerrado no es un fallo de liveness. No usarlo como startup probe. Verificar el scale-to-zero real con evidencia de instancias/métricas después de inactividad; min0 declarado no equivale por sí solo a uso0 demostrado. No crear warmers, worker residente, Jobs ejecutados o Scheduler para comprobarlo.

## Costo y rollback

Repositorio GitHub público confirmado: runners Linux estándar utilizan el régimen público de Actions; no asumirlo si cambia la visibilidad o se elige runner de pago. Build acotado a 20 minutos y job a 30 minutos. No nuevo cómputo GCP en Gate C. Registry retiene la imagen (máximo local de 2 GiB; referencia bruta ≈ USD 0,20/mes sin asumir free tier), operaciones/red y pull de recuperación a un runner externo pueden generar cargos; presupuesto de USD 5 y cap de Cloud Run no los cubren. La retención de 30 días del recibo deGitHub no elimina la imagen en Registry. WIF y SA no mantienen cómputo. No se promete costo cero ni un cap de factura.

Rollback identidad: deshabilitar únicamente este provider/pool o retirar su binding WorkloadIdentityUser exacto, sin tocar runtime, scheduler, otras cuentas, Cloud Build o Supabase. No restaurar grants obsoletos por rutina. Si C falla después de publicar, conservar digest/evidencia y recuperar esa versión; no reconstruir a ciegas. D/E: ante fallo retirar sólo acceso público deAPI y restaurar site_url/redirects del snapshot si corresponde; conservar migraciónB cerrada/datos/secretos/Jobs sin ejecutar. Nunca volver al proyecto anterior ni quitar el bloqueo deapply.

Referencias: [WIF para pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines), [auth oficial de GitHub](https://github.com/google-github-actions/auth), [principals WIF](https://docs.cloud.google.com/iam/docs/workload-download-cred-and-grant-access), [Tags create atómico](https://docs.cloud.google.com/artifact-registry/docs/reference/rest/v1/projects.locations.repositories.packages.tags/create).

## Validación de esta propuesta

- 25 pruebas focales de publicación, respuestas negativas, no sobrescritura, historial persistente, generación de manifiestos y configuración WIF idempotente: PASS.
- actionlint 1.7.12 fijado por checksum: PASS. Sintaxis Python del helper y del bloque Cloud Shell: PASS.
- Validador de release existente y revisión de secretos en los archivos propuestos: PASS, sin aplicar cambios.
- CI general no repetida, Docker no construido y ninguna llamada de mutación GCP/Supabase ejecutada. La prueba real de OIDC y la publicación siguen pendientes del GO y de la configuración del propietario.

Reproducir los tests desde el repositorio requiere Python con PyYAML y un worktree limpio del SHA de aplicación:

```bash
git worktree add --detach /tmp/dation-validated-source 792470ff8cce54cb32b81240b206fdbcb7078ea2
DATION_TEST_VALIDATED_SOURCE=/tmp/dation-validated-source python3 -m unittest discover -s tests/operations -v
actionlint .github/workflows/runtime-v2-publish.yml
python3 scripts/zero_idle_release.py validate
```

Estos comandos sólo validan en local; no crean imágenes ni recursos cloud. No usar un directorio existente para el worktree.
