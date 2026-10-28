# T12 — Controlled Rollout / RC Freeze / Production Readiness

Fecha de observación: **2026-10-28 UTC**. Alcance: exclusivamente T12, autorizado tras el GO de T11/T11-R. Fuentes: [Master Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md#t12--controlled-rollout), [T11 histórico](../t11/t11-execution-report.md) y [T11-R aprobado](../t11/t11-remediation-report.md).

**Resultado: HOLD antes de toda mutación productiva.** Se congeló y comprometió localmente el candidato exacto. El preflight identificó bloqueos de acceso GCP, recuperación productiva, activación por workspace y formato admitido por Storage. No hubo push, deploy, migraciones, cambio de flags, usuarios, datos, bucket, secretos, triggers ni infraestructura. No corresponde ROLLBACK porque este candidato no se desplegó.

## Release Candidate Identity

- Release: **RC ULTIMATE MVP**.
- Commit local del candidato: **`bd4da14bc1b8125a6fcd13dcb6475911698224d3`**, `Freeze certified Ultimate MVP release candidate through T11`.
- Parent/checkpoint T10: `32b85681907a8d7b7811a9e16ae1988941b3d3d1`.
- Árbol Git del RC: `96e66c5b988f7c776bfb08667129e9894ec965d4`.
- Branch: `main`. Árbol limpio inmediatamente después del commit del RC.
- Contenido certificado de aplicación, 380 archivos: SHA256 **`fe9944b73f6a5b9f189d57477f1205fd73ca485ff9b92a7cf2fd272565e92138`**.
- Los 380 archivos se compararon contra sus hashes T11-R **y contra los blobs del commit RC**. Los 311 archivos del dossier T11 y los 207 del manifest T11-R permanecen idénticos. No se normalizaron logs/CRLF históricos para modificar evidencia certificada.
- T12 no hizo cambios de aplicación. Este reporte, sus evidencias y los inputs piloto se conservan en un commit documental separado; no sustituyen la identidad del RC ni representan otra versión de aplicación.

[Manifest del RC](release-candidate-manifest.json), [verificación de fuentes y dossiers](evidence/source-and-dossier-verification.json), [identidad del commit](evidence/rc-commit.json). Los campos históricos «T12 no autorizado/no ejecutado» de T11-R permanecen como registro de aquella fase; la autorización y ejecución actuales constan en este dossier.

## Git / Build / Schema identities

| Identidad | Estado fijado |
| --- | --- |
| Git remoto, tras `git fetch origin` | `origin/main = ef997235a30251fbf7ae53690ed738092ee973d8`; el RC está 2 commits ahead / 0 behind. Sin divergencia remota. |
| API/worker local certificado | `sha256:b26cfedb7e7a70927171801dd89b44429b568b719528328cc5b99e78cf781ddb`, tag `dation-certification:t11-r-under-test`. Disponible en Docker local; `RepoDigests=[]`. |
| Worker en producción | Revisión, digest, recursos, service account y configuración **no verificables** por HTTP 401 de GCP. No se equipara la imagen local a una imagen desplegada. |
| Frontend | 183 archivos estáticos del manifest certificado, incluidos en la misma imagen FastAPI. [Manifest individual y hash agregado](evidence/frontend-content-manifest.json). No existe un build Netlify identificado en el RC. |
| Schema | Set ordenado de 40 archivos SQL con hashes T11-R. Último: `20261027190121_ultimate_copilot_consumers.sql`. Identidad del catálogo efectivo certificado y su SHA256 en el manifest; no se inventa un número único de schema. |
| Motor D1 / D2 | `transport_plan 2.0.0` / `day_scheduling 2.0.0`. |
| Schemas de resultados | `transport_plan_v1:1`, `day_scheduling_v1:1`; lectores legacy `assignment_v1:1`, `scheduling_v1:1`, `dispatch_v2:2`. |
| Assemblers | `RESULT_ASSEMBLER_D1_V1`, `RESULT_ASSEMBLER_D2_V1`. |
| Registry / graph | `DATION_RESULTS_REGISTRY_V1`, `ULTIMATE_DOMAIN_V1`, `ULTIMATE_DECISION_GRAPH_V1`. |
| Canonical / normalizer / Transit | `DATION_CANONICAL_V1`, `DATION_INPUT_NORMALIZER_V1`, `DATION_TRANSIT_V1`. |
| Contratos / IA | Result contract v1; `transport_demand_v1`, `transport_resources_v1`, `normalized_logistics_input_v1`; `decision_context_v1`; prompt `ULTIMATE_APPROVAL_COPILOT_V1`; reasons `DATION_REASONS_V1`. |
| Knowledge | Nueve documentos, hashes exactos preservados en el manifest. |

El registry público conserva los valores `implemented=false/available=false` para Ultimate tal como fue certificado. El resolver privado del worker reconoce las identidades exactas D1/D2; sus admissions dependen de flags SQL. No se modificó ese registry para simular readiness productiva.

## Production Preconditions

| Precondición | Observación / resultado |
| --- | --- |
| Target Supabase | **Verificado:** proyecto `gijiinufjjurgfeehufj`, nombre DDA, región `us-west-2`, `ACTIVE_HEALTHY`, PostgreSQL 17.6; coincide con el hostname configurado. |
| Target Cloud Run | Runbook/URL señalan proyecto `dation-510100`, número `469052310590`, región `us-west1`, servicios `dation-core` / `dation-core-worker`. La URL pública responde; la identidad administrativa del proyecto y las configuraciones actuales quedan **sin verificar**. |
| Acceso administrativo GCP | GET del proyecto y ambos servicios: **401 UNAUTHENTICATED / ACCESS_TOKEN_TYPE_UNSUPPORTED**. No se cambió ni imprimió ninguna credencial. La presencia de una variable no constituye acceso válido. |
| Salud pública actual | `/health` 200, `{"status":"healthy"}`. No contiene identidad de build. `/app` 303 a `/login`; `/api/platform/home` 401 sin token. |
| Ultimate actual | `/api/platform/ultimate-foundation/capabilities` 404. Catálogo sin Models, columnas de cohorte ni funciones Ultimate. Esto es compatible con el baseline previo; no se presenta como falla del RC desplegado. |
| Drift de schema | **Baseline reconocido:** las 101 definiciones de funciones, ACL/config/security-definer coinciden con T0 observado. Siete categorías completas coinciden con el catálogo post-T1; la única diferencia de función es `platform_home`, cubierta por la migración Home pendiente. |
| History de migraciones | Diez entradas hasta `20261005012207`, aunque el catálogo tiene expansiones posteriores. Esta diferencia ya estaba reconocida. No se hizo replay ni history repair. |
| Storage | `dda-inputs` privado, límite 10 MiB; MIME permitidos CSV/Excel/texto, **sin `application/json`**. Bloquea el preflight certificado de publicación normalizada y artifacts JSON. |
| Secrets/config productivos | Nombres esperados revisados en el código; referencias, disponibilidad y valores en Cloud Run **no verificados** por el 401. No se volcaron secrets ni se trató una service key como sesión de usuario. |
| Cohorte / rollback / backup | **HOLD**, por los motivos detallados abajo. |
| Netlify | Arquitectura RC: frontend nativo servido por FastAPI y empaquetado en Docker. No se encontró config/site ID Netlify; no hay verificación administrativa de un sitio externo y no se creó ni modificó uno. |

Evidencia: [proyecto](evidence/supabase-project-observed.json), [Cloud Run API](evidence/cloud-run-api.json), [worker](evidence/cloud-run-worker.json), [salud](evidence/production-health.json), [rutas públicas](evidence/production-public-route-observations.json), [catálogo completo sin datos comerciales](evidence/production-catalog-complete.json), [reconocimiento de migraciones](evidence/migration-preflight-recognition.json), [Storage](evidence/production-storage-settings.json).

Se aplicaron las Skills de runtime cloud y Supabase/Postgres a readiness, lectura de metadata y preservación del esquema certificado. La lectura HTTPS del changelog de Supabase fue bloqueada por la política de red; se consultaron las herramientas/documentación del conector sin eludir esa política. No hubo implementación Supabase. Skills UI: N/A, sin cambios de UI. No hubo agentes ni nueva auditoría transversal.

## Backup / Rollback

RESTORE11 certificó localmente `pg_dump -Fc` con ACL, copia independiente de objetos privados, `pg_restore --exit-on-error`, comparación de catálogo/grants/datos/hashes y lectura de ambas cohortes. **Ese ensayo no es un backup de producción.**

El GET administrativo de backups productivos devolvió HTTP 200: `walg_enabled=true`, `pitr_enabled=false`, `backups=[]`, `physical_backup_data={}`. No se obtuvo un recovery point verificable. Esto no afirma que no exista otra copia externa; afirma que ninguna está identificada y disponible en esta ejecución. [Respuesta](evidence/supabase-backups.json).

Tampoco se identificó una copia productiva recuperable de los bytes privados de Storage. Un backup PostgreSQL/metadata no reemplaza esa copia. No se exportaron datos comerciales para el dossier.

Rollback local certificado: **`sha256:610a317cbde6fe000d034bdb9dce28ad9f7309a948b13eb804d4483e6dd48041`**, tag `dation-certification:rollback-dual-compatible-t11`; disponible localmente, `RepoDigests=[]`. No se verificó una imagen publicada ni una revisión Cloud Run ejecutable para recuperarse en producción.

Se preserva la errata T11-R: el overlay temporal de Config apuntó al directorio equivocado. La evidencia acredita readers/backend/worker duales, **no una reversión visual a la Config antigua**. No se utilizó esa afirmación histórica para aprobar el gate productivo.

## Migrations Applied

**Ninguna.** Los 40 archivos certificados conservan sus hashes. El preflight reconoce nueve pendientes, en este orden:

1. `20261026010000_home_decision_owner_attention.sql`
2. `20261026143813_ultimate_foundation.sql`
3. `20261026144259_ultimate_result_artifacts.sql`
4. `20261026161050_ultimate_case_models.sql`
5. `20261026184655_ultimate_progressive_data_pack.sql`
6. `20261027033128_ultimate_decision_graph.sql`
7. `20261027140333_ultimate_result_publication.sql`
8. `20261027175943_ultimate_day_scheduling.sql`
9. `20261027190121_ultimate_copilot_consumers.sql`

Las primeras 31 migraciones históricas no se reaplican por estar ausentes del ledger remoto. No se ejecutó baseline, SQL de reparación, backfill improvisado, borrado ni downgrade. La comparación post-migración con el catálogo certificado está **NOT RUN**, porque los gates previos impiden mutar producción. El hallazgo MIME no se corrige con una migración nueva dentro de esta fase.

## Backend / Worker Deployment

**BLOCKED / NOT DEPLOYED.** El candidato local conserva los 327 archivos backend/assets contrastados dentro de la imagen en T11-R. La comprobación Docker T12 confirma disponibilidad de la imagen y del rollback, sin reconstruirlas.

GCP 401 impide verificar revisión actual, command/args del worker, CPU/memoria/concurrencia, secrets refs, leases, imagen rollback, permisos y orden efectivo del pipeline. Los datos históricos de configuración no sustituyen estas verificaciones. No se ejecutaron scripts antiguos de despliegue ni se ajustó infraestructura.

## Frontend Deployment

**NOT DEPLOYED.** Los 183 archivos certificados permanecen iguales. API y frontend pertenecen a la misma imagen; no se asumió un frontend independiente en Netlify. Para retomar, debe observarse el orden real del pipeline: schema compatible, worker/API compatibles y UI servida con capacidades cerradas hasta que los gates permitan el piloto. Un push de `main` sin esa comprobación sería prematuro.

## Feature Gating

El candidato tiene tres flags booleanos en la fila singleton de `dation_private.platform_release`:

- `ultimate_foundation_enabled`: Models/Cases y sus capacidades.
- `ultimate_admissions_enabled`: admisión D1/D2.
- `ultimate_scheduling_admissions_enabled`: admisión D2.

Son **globales**, no contienen selector de workspace/cuenta/cohorte. La RPC foundation combina su flag con DDA Logística y roles; execution combina sus flags con DDA, roles, owners y contexto. Ninguno de esos checks representa una allowlist de piloto. `workflow_version` separa Cases legacy/Ultimate, pero no selecciona clientes autorizados para el rollout.

Fuentes: [foundation](../../../../supabase/migrations/20261026161050_ultimate_case_models.sql), [execution D2](../../../../supabase/migrations/20261027175943_ultimate_day_scheduling.sql), [rutas](../../../../backend/app/platform/ultimate_routes.py), [admisión](../../../../backend/app/services/ultimate_run_service.py).

Activar los flags permitiría Ultimate a otros workspaces habilitados y con permisos, sin limitarlo a 1–3 pilotos. Deshabilitar su DDA perjudicaría Legacy y no es una solución aceptable. No se improvisó una tabla/flag/migración ni se parcheó el candidato congelado. **HOLD: falta un mecanismo de activación por cohorte certificado.**

En producción los tres campos Ultimate todavía no existen. Los únicos flags observados son `admissions_open=true` y `workflow_gates_enabled=true`, intactos. No se creó ningún tenant ni se eligió una cuenta comercial como piloto.

## Legacy Compatibility

**Certificación T11/T11-R preservada; smoke productivo autenticado NOT RUN.** El registry conserva assignment_v1, scheduling_v1 y dispatch_v2. RESTORE11 verificó readers históricos, resultados/approvals/historia y jobs legacy + D2 con backend dual.

T12 no convierte Cases, Orders/Fleet ni Runs históricos. Las rutas públicas existentes responden, pero eso no demuestra lectura de todos los Cases, exports o historial con permisos reales. No se declara un PASS productivo sin esos checks.

## Production Smoke

**SMOKE12: BLOCKED_NOT_RUN**, tanto `read-only` sobre una cadena sintética como `pilot-write`. No existe deployment observation que identifique el RC en Cloud Run, ni workspace/actor piloto identificado con sesión autorizada. Los gates de backup, rollback, Storage y cohorte tampoco pasan.

No se fabricó un manifest de despliegue con la imagen local, ni se reutilizaron UUIDs/usuarios del sandbox como identidades productivas. No se sustituyó el smoke por `/health` 200.

La interfaz certificada sigue en [ultimate_release_smoke.py](../../../../backend/tests/e2e/ultimate_release_smoke.py). Al retomar exige manifest con imagen observada, workspace real, nombre de variable de token, creación sintética explícita y cadena D1→review→approve→D2→review→approve. Las comprobaciones adicionales de UI, roles/tenant, IA y métricas se registran junto al CLI; su PASS por sí solo no acredita todos esos puntos.

## D1 Validation

**Producción: NOT RUN.** No hay nuevo Run ID, duración ni fingerprint productivo.

Se preserva la evidencia T11-R: dataset real de escala 500 órdenes/50 recursos/31 días, 128 Trips, golden completo y 83 artifacts; fingerprint del fixture `6de1eeb6b9c20c9a4c9ac5bd07db035bbebed972cba7ef3bb84e34848f858014`. Ese hash corresponde al contexto/IDs del fixture y no debe imponerse a una Run productiva con otros IDs.

El piloto deberá comprobar result schema/engine, COMPLETED, publication READY, hash recalculado, lectura de artifacts, Sankey/dashboard, CSV/JSON, review y aprobación vinculados a su propia Run/fingerprint.

## D2 Validation

**Producción: NOT RUN.** Se preserva la certificación de Scheduling sobre upstream real aprobado, incluida la escala de 100 Trips; no se convierte el ensayo de serialización de 1.000 filas en una promesa de engine de 1.000 Trips.

El piloto deberá usar exactamente `source_transport_plan = {run_id, result_fingerprint}` del D1 aprobado, conservarlo sin reasignar, verificar fechas/ciclos/servicio, artifacts READY, Gantt/export/review y aprobación D2. La segunda D2 debe conservar el upstream D1 aprobado; reejecutar D1 sólo invalida vigencia downstream, manteniendo el historial.

## Result Integrity

El layout certificado permanece privado en `dda-inputs`:

- Inputs: `{workspace_id}/normalized/{dataset_id}/{canonical_sha256}.json`.
- Resultados: `{workspace_id}/runs/{run_id}/{kind.lower()}/{part_key}/{content_sha256}.json`.
- Particiones de resultados: hasta 1 MiB / 100 filas; binding de workspace, Run, Core, hash y manifest antes de READY.

El bucket actual no admite `application/json`. [private_bucket](../../../../backend/app/services/case_data_pack_service.py:61) rechaza esa configuración explícitamente; [result_artifact_service](../../../../backend/app/services/result_artifact_service.py:62) publica JSON. El requisito incumplido se constató mediante metadata y código certificado, **sin intentar una carga productiva fallida**.

No se publicaron packages ni se observaron errores de hash de nuevas Runs productivas. Integridad productiva queda pendiente; byte/schema equivalence T11-R y archivos fuente permanecen certificados.

## Approval / Lineage

No hubo approvals, invalidaciones, Runs ni cambios de ownership en producción durante T12. Evidencia previa preservada; validación productiva bloqueada.

Al retomar: review del fingerprint actual; actor Owner/Admin real; D1 aprobado vigente; D2 exacto; reload/history/export con mismo resultado; denegación de Viewer y de tenant ajeno; reaperturas sin pérdida de Runs o approvals históricos. Ninguna entidad Branch ni reconstrucción manual de vigencia.

## Security Checks

| Check | Resultado T12 |
| --- | --- |
| RLS en tablas públicas existentes | **19/19 habilitadas**. Lectura de catálogo; no equivale a smoke completo de permisos. |
| Bucket público | `dda-inputs.public=false`. No se publicaron artifacts ni se generaron enlaces públicos. |
| Acceso anónimo | Home API 401, `/app` redirige a login. Ultimate 404 por no estar desplegado; ese 404 no certifica autorización de sus futuros endpoints. |
| Session / tenant / roles | **NOT RUN en producción**; no hay sesión de piloto ni se suplantó una con service role. |
| Service role sólo server-side / secrets en build | Candidato certificado preservado; configuración e imagen productiva no inspeccionables por 401. No se imprimieron secretos en el dossier. |
| Grants / funciones | ACL/config/security-definer de 101 funciones iguales al baseline remoto T0 reconocido. No hubo GRANT/REVOKE/RLS changes. |

## Performance Checks

**No se repitieron suites de engine/QA completas:** el RC tiene exactamente los bytes certificados. Resultados previos, no mediciones productivas nuevas:

- B-PY T11-R: 688 tests ejecutados, 680 IDs únicos; 8 heredados duplicados, 0 fallos/errores/skips.
- PERF5 cold: p50 **61,6323 s**, peor **64,2408 s** para el subtotal fixture+engine+assembler.
- Dos ejecuciones first-cold de API+worker en la imagen certificada: **88,1741 s / 86,7984 s**, desde antes de admisión hasta completed con publicación/recuperación de 83 artifacts.
- Worker de ensayo: 2 CPU / 1 GiB, peak **727,43 MiB**. Margen temporal mínimo contra 90 s: **1,826 s**. Muestra pequeña; no es SLO productivo universal.
- CONSISTENCY11 4 PASS, E8 8 PASS; 200 focales PASS; 18 schemas y golden completo idénticos. Node153, browser290, SQL162 y evidencia E2E no afectada se conservan, no se reetiquetan como ejecuciones T12.

T12 ejecutó: comparación de 380 fuentes con Git y manifest, 40 SQL, nueve knowledge docs, 311+207 archivos de evidencia; lectura de metadata y health; normalización local de diez CSV positivos y rechazo esperado de un duplicado negativo del piloto. **Cero ejecuciones de engine y cero Runs productivas en T12.**

Health productivo observado: **10,759 s** para una petición; las tres lecturas siguientes tardaron 0,23–0,29 s. No es una medición D1/D2 ni prueba de regresión de solver. Latencia de Run, retrieval, dashboard, artifacts e IA productivos: **NOT MEASURED**. No se amplía cohorte basándose en estos GETs.

## Observability

Pipeline: **sin push desde T12 y sin nuevo despliegue disparado por esta tarea**. El conector GitHub confirma el SHA remoto anterior y devuelve `statuses=[]`; eso no prueba éxito/fracaso de Cloud Build. Estado administrativo de Cloud Build/Run y revisión en servicio: **no observado**, por acceso GCP inválido.

Las capacidades existentes de `/ready`, `/metrics`, operaciones y logs deben observar admissions/worker/solver/publication/artifacts/approval/API5xx/frontend/latency/lease-retries durante el piloto. Requieren identidad admin o acceso cloud válido; no se falseó esa observación ni se desplegó una nueva plataforma.

Dation IA productiva: **NOT RUN**. Al retomar debe comprobarse `decision_context_v1` sobre Run/fingerprint y selected entity correctos, sin raw CSV innecesario, sin acciones/approvals ejecutables, con fallback seguro ante proveedor ausente. La lectura de historia de copilot no equivale a probar una respuesta nueva del proveedor.

## Rollback Readiness

**Gate productivo: FAIL / HOLD.** Antes de retomar deben existir:

1. Acceso administrativo GCP funcional y target/revisiones/pipeline observados por IDs reales.
2. Recovery point PostgreSQL y copia de objetos privados con inventario/hashes y restauración ejecutable; no sólo metadata de Storage.
3. Imagen dual-compatible disponible por digest publicado, revisión/traffic recuperable y rollback frontend explicitado dentro del alcance realmente ensayado.
4. Activación server-side de Ultimate limitada a workspaces/cuentas piloto, certificada antes de cambiar el RC.
5. Compatibilidad MIME de `dda-inputs` con CSV y JSON normalizado/artifacts, preservando bucket privado y entradas legacy, mediante configuración revisada/ensayada; no cambio improvisado en este HOLD.
6. Identidades reales del piloto, sesión autorizada y observación productiva de la cadena completa.

Una vez disponibles: revalidar identidad del RC y remoto; backup; migraciones reconocidas únicamente; verificar catálogo/RLS; desplegar worker/API compatibles mediante pipeline existente con Ultimate cerrado; verificar imagen; habilitar sólo cohorte controlada; SMOKE12 y observación. Cualquier revisión del RC debe tener diff, tests de frontera y nueva build identity explícitos.

Ante fallo después de activar: cerrar admissions Ultimate mediante mecanismo certificado; drenar/recuperar jobs según protocolo; volver a imagen dual-compatible si corresponde; preservar Runs, artifacts, approvals e historia; conservar schema aditivo. Nunca DELETE de Ultimate ni downgrade destructivo. Ningún rollback se ejecutó en esta fase.

## Pilot Cohort Recommendation

**HOLD**, no PILOT ni EXPAND por ahora. Objetivo posterior: 1–3 workspaces controlados, inicialmente uno, con datos sintéticos/no críticos. No hay workspaces productivos seleccionados ni cuentas inventadas.

Se prepararon [cinco escenarios locales](pilot/README.md), configuraciones y diez CSV válidos, más un CSV negativo. [Validación de entradas](pilot/input-validation.json): 10/10 normalizaciones PASS y 1/1 rechazo esperado. No se ejecutaron engines ni se crearon fixtures productivos permanentes.

| Escenario | Datos y comprobación preparados | Estado productivo |
| --- | --- | --- |
| A — 100% tercerizado | 70 pallets; EXTERNAL 26×2 + 30×1; 3 Trips, cobertura 70/70, costo ARS350. | NOT RUN |
| B — OWN + EXTERNAL | 1 pallet / 30 km; OWN 2/km ida+vuelta frente a EXTERNAL 300/viaje; elección OWN, ARS120. | NOT RUN |
| C — Capacidad insuficiente | 70 pallets; EXTERNAL 26×2; 52 asignados/18 residuales, costo ARS200, CAPACITY_GAP explícito. | NOT RUN |
| D — Reutilización OWN | Dos cargas de 26, una unidad OWN, 480 km; D2 salidas 2/4 de noviembre, disponibilidad 4/6, ciclo 2 días. | NOT RUN |
| E — Límites / excepciones | Disponibilidad ASSUMED explícita; ready=due 4/11, margen cero AT_RISK; duplicado de order_id rechazado antes de publicar. | NOT RUN |

Los valores esperados provienen de fixtures/oráculos ya certificados. Los hashes de contrato de la validación local pertenecen a Model Versions ficticias **sólo locales**; cada piloto real debe publicar su Model y obtener su contract hash real antes de subir archivos.

Clasificación preparada: **P0** seguridad/corrupción/decisión incorrecta; **P1** flujo bloqueado/resultado incorrecto; **P2** UX/performance grave; **P3** usabilidad/copy/polish; **P4** mejora futura. P0/P1 bloquean expansión; P2 exige evaluación; P3/P4 pueden ir a backlog. Registrar siempre workspace, Case/Run/fingerprint, build, schema, hora, evidencia y reproducción sin secretos.

## Known Issues

| ID | Severidad / gate | Hallazgo real |
| --- | --- | --- |
| T12-01 | P1 rollout / acceso | GCP rechaza la credencial configurada; no se pueden certificar deployment ni recuperación. |
| T12-02 | P1 rollout / recovery | Sin recovery point productivo verificable, copia de objetos ni rollback publicado/revisión ejecutable identificados. |
| T12-03 | P1 rollout / cohorte | Flags Ultimate globales; no existe selector certificado que restrinja la activación al piloto sin afectar Legacy. |
| T12-04 | P1 rollout / publicación | `dda-inputs` no permite JSON; el guard del candidato bloquearía inputs normalizados. |

La historia de migraciones incompleta y la migración Home pendiente son **estados reconocidos**, no discrepancias desconocidas ni una razón para reparar el ledger. No se observó corrupción, fuga de tenant o regresión nueva de engine; tampoco se declara su ausencia productiva sin smoke.

## Risks

- El pequeño margen cold del worker requiere verificar recursos reales y latencias productivas antes de expandir.
- Activar flags globales expondría capacidades fuera del piloto; no se acepta una ventana temporal abierta para crear sólo un Case.
- Un push podría accionar el pipeline antes de resolver schema/Storage/worker/rollback. Por eso se preserva localmente el RC.
- Una imagen local o un rebuild de igual Git SHA no demuestra por sí solo el digest desplegado ni su base/runtime; debe observarse la identidad efectiva.
- La evidencia de restore local prueba el procedimiento en sandbox, no la disponibilidad de backups actuales de clientes.
- No hay evaluación autenticada del frontend, IA ni permisos en producción; no se deduce de health/login.

## Deferred Backlog

No se agregan features ni se reabren decisiones visuales. Los cuatro blockers T12 son prerrequisitos para retomar este rollout, no mejoras opcionales ni trabajo de una nueva fase ejecutado aquí. Cualquier solución que modifique aplicación/migraciones requiere revisión explícita del RC y certificación de su frontera antes de desplegar.

Sólo después de piloto válido: clasificar feedback P2–P4, dimensionar observación según datos reales y proponer expansión por separado. No se autoriza automáticamente wide release ni una fase posterior.

## FINAL DECISION

| Gate | Resultado |
| --- | --- |
| Freeze / commit / identidad de aplicación / dossiers | PASS |
| Git sin divergencia / sin edición funcional T12 | PASS |
| Baseline de schema reconocido / hashes certificados | PASS predeploy; aplicación y verificación post-migración NOT RUN |
| Acceso/config productiva / rollback / backups | HOLD |
| Storage compatible / cohorte controlada | HOLD |
| Legacy + Ultimate SMOKE12 / D1 / D2 / integridad / approval-lineage / tenant / IA / performance productiva | BLOCKED_NOT_RUN |
| Push / deploy / activación / expansión | NO EJECUTADOS |

**HOLD — T12 requiere correcciones antes del Production Pilot.**
