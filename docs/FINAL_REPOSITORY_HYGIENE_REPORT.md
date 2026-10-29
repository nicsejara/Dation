# Dation — Final Repository Hygiene Report

Fecha: 2026-10-29 (`America/Buenos_Aires`). Scope: Repository Hygiene + Codex
Environment Hygiene + Master Development Baseline. No es T13 ni una nueva
auditoría funcional. Autoridad: documento maestro adjunto y pedido explícito de
ejecutarlo sobre `nicsejara/Dation`, `main`, environment `Dation`.

## Git baseline

- SHA remoto inicial y fuente productiva inspeccionada: `3e8712962ba7b444f47b44d5afa9887f4c2e4a10`.
- Workspace recibido: rama `work`, HEAD `e342971813b6baae6031bb0b38b206d3a5cba925`;
  `main` y `origin/main` locales en `1477b41fd5480562d6369f9f34bc093bafd6b2c3`.
  Working tree limpio. Se registró ese estado antes de cambiarlo.
- Remote verificado: `https://github.com/nicsejara/Dation.git`; default branch
  verificada por GitHub: `main`. Fetch completo, historial no shallow y avance
  fast-forward a `3e8712962ba7b444f47b44d5afa9887f4c2e4a10`. Sin reset, rebase ni force-push de `main`.
- Tag productivo anotado creado y publicado antes de intentar eliminar ramas:
  `ultimate-mvp-production-20261029`. Objeto tag `067b5aea122256a8b0eb82f87f6363c153eb5407`;
  target pelado `3e8712962ba7b444f47b44d5afa9887f4c2e4a10`. Mensaje: Dation Ultimate MVP consolidated production
  baseline after T0-T12. No había tags remotos previos.
- **SHA final de `main`: `3e8712962ba7b444f47b44d5afa9887f4c2e4a10`**, sin cambios respecto del inicial.
- Cambios documentales publicados en `chore/final-repository-hygiene`; commit de
  contenido inicial `f857c0cda8045428fd4a0566cdf377fbdbae334d`, seguido por la
  actualización de este informe para registrar los bloqueos de aprobación.
- La revisión automática rechazó el push directo a `main` por ser la rama
  predeterminada y disparar producción, requiriendo aprobación explícita. Se optó
  por publicar la rama de trabajo y preparar una PR borrador como alternativa
  revisable. No se usó otra API para eludir el rechazo.
- La rama temporal se conserva hasta aprobar e integrar el cambio documental;
  después debe eliminarse. El SHA exacto del candidato se resuelve con
  `git rev-parse origin/chore/final-repository-hygiene` y se informa en la entrega.

## Branch cleanup

Inventario remoto inicial completo: **104 ramas**, obtenido en dos páginas
de GitHub (100 + 4) y contrastado con fetch Git. `main` se conserva. Las otras
**103** están clasificadas en la tabla final de este informe:

- **88 B:** `git rev-list --left-right --count main...SHA` da cero commits propios;
  son ancestros o idénticas a `main`.
- **15 A:** tenían commits únicos por SHA. Su diff acumulado desde merge-base
  tiene el mismo `git patch-id --stable` que un squash de `main`. Además se
  comprobó igualdad exacta de blobs y modos de cada archivo afectado contra ese
  commit; no se decidió por antigüedad o por el nombre de la rama.
- **0 C, 0 D remotas.** No se importó ningún cambio de ramas históricas.
- `recovery/t12-t12r-environment-20261029` es B: mismo SHA `3e8712962ba7b444f47b44d5afa9887f4c2e4a10`.

**Eliminadas remotas históricas: 0. Conservadas históricas: 104, incluido `main`.**
Hay además una rama temporal nueva `chore/final-repository-hygiene` para revisión:
**105 ramas remotas en total al preparar la entrega**. La revisión
automática rechazó la eliminación atómica de las 103 referencias por alcance
amplio y coste de reversión, exigiendo aprobación explícita de esa lista exacta.
No se eludió la revisión por lotes menores ni otra API. La lista constituye el
plan concreto de eliminación; después de aprobar, revalidar los SHA esperados.

### Excepción local D — trabajo único potencialmente relevante

Se conserva **únicamente local**, además de `main`:
`platform/phase12-hardening` → `6b1781ccd42c845a8be68e7b713acdd1c0c22c75`.
Tiene un commit propio, 90 commits de diferencia por el lado de `main`, y 17
archivos afectados. No tiene squash equivalente y no existe como rama remota.

Inspección focal del diff y de los archivos correspondientes en `main`:

- `backend/app/static/js/platform/session.js`: el WIP descarta la sesión en memoria
  cuando falla un refresh explícito y maneja respuestas de sesión no JSON. Esas
  modificaciones concretas no están en `main`.
- `backend/app/auth.py`, `observability.py`, servicios de jobs/comparative: el WIP
  incorpora atribución UUID de usuario/workspace desde autoridad verificada. La
  ampliación de campos de telemetría no está en `main`.
- Añade `release_session_journey.py`, `test_interpreter.py` y `test_release_gate.py`
  bajo `backend/tests/e2e/`; esos archivos no existen en `main`. Sus contratos son
  anteriores a Ultimate y requieren revisión focal antes de reutilizarse.
- Los cambios de Home del WIP pertenecen a una vista reemplazada por el Home
  actual. Esa parte superada no demuestra que el resto del WIP sea prescindible.

No se afirmó un bug funcional ni se ejecutaron tests para recertificar el
producto. No se cherry-pickeó ni publicó este WIP. Resolverlo requiere decidir
su descarte justificado o una tarea focal separada para adaptar lo pertinente.
Mientras exista esta excepción, no se declara CLEAN.

### Limpieza local ejecutada

Se eliminaron **68 ramas locales B**, mediante `git branch -d` y comprobación
previa de ascendencia contra `main`. Incluye `work`, cuyo HEAD ya estaba integrado.
Se removió `/workspace/Dation-foundation`, worktree histórico limpio, sin cambios
no versionados y sobre un ancestro. No se usó eliminación forzada de worktrees.
El WIP D se conserva. Los 68 nombres eliminados figuran en el apéndice local.

Los virtualenvs y caches ignorados permanecen como herramientas de desarrollo.
Los artifacts históricos fuera del repositorio no se borraron por antigüedad.
Los scratch assets de esta tarea viven en `/workspace/work/dation-hygiene`, fuera
del árbol versionado. No se identificaron temporales no versionados que requieran
borrado adicional en el working tree.

## Repository cleanup

**Archivos versionados eliminados: ninguno. Movidos: ninguno. Renombrados: ninguno.**

Se revisaron 2421 archivos versionados. Los 286 candidatos por extensión de log/
temporal están dentro de `docs/execution/`, como evidencia deliberada; se conservaron.
Los duplicados encontrados tienen responsabilidades distintas: versiones Python
en raíz/backend, logo de landing/app, templates y fixtures repetidos de escenarios.
Se verificaron referencias en landing, templates, tests y scripts. Los templates
de compatibilidad se conservan; no se demostró ausencia de consumidores para
justificar su eliminación. Scripts de fixtures/conversión/benchmark siguen
referenciados por tests o documentación histórica.

Documentación actualizada por contradicciones materiales:

- `README.md`: Ultimate, modelos/pack versionado, D1/D2 y schemas actuales;
  separación del flujo Orders/Fleet/tercer nodo histórico.
- `backend/DEPLOYMENT.md`: pipeline vigente, configuración mínima y distinción
  del runbook histórico de versiones 1.0 y pasos SQL ya aplicados.
- `docs/architecture.md`, `domain-model.md`, `component-map.md`, `decision-runs.md`:
  paths Ultimate reales y límites respecto de los contratos de compatibilidad.
- `infra/README.md`: build/publicación/worker/API y CI separado.
- `supabase/README.md`: orden completo de reconstrucción y alcance de las listas
  incrementales antiguas.
- Índice y estado de `docs/platform-mvp/`: aviso de evidencia histórica, sin
  reescribir sus resultados ni marcar retrospectivamente fases como completadas.
- `docs/MASTER_DEVELOPMENT_BASELINE.md`: referencia técnica corta para continuar
  en el mismo chat maestro.
- Este informe: inventario, evidencia de clasificación y excepciones reales.

No se modificaron engines, contratos, APIs, SQL, tests, frontend ni infraestructura.
Se preservan `logistics_assignment`, `logistics_scheduling`, `transport_plan_v1`,
`day_scheduling_v1`, `decision_context_v1` y los ABIs existentes. Los Execution
Reports T0–T12/T12-R y sus artifacts permanecen intactos.

## Migrations

**41 archivos**, timestamps únicos y contenidos distintos; primero
`20261001004934_dispatch_v1.sql`, último
`20261029040212_ultimate_pilot_cohort.sql`. El sandbox versionado aplica el baseline
capturado y todas las migraciones posteriores a `20261010100000`, en orden.
Se revisaron las referencias del último handoff existente. No se renombró,
combinó, reparó, regeneró ni ejecutó ninguna migración. No se consultó ni modificó
Supabase productivo. El estado productivo declarado por el documento maestro no
se presenta como una nueva comprobación remota del catálogo.

## GitHub workflows y deployment

Confirmado sobre el SHA inicial mediante el check de Google Cloud Build:

`main → Cloud Build → Artifact Registry → Cloud Run Worker → Cloud Run API`.

Build [609cb976-22f2-4c4b-8d86-e4ccfe8507db](https://console.cloud.google.com/cloud-build/builds/609cb976-22f2-4c4b-8d86-e4ccfe8507db?project=469052310590),
pasos `Dockerfile`, `Push`, `Worker` y `Deploy`: **SUCCESS**. El trigger existente
se administra fuera del repo; no hay un cloudbuild.yaml versionado. El Dockerfile
raíz incluye app, entrypoints y ambos directorios sample requeridos. El workflow
`.github/workflows/backend-tests.yml` ejecuta CI en paralelo y no despliega.

El check [tests del SHA inicial](https://github.com/nicsejara/Dation/actions/runs/40888476638/job/123498478423)
estaba **FAILURE antes del hygiene**. No se cambió ni relanzó esa suite para
convertir esta tarea en otra certificación funcional. Los checks de un nuevo
commit disparados por la integración normal deben distinguirse de esa evidencia.

La lectura administrativa de triggers GCP respondió HTTP 401 tanto en región
us-west1 como global usando el binding existente; no se renovaron tokens. El
check de Cloud Build en GitHub permite confirmar el pipeline sin depender de ese
token temporal. No hubo deploy manual ni cambios de IAM, cuentas o servicios.
El push a `main` fue rechazado antes de ejecutarse; el commit documental permanece
en la rama temporal. Una integración aprobada aceptará el deployment automático
normal, sin operaciones GCP manuales adicionales.

## Codex environment

Environment objetivo indicado por el usuario: **Dation**. Instancia adjunta:
`ccarenv_b64_Y2NhcmVudl80MjgzNzNjNDc5OTg4MTkxODAwNDY1MjQ1MjUxMDk5MA`.
La API runtime informa instancia y readiness, no un campo de nombre visible;
no se inventa una lectura de ese nombre. Estado observado `running/connected`,
observaciones actuales y política HTTP `restricted/enforced`. Sin VPN configurada
ni grants TCP. No hay outbound identities ni capabilities adicionales declaradas.

Directorio de inicio del executor: `/workspace`; repositorio de trabajo:
`/workspace/Dation`. Para tareas futuras seleccionar ese repo y `main`. Fetch
normal configurado para `origin/main`; se usó un refspec explícito para inventariar
todas las ramas durante este hygiene.

### Variables, secrets y Network Secrets — sólo nombres

| Nombre | Estado observado / uso | Acción |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_INPUT_BUCKET` | Runtime variables ready; integración backend/Storage | Conservar para integración autorizada; QA aislado usa fixtures propias |
| `SUPABASE_SECRET_KEY` | Network Secret ready, limitado al host del proyecto | Conservar protegido para integración autorizada; nunca navegador |
| `SUPABASE_ACCESS_TOKEN` | Network Secret ready, host Management API | Acceso administrativo opcional; no dependencia del desarrollo ordinario |
| `DATION_ACCESS_PASSWORD` | Runtime variable ready; sólo definición legacy en config | Eliminar de variables del environment Dation; Auth actual usa Bearer |
| `GCP_ACCESS_TOKEN` | Network Secret ready; GET administrativo devolvió 401 | Eliminar binding y Network Secret de Dation: token operativo temporal, no pipeline normal |
| `GCP_ROLLOUT_ACCESS_TOKEN` | Network Secret ready; sin consumidor runtime normal encontrado | Eliminar binding y Network Secret de Dation: credencial temporal T12-R |
| `LLM_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL` | No presentes en este executor | Sólo configurar proveedor y destino si una tarea requiere IA real; no bloquea hygiene |

No se leyeron, imprimieron ni decodificaron valores de secretos. `ready` indica
inyección configurada, no vigencia del OAuth token. No se verificó la expiración
de `GCP_ROLLOUT_ACCESS_TOKEN` ni se intentó renovarlo. `GCP_ACCESS_TOKEN` aparece en
`scripts/deploy_production_phase3.py` (deploy manual histórico), en documentación
y en scrubbers de variables de tests. El pipeline y el runtime no lo consumen.

### Red y herramientas

Destinos personalizados actuales: `api.github.com`, `api.supabase.com`,
`gijiinufjjurgfeehufj.supabase.co`,
`dation-core-469052310590.us-west1.run.app`, `artifactregistry.googleapis.com`,
`cloudbuild.googleapis.com`, `cloudresourcemanager.googleapis.com`,
`iam.googleapis.com`, `iamcredentials.googleapis.com`, `logging.googleapis.com`,
`run.googleapis.com`, `secretmanager.googleapis.com`, `serviceusage.googleapis.com`,
`storage.googleapis.com`, `us-west1-docker.pkg.dev`; preset `package_managers`.
No se alteró la política. Los destinos de administración GCP son opcionales para
trabajo operativo, no necesarios para un cambio ordinario mediante GitHub.

Git 2.52.0, ripgrep, gh, Docker 28.4.0 y npm disponibles. La shell selecciona
Python 3.12.14 / Node 24.19.0; el proyecto conserva `.venv/bin/python` 3.13.5 y
Node 22.23.3 en `/workspace/.dation-cloud/node/node_modules/.bin/node`.
Virtualenvs separados de navegador/auditoría existentes. gcloud no está en PATH,
pero hay una instalación histórica en `.dation-cloud/google-cloud-sdk`; no se
necesita instalarla ni activarla para desarrollo normal. Supabase CLI no está
en PATH; no se necesita para este hygiene.

### Setup scripts y acciones manuales de UI

La herramienta Cloud Environment disponible inspecciona runtime; no ofrece
mutación/publicación de configuración del environment. Acciones precisas en la
UI de **Dation**, sin bloquear el resto del hygiene:

1. Eliminar Network Secrets `GCP_ACCESS_TOKEN` y `GCP_ROLLOUT_ACCESS_TOKEN` y sus
   bindings a esas variables. Si hubiera variables duplicadas separadas, retirarlas
   también. No tocar secretos productivos de Cloud Run/Secret Manager.
2. Retirar la variable legacy `DATION_ACCESS_PASSWORD` del environment de Codex.
3. Repository: `nicsejara/Dation`; branch inicial: `main`; working directory:
   `/workspace/Dation`. Contexto de inicio: `docs/MASTER_DEVELOPMENT_BASELINE.md`.
4. Eliminar del setup/start configurado referencias a fases anteriores o a
   `.dation-cloud/smoke.py`, que espera Basic y pertenece al workspace antiguo.
   `.dation-cloud/install-final.sh` instala dependencias pero también regenera ese
   smoke y herramientas GCP históricas; no usarlo como setup maestro actual.
5. Mantener setup mínimo con Python 3.13 y los requirements con hashes, `pip check`
   y Node 22 si se necesita frontend. Instalar browser/dev requirements sólo para
   el trabajo que los requiere. Ningún setup debe ejecutar migraciones, seeds,
   cleanup productivo, rollout, auditorías integrales o smokes con escritura.

`activate.sh` sólo activa virtualenv y PATH; los `start_skill_phase*.txt` son
instrucciones históricas, no contexto maestro. No se ejecutaron esos scripts ni
se borraron configuraciones/credenciales opacas. Los directorios de evidencia de
auditorías previas quedan fuera del repo activo y no son fuente de arquitectura.

## Verificación del hygiene

Diff de **12 archivos, todos Markdown**. Validación focal **PASS**: whitespace/diff,
79 enlaces locales, 26 paths canónicos actuales, las cinco entradas COPY del
Dockerfile, unicidad de versiones/contenidos y orden de 41 migraciones, árbol de
migraciones intacto, ascendencia/clasificación y tag anotado. No se ejecutó T11 ni suites funcionales:
no se eliminaron archivos de código ni se modificaron imports, build o runtime.
La entrega vuelve al `main` original, con HEAD igual a `origin/main` y working tree
limpio. La rama temporal conserva los documentos para revisión; el WIP local D
permanece aparte. Las referencias observadas se registran en la respuesta de entrega.

## Deferred

Deferred operational hardening — external production backup destination.

No se creó bucket ni backup nuevo. No bloquea desarrollo, testing ni deployment
normal. El WIP D y la aprobación de ramas son condiciones de cierre de este
hygiene, no pendientes escondidos en hardening.

## Inventario remoto certificado — 103 candidatas pendientes de eliminación

`main` es la rama restante fuera de esta tabla, en `3e8712962ba7b444f47b44d5afa9887f4c2e4a10` al inspeccionar.
Todas las filas siguientes se conservan remotamente hasta aprobar su eliminación.

| Rama | SHA inicial | Categoría | Evidencia de integración |
|---|---|---|---|
| `codex/container-runtime-fix` | `85fe7b024e70c9413c47b31d13e1a6896be5ce98` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase0-spec` | `2f377515aa9baa562daa5fd0427482f903b9fb70` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase1-current-step-contrast` | `db174733af0e4cd5e5c193daec07a1889637c14b` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase1-foundation` | `c3c1537c1fbc1c5b86c0e80b670d4a998a5620e9` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase2-home-overview` | `179c7d14d47b852458b837004d916753db257971` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase3-data-pack` | `7ef2fc52525eae63740da40da4906656024c608b` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase4-config` | `ffa0a587e5ccca9bf36273730b6a165d125fa4c9` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase5-dashboards` | `744bb922da5000e455640ca9a29de010de6afe13` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase6-qa` | `b8416fbb8d1610f9a41ec0e4f3566785d8a13335` | B | Ancestro / mismo HEAD |
| `codex/dark-rebrand-phase7-cleanup` | `0f318742eed013fa153d0341780cfa91fa24688c` | B | Ancestro / mismo HEAD |
| `codex/dashboard-progressive-analysis` | `998772ec2ebd7942996d4afe53e4ba938e997ebd` | B | Ancestro / mismo HEAD |
| `codex/dashboard-refinement-v2` | `cdbaed63f6584e786775e1eb031338ea9e0e94a1` | B | Ancestro / mismo HEAD |
| `codex/overview-dual-cta-disclosure-fix` | `33fe736319c26fd7309038887cbd606c708732f6` | B | Ancestro / mismo HEAD |
| `codex/phase-3-durable-execution` | `a9bbb0dd70c03ff1de49635b596b5ae1ae1fb1e6` | B | Ancestro / mismo HEAD |
| `codex/phase-4-approval-clock` | `34191ee53c8da30c6d73752fb07b0eac85933da1` | B | Ancestro / mismo HEAD |
| `codex/phase-4-persistence-traceability` | `2c99d088eafdc9d475348682bc32707dae2c0457` | B | Ancestro / mismo HEAD |
| `codex/phase-5-performance` | `f4de0907605afa661da68020d971b06c7589714a` | B | Ancestro / mismo HEAD |
| `codex/phase-6-end-to-end` | `ed40fa2910c903aaf5eb9ae64f6dd271d7fcadd6` | B | Ancestro / mismo HEAD |
| `codex/phase-7-observability` | `5ca1ead33bf36195d0e2ce5b8866ba94af293d7a` | B | Ancestro / mismo HEAD |
| `codex/phases-0-2-production` | `1442610210112bcbeafbf5cba060ee095b36b884` | B | Ancestro / mismo HEAD |
| `codex/platform-phase10-audit-activity` | `7c7f6a1c46f737e7ca77344cde00ce3457d50957` | B | Ancestro / mismo HEAD |
| `codex/platform-phase11-demo-image-context` | `9429ff3b670a28574e3bfe3d016b84da5b40bab5` | B | Ancestro / mismo HEAD |
| `codex/platform-phase11-onboarding-demo` | `e00fcb7c47c23defe87abc669f7490370dd0bed6` | B | Ancestro / mismo HEAD |
| `codex/platform-phase8-team` | `2dabcf2d6cbbca67a3ab8bf9f8ca6d1c911c6828` | B | Ancestro / mismo HEAD |
| `codex/platform-phase9-settings-free` | `579f7d9416d1fbbd68eb73ee213f28f06ff80756` | B | Ancestro / mismo HEAD |
| `codex/ux-navigation-recovery-v3` | `5b81f4c5b729f98508974dac9ac336d67755950b` | B | Ancestro / mismo HEAD |
| `codex/workflow-design-system-phase1` | `c3ee7f1ed6901341dd26fa681c0750bdc2282e80` | B | Ancestro / mismo HEAD |
| `codex/workflow-design-system-phases2-3` | `81d271247468ff71e43495dfb739c9745bb99188` | B | Ancestro / mismo HEAD |
| `codex/workflow-hero-system-phase4` | `0156e990da67e4a5b87d29460d5262010abcaaf8` | B | Ancestro / mismo HEAD |
| `docs/platform-mvp-phase0` | `2f82015c1477fb0c8f247c94b18637ccc19a6c71` | B | Ancestro / mismo HEAD |
| `feat/assignment-dashboard-phase0-audit` | `0283f9bd9997e5d7476228f697ae30bf380dc86e` | B | Ancestro / mismo HEAD |
| `feat/assignment-dashboard-phase1-shell` | `de0700b4853ed6ed207cfbe2d124bbd880ef754e` | B | Ancestro / mismo HEAD |
| `feat/assignment-dashboard-phase2-essential` | `28d2672708a9be2756ec102f98f15bd6fc290bc6` | B | Ancestro / mismo HEAD |
| `feat/collapsible-scope-filters` | `d230b957e428dd04df8f26597c1d605389288df8` | B | Ancestro / mismo HEAD |
| `feat/configure-decision-redesign` | `b2e2b35b27752e8f74607cb6bb5250ad772ea836` | B | Ancestro / mismo HEAD |
| `feat/d1-assignment-dashboard-v2` | `41b234ab2c60a34eeeeee3246d4450ba6f096656` | B | Ancestro / mismo HEAD |
| `feat/d2-scheduling-dashboard-v21` | `5737aedffc41ba0673239762f2217b632419dc7a` | B | Ancestro / mismo HEAD |
| `feat/decision-cases-persistence-v1` | `1addfa9f65e9f5eb561bc100e5418a2783da39d3` | B | Ancestro / mismo HEAD |
| `feat/decision-map-case-datapack-v2` | `98bb9ea0a8b5be75d4eab0eae6688a05eee48e82` | B | Ancestro / mismo HEAD |
| `feat/decision-map-micro-polish` | `2319138355e70b0ad48b3cd8a90c8e76fec8bc7b` | B | Ancestro / mismo HEAD |
| `feat/decision-run-history-v2` | `7eae1b85fb02801503fe6b13386b820d38071e6a` | B | Ancestro / mismo HEAD |
| `feat/landing-informative-navigation` | `2fc00c8c5f5b4a62b42395065f80551941996ec2` | B | Ancestro / mismo HEAD |
| `feat/platform-mvp-foundation` | `0e5934eb3623b7bc702404a9378eeb2409576c92` | B | Ancestro / mismo HEAD |
| `feat/platform-phase2-auth-tenancy` | `218ca6a212e993aea444fb19ff3bca11430d149e` | B | Ancestro / mismo HEAD |
| `feat/platform-phase5-dda-entitlements` | `21a98e5cb3d659fc27e62cfba516d859a78e0275` | B | Ancestro / mismo HEAD |
| `feat/platform-phase6-data-hub` | `0f97bb5b0427a7503b41bb075d20aad33a5284c8` | B | Ancestro / mismo HEAD |
| `feat/platform-phase7-decision-center` | `8438976382f6ba303a18c40451c526db64eae925` | B | Ancestro / mismo HEAD |
| `feat/platform-workspace-home` | `73c1e88557aa8eb9934bd57a478fa8561e3aaddf` | B | Ancestro / mismo HEAD |
| `feat/pre-dashboard-ux-normalization` | `9e520f02475353f14d290547265ad6c42be2a483` | B | Ancestro / mismo HEAD |
| `feat/premium-decision-map` | `f14e7ae38e7a9980eb5f5f79cf3f545c1f56d287` | B | Ancestro / mismo HEAD |
| `feat/scheduling-config-phase1` | `c731eee9e45464918414a03d33834aa32c5eed86` | B | Ancestro / mismo HEAD |
| `feat/scheduling-config-phase2` | `57c439d8fef2f885897cd367dd35f3ac770a3fbd` | B | Ancestro / mismo HEAD |
| `feat/scheduling-config-phase2-shared-ui` | `00c3d8c48667fe957c92600b8611fa7a4fd4405e` | B | Ancestro / mismo HEAD |
| `feat/scheduling-config-phase3-rule-editor` | `5c5d39a855996b991ad6e2c038dff549750f8d24` | B | Ancestro / mismo HEAD |
| `feat/scheduling-config-phase4-execution-lifecycle` | `ae7d51f891cd13e14dfb789d788a5a1a87fcb79d` | B | Ancestro / mismo HEAD |
| `feat/traceability-phase3` | `81b2346015188538647bab47054b67a562657a3c` | B | Ancestro / mismo HEAD |
| `feat/workflow-responsive-a11y-phase6` | `131c5b7ebe1db40e9503c42cc15149bd664e2239` | B | Ancestro / mismo HEAD |
| `feat/workflow-review-dialog-phase5` | `c66223542751e7806c450c35f7e412c4d494bd79` | B | Ancestro / mismo HEAD |
| `feature/dashboard-actions-ai-ux` | `b713eaf6a9f2c01dd03f2650096431c41cc4b967` | A | `557f7f44ed257e91187817687e05d190bbd51e90` |
| `feature/dashboard-decision-focus` | `cbace6cb071ee98a2c8f3e1104c9ee109730c20f` | A | `df3e35b915be6d0e92c59beede195a7262553d3a` |
| `feature/data-pack-v3-decision-readiness` | `b3b9d36bd5b8be2dac501bb10ddd438e534909c0` | A | `371702a0a210194f7260e18026587fcf8bf915c6` |
| `feature/decision-chain-phase2-map` | `49031dfdad530b15fa98caa6ae6e0904e578fbc2` | A | `e1c181997c0ffae56e59422b44a5162aaa36a337` |
| `feature/decision-chain-phase3-assignment-engine` | `f017feeaab83094e55759de7d69bc3b95a51ba95` | A | `ad90e37e8de1855e259bff4222f3afcee002eed7` |
| `feature/decision-chain-phase4-scheduling-engine` | `d3b6d0c86db3c25d8860386d049cdd85f0e35b3a` | A | `2a1b22da5b3c67e9c25fdf1be82e4af31ceac180` |
| `feature/decision-composer-config` | `df48a4a0b5e55082e5e17577cf54f703d5e3cc7a` | A | `6f480983dbb8c3100ebd2907fe57732e5e621189` |
| `feature/decision-flow-navigation` | `38bf1882840d5ceccd2c4368e42ca00c5d138841` | A | `fdff846a2890175b04f2fd7c51d6970a450cdecd` |
| `feature/decision-workspace-v01` | `c5731c79c1f3205f3d470073e2c5749c52ac7082` | A | `aafe2e19a026d79203349264896af84db28082c3` |
| `feature/decision-workspace-v02` | `c2a5e311c135ed176b56f8df9b688f61e9e1751b` | A | `20dd6ff257d411bf136220f5fbfb0ec9495c54d2` |
| `feature/dispatch-v2-phase1-contract-transition` | `33a6a4e03c934de8866c46c14a395845baa1d2b7` | A | `aa62bfacbe97d8f830c56a7c7d394476586ca28a` |
| `feature/dispatch-v2-phase2-spatial-fleet` | `0ae7c801cfb8b922dcc3126f3c4e4b6e169fc07b` | A | `ce41564aaa4e3da0313234d1ad42ccb175c37325` |
| `feature/dispatch-v2-phase3-temporal-capacity` | `c9dd9bcfa5145200a526e62720aaf80ad68ec63a` | A | `b4f4637fec0b5c86f8feb71da5487292156d3579` |
| `feature/dispatch-v2-phase4-objectives-sla` | `3d63b8b79563f3778ca980487e075355a31ef203` | A | `eb0ca87fff23a036eabb9d51faefabfab2c3a515` |
| `fix/assignment-dashboard-phase2-cache-bust` | `b3d9560d58602ab075c80967d9897c9f86839ebc` | B | Ancestro / mismo HEAD |
| `fix/catalog-pill-sizing-production-icon` | `0c28f00511d05178134324b77c34e81687ee4b88` | B | Ancestro / mismo HEAD |
| `fix/config-decision-duplicate-render` | `285f29e6ec1d686b38e098188dfdaa4bf2d2e51c` | A | `5cc78a03b6846510b50c159988a491471cc51ede` |
| `fix/config-decision-visual-consistency` | `8e1274f2c5764585bb0c4ed968ede9b828ef2dee` | B | Ancestro / mismo HEAD |
| `fix/d1-d2-hero-context-kpi` | `818184c2ed1ab12424ac152d76b95bc6fc6b6dc9` | B | Ancestro / mismo HEAD |
| `fix/d1-disclosure-polish` | `860a33ea30febc004d7ab08d68fdbbc92c6a4b0b` | B | Ancestro / mismo HEAD |
| `fix/d1-evidence-focus-overflow` | `75fceb337a6f48906d1f0874851addd4f79d6164` | B | Ancestro / mismo HEAD |
| `fix/d1-table-focus-visibility` | `e872b839803d817fd5dc127fc09f2c3e844dc566` | B | Ancestro / mismo HEAD |
| `fix/decision-case-navigation-ux` | `01e12ea4ac52288ce118a6100e36fac395de81da` | B | Ancestro / mismo HEAD |
| `fix/home-catalog-keyboard-scroll` | `824c9174ab7fee2dbb01f57a94ef706c3eb95cb2` | B | Ancestro / mismo HEAD |
| `fix/platform-bfcache-session` | `a1e576e6b20ad0c01b0786f3a1c6bd738b0fd380` | B | Ancestro / mismo HEAD |
| `platform/apply-attributes-before-csv` | `21a71ea7cb8b5133b1447776301ca04f03b8496a` | B | Ancestro / mismo HEAD |
| `platform/case-workflow-ultimate` | `997427d55d82cf569ed0e668f18b6f9a0e812658` | B | Ancestro / mismo HEAD |
| `platform/foundation-implementation` | `5db4f8f7c1f40257aa70d46e37d3df562546fe59` | B | Ancestro / mismo HEAD |
| `platform/optimized-ux-responsibilities` | `0cdac948ed985ec4fe1904a5ffe9b9b34b9770b5` | B | Ancestro / mismo HEAD |
| `platform/saga3-runs-ownership` | `e7d6926c3eb5f5c2b33993cbf006ce5ef86cf8a4` | B | Ancestro / mismo HEAD |
| `platform/saga4-workflow-polish` | `1a559c6f70d1395a08074fd7d336ce19595f26f6` | B | Ancestro / mismo HEAD |
| `platform/saga5-case-attributes-results` | `781174350f289969264f8bf8b3a806af63200013` | B | Ancestro / mismo HEAD |
| `platform/ux-workflow-second-saga` | `a246b595484efb4d2c4c3192ab60f584546cb89e` | B | Ancestro / mismo HEAD |
| `platform/v2-phase1-foundation` | `16007b0d18918606244af7792058e9a90619e396` | B | Ancestro / mismo HEAD |
| `platform/v2-phase2-decision-center` | `2b6ed989c72e67752562b3587016f991fe421dda` | B | Ancestro / mismo HEAD |
| `platform/v2-phase2-preserve-assignment-search` | `d3cafabf4d8093a0aabc8110d35a7b2227ec4db6` | B | Ancestro / mismo HEAD |
| `platform/v2-phase3-data-hub` | `44d97b5e9c1e4d558bfba5ba0c4685b32c6bf1c3` | B | Ancestro / mismo HEAD |
| `platform/v2-phase4-certifi` | `82b1fce9ff2a592614b07bbfb3552dd58ed5edc0` | B | Ancestro / mismo HEAD |
| `platform/v2-phase4-home` | `750ed369f33fef9362369bf112741af9c294973d` | B | Ancestro / mismo HEAD |
| `platform/v2-phase5-transversal` | `c8cd9d880173e1641603b78a7f7a1349159599da` | B | Ancestro / mismo HEAD |
| `platform/v2-phase6-golden-regression` | `42b9095119c0712a1575f5b56d45116be6a896d1` | B | Ancestro / mismo HEAD |
| `recovery/t12-t12r-environment-20261029` | `3e8712962ba7b444f47b44d5afa9887f4c2e4a10` | B | Ancestro / mismo HEAD |
| `refactor/shared-decision-config-foundation` | `6d552cb3d4790c649a33d9779950dff1c0946a82` | B | Ancestro / mismo HEAD |
| `test/workflow-end-to-end-phase7` | `8eed2a411da953c70af8b5746177e09c1a6eb4b9` | B | Ancestro / mismo HEAD |
| `ux-ui/visual-product-upgrade` | `ff8134c6a19fc98c7e6a81029d830b4ab5285560` | B | Ancestro / mismo HEAD |

## Apéndice — 68 ramas locales B eliminadas

- `codex/container-runtime-fix`
- `codex/dark-rebrand-phase0-spec`
- `codex/dark-rebrand-phase1-current-step-contrast`
- `codex/dark-rebrand-phase1-foundation`
- `codex/dark-rebrand-phase2-home-overview`
- `codex/dark-rebrand-phase3-data-pack`
- `codex/dark-rebrand-phase4-config`
- `codex/dark-rebrand-phase5-dashboards`
- `codex/dark-rebrand-phase6-qa`
- `codex/dark-rebrand-phase7-cleanup`
- `codex/dashboard-progressive-analysis`
- `codex/dashboard-refinement-v2`
- `codex/overview-dual-cta-disclosure-fix`
- `codex/phase-3-durable-execution`
- `codex/phase-4-approval-clock`
- `codex/phase-4-persistence-traceability`
- `codex/phase-5-performance`
- `codex/phase-6-end-to-end`
- `codex/phase-7-observability`
- `codex/phases-0-2-production`
- `codex/platform-phase10-audit-activity`
- `codex/platform-phase11-demo-image-context`
- `codex/platform-phase11-onboarding-demo`
- `codex/platform-phase8-team`
- `codex/platform-phase9-settings-free`
- `codex/ux-navigation-recovery-v3`
- `codex/workflow-design-system-phase1`
- `codex/workflow-design-system-phases2-3`
- `codex/workflow-hero-system-phase4`
- `docs/platform-mvp-phase0`
- `feat/d1-assignment-dashboard-v2`
- `feat/d2-scheduling-dashboard-v21`
- `feat/platform-mvp-foundation`
- `feat/platform-phase2-auth-tenancy`
- `feat/platform-phase5-dda-entitlements`
- `feat/platform-phase6-data-hub`
- `feat/platform-phase7-decision-center`
- `feat/platform-workspace-home`
- `feat/pre-dashboard-ux-normalization`
- `feat/workflow-responsive-a11y-phase6`
- `feat/workflow-review-dialog-phase5`
- `fix/catalog-pill-sizing-production-icon`
- `fix/d1-d2-hero-context-kpi`
- `fix/d1-disclosure-polish`
- `fix/d1-evidence-focus-overflow`
- `fix/d1-table-focus-visibility`
- `fix/decision-case-navigation-ux`
- `fix/home-catalog-keyboard-scroll`
- `fix/platform-bfcache-session`
- `platform/apply-attributes-before-csv`
- `platform/case-workflow-ultimate`
- `platform/foundation-implementation`
- `platform/foundation-stabilization`
- `platform/optimized-ux-responsibilities`
- `platform/saga3-runs-ownership`
- `platform/saga4-workflow-polish`
- `platform/saga5-case-attributes-results`
- `platform/ux-workflow-second-saga`
- `platform/v2-phase1-foundation`
- `platform/v2-phase2-decision-center`
- `platform/v2-phase2-preserve-assignment-search`
- `platform/v2-phase3-data-hub`
- `platform/v2-phase4-certifi`
- `platform/v2-phase4-home`
- `platform/v2-phase5-transversal`
- `platform/v2-phase6-golden-regression`
- `test/workflow-end-to-end-phase7`
- `work`

## Final status

# HOLD — UNIQUE WORK NOT YET CONSOLIDATED

Motivo: WIP local D preservado y no incorporado. Además, la integración documental
a `main` y la eliminación de 103 ramas remotas certificadas esperan aprobación
explícita tras sendos rechazos de la revisión automática. No corresponde declarar CLEAN mientras persista trabajo
único potencialmente relevante. El baseline y el contexto maestro están
preparados; no se sacrificó trabajo único para obtener el resultado ideal.
