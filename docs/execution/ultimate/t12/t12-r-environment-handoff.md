# T12-R — Handoff de environment

Fecha: 2026-10-29 (America/Buenos_Aires).

Este documento preserva exclusivamente metadata y resultados no sensibles para continuar T12-R en una nueva tarea. El estado sigue siendo **HOLD ENV / ACCESS**; no constituye aprobación de rollout ni del Production Pilot. No contiene credenciales, tokens, valores de secretos, service keys, URLs firmadas, dumps ni datos comerciales.

## Baseline, rama e identidad

| Referencia | Identidad al preparar este handoff |
| --- | --- |
| RC funcional certificado, sin modificar | `bd4da14bc1b8125a6fcd13dcb6475911698224d3` |
| Baseline T12 / `main` local | `6773309350c40a9ec23348a2914927d37d6c18c3` |
| `origin/main` observado antes de publicar la recuperación | `ef997235a30251fbf7ae53690ed738092ee973d8` |
| Rama de recuperación | `recovery/t12-t12r-environment-20261029` |
| Rama de implementación conservada | `fix/t12-rollout-readiness-remediation` |
| HEAD de implementación T12-R, anterior al commit de este handoff | `b4b22f0454c116b58a5708c634d61860155cfef2` |
| Identidad de release propuesta por el cambio SQL | `RC ULTIMATE MVP T12-R1` |
| Hash del contenido funcional certificado | `fe9944b73f6a5b9f189d57477f1205fd73ca485ff9b92a7cf2fd272565e92138` |

El commit que incorpora este archivo es un sucesor documental de `b4b22f0`; su SHA se obtiene con `git log -1 --format=%H -- docs/execution/ultimate/t12/t12-r-environment-handoff.md`. La publicación autorizada abarca únicamente la rama de recuperación. No autoriza actualizar `main`, merge, PR, deploy ni operaciones productivas.

Commits locales que se preservan, en orden desde `origin/main`:

| Commit | Contenido |
| --- | --- |
| `32b85681907a8d7b7811a9e16ae1988941b3d3d1` | Checkpoint Ultimate MVP funcional hasta T10 |
| `bd4da14bc1b8125a6fcd13dcb6475911698224d3` | Freeze del RC certificado hasta T11 |
| `6773309350c40a9ec23348a2914927d37d6c18c3` | Dossier T12 y preflight de producción: 49 archivos en `docs/execution/ultimate/t12/` |
| `b4b22f0454c116b58a5708c634d61860155cfef2` | Cohorte server-authoritative T12-R: una migración y seis archivos de tests/fixtures |
| Commit de este archivo | Handoff documental para recuperar el environment |

Se verificaron los hashes de los **380 archivos funcionales certificados**, las **40 migraciones anteriores** y los **48 archivos enumerados en el manifiesto del dossier T12**. Permanecen intactos. El working tree estaba limpio al iniciar este handoff. No hubo cambios T12-R en matemática D1/D2, motores, Result Package, fingerprints, código de aplicación, frontend, Docker o configuración del pipeline.

Fuentes de continuidad en Git: `DATION_FINAL_MASTER_EXECUTION_PLAN.md`, [reporte T12](t12-rollout-report.md), [manifiesto del RC](release-candidate-manifest.json), [dossier T12](dossier-manifest.json) y [freeze T11](../t11/evidence/remediation/source-frozen.json). Este handoff agrega los resultados T12-R posteriores; no reescribe la evidencia histórica T12.

## Estado de los blockers

| Blocker | Resultado verificado | Pendiente |
| --- | --- | --- |
| A — GCP / Cloud Run 401 | Reproducido en este environment; la prueba externa del usuario confirmó OAuth válido y Resource Manager HTTP 200 | **Abierto: environment / secreto de red disponible para esta ejecución**. Falta verificar el target y la identidad efectiva desde el environment republicado |
| B — Backup / rollback | **PASS local**: restore SQL + ACL + objetos y rollback de aplicación en contenedores propios | **Recuperación productiva aún no verificada**: destino autorizado de backups pendiente; recovery point y revisiones/imágenes productivas sin comprobar |
| C — Cohort gating | **PASS de implementación y pruebas locales** | Migración sin aplicar en producción; workspace piloto autorizado pendiente; cohorte productiva sin activar |
| D — Storage JSON | **PASS**, corrección de MIME aplicada y comprobada antes del checkpoint de recuperación | No repetir la escritura de configuración ni la sonda por defecto; revalidar en lectura si hace falta |

El bloqueo de ejecución inmediata es A. Su resolución no convierte automáticamente B ni los prerrequisitos del piloto en PASS. No se ejecutó Production Pilot ni se crearon Runs productivos.

## A — GCP: evidencia y límite de la investigación

Target previsto: proyecto `dation-510100`, número `469052310590`, región `us-west1`; servicio API `dation-core`, worker `dation-core-worker`, Artifact Registry `cloud-run-source-deploy`.

La última comprobación HTTPS usó directamente el secreto de red configurado, sin imprimirlo, decodificarlo, validarlo localmente ni registrar su valor. No se cambiaron credenciales ni permisos IAM.

| Request GET | Hostname exacto | Resultado de este environment |
| --- | --- | --- |
| Proyecto `/v1/projects/dation-510100` | `cloudresourcemanager.googleapis.com` | HTTP 401, `UNAUTHENTICATED`, `ACCESS_TOKEN_TYPE_UNSUPPORTED` |
| API `/v1/projects/dation-510100/locations/us-west1/services/dation-core` | `run.googleapis.com` | HTTP 401, mismo motivo |
| Worker `/v1/projects/dation-510100/locations/us-west1/services/dation-core-worker` | `run.googleapis.com` | HTTP 401, mismo motivo |
| Registry `/v1/projects/dation-510100/locations/us-west1/repositories/cloud-run-source-deploy` | `artifactregistry.googleapis.com` | HTTP 401, mismo motivo |

Estos hostnames figuraban como autorizados; las respuestas provenían de Google y no fueron rechazos por hostname del proxy. El 401 no demuestra un problema de roles IAM ni de Cloud Run. No quedaron verificadas desde esta ejecución la identidad efectiva, sus permisos, las revisiones/imágenes actuales ni la capacidad requerida de deploy/rollback.

La lectura del health público en `dation-core-469052310590.us-west1.run.app` respondió HTTP 200; no informó una identidad de build verificable y no reemplaza las comprobaciones administrativas anteriores. Las otras verificaciones de proveedor usaron `api.supabase.com` para backups y `gijiinufjjurgfeehufj.supabase.co` para Storage.

**Confirmación externa del usuario:** `gcloud auth print-access-token` produjo un OAuth access token válido; Cloud Resource Manager respondió HTTP 200 para `dation-510100`. Esa prueba fue informada por el usuario y no ejecutada desde este environment. Por instrucción posterior, se cerró aquí la investigación de autenticación: el problema pendiente corresponde al environment/secreto de esta ejecución.

En la nueva tarea, reportar primero cada hostname y utilizar únicamente el secreto de red mediante el header Bearer, sin exponer su valor. Si un hostname resulta no autorizado, detener esa verificación y reportar únicamente el hostname faltante; no cambiar credenciales ni permisos para sortearlo.

## B — Restore y rollback local PASS; recuperación productiva pendiente

Se ejecutó una sola prueba focal del harness certificado de T11:

`test_ultimate_restore.UltimateRestoreTests.test_clean_slate_upgrade_restore_and_dual_compatible_image`

Resultado: **1 PASS**, 100.776 s de ejecución total. Se usaron PostgreSQL 17, API, worker y Storage de prueba propios, con datos sintéticos. La duración no representa un RTO productivo.

- Restore SQL con ACL incluidas; metadata y hashes de **39 tablas** preservados.
- **31 objetos privados** restaurados con paths, bytes y hashes idénticos, conservando bindings de Runs.
- Catálogo SQL anterior y posterior idéntico: SHA-256 `ecd5c5a2e2f25b96dd2709b72a5887460ec465f8980accd2033fbdacb55577d2`.
- Dump exclusivamente local de prueba: SHA-256 `0f3aed45e02b4306b0118d525237c6fd66138ea82fdbb5fc0385cb5f364575fb`. El dump no se incorpora a Git.
- Imagen de rollback real ejecutada por API y worker; lectores `assignment_v1`, `transport_plan_v1` y `day_scheduling_v1`, trabajos del worker y smokes locales de lectura/escritura: PASS.
- Sin downgrade de esquema ni borrado de Runs, approvals, artifacts o historial como mecanismo de rollback.

Identidades de imágenes **locales** verificadas:

| Uso | Image ID |
| --- | --- |
| Candidato API / worker | `sha256:b26cfedb7e7a70927171801dd89b44429b568b719528328cc5b99e78cf781ddb` |
| Rollback dual compatible | `sha256:610a317cbde6fe000d034bdb9dce28ad9f7309a948b13eb804d4483e6dd48041` |

Se verificaron en ambas imágenes **183 archivos frontend certificados: 180 estáticos y 3 templates**. Esto demuestra consistencia local, no la identidad del frontend previamente desplegado. Una evidencia antigua T11 de overlay del frontend apuntaba a un path incorrecto; no usarla como prueba de rollback a una UI productiva anterior. No se publicaron estas imágenes ni se verificaron sus revisiones productivas en T12-R.

La API de backups de Supabase (`api.supabase.com`) respondió HTTP 200 con `walg_enabled=true`, `pitr_enabled=false`, `backups=[]` y `physical_backup_data={}`. Esa respuesta no demuestra un recovery point utilizable ni permite asumir plan, frecuencia, retención, RPO o RTO.

El usuario confirmó que **el destino autorizado para backups productivos está pendiente**. No copiar datos comerciales/productivos fuera de sus ubicaciones actuales ni crear backups hacia nuevos destinos. Un backup SQL no incluye los bytes de Storage. La futura verificación productiva debe cubrir DB + ACL, objetos privados + paths + hashes + bindings y las revisiones reales de API/worker/frontend, con restauración aislada y un destino previamente autorizado. El rollback debe cerrar nuevas admisiones, permitir drenar trabajos ya admitidos y conservar el esquema aditivo y la historia.

## C — Cohorte implementada y validada

Migración: `supabase/migrations/20261029040212_ultimate_pilot_cohort.sql`.

SHA-256: `dbc8278a887c9463d2e6cdb54d4a40d2e173d45636910b1869594661dfcaad18`.

El set pasa de 40 a **41 migraciones**. La nueva migración todavía **no se aplicó en producción**. La identidad propuesta `RC ULTIMATE MVP T12-R1` identifica esta adaptación SQL separada del RC funcional; los bytes de las imágenes de aplicación certificadas permanecen iguales.

- `dation_private.platform_release.ultimate_pilot_enabled` tiene default `false`.
- Allowlist privada `dation_private.ultimate_pilot_workspaces`, inicialmente vacía, con `workspace_id` y `enabled=false` por defecto.
- Autoridad de configuración exclusiva del operador de release/DB. RLS y revocaciones impiden que roles de aplicación, browser o `service_role` administren la allowlist. Un Admin del workspace no puede autoinscribirse.
- Helper privado `ultimate_pilot_allows(uuid)`; las capacidades requieren flags existentes **y** piloto habilitado **y** workspace inscripto/habilitado. No se reemplazan los controles de membresía y roles.
- Cinco funciones existentes reciben únicamente expresiones de gating: `t3_case_context`, `platform_ultimate_foundation`, `platform_ultimate_data_pack`, `platform_ultimate_execution` y `platform_ultimate_graph`. La migración exige coincidencias exactas y falla si las definiciones no son las esperadas.
- Kill switch global o por workspace: bloquea nuevas escrituras/admisiones; conserva lecturas históricas, aprobación de Runs existentes, replays idempotentes y finalización de trabajos ya admitidos.
- Query params, payload, workspace header y localStorage no amplían autorización.

Archivos de pruebas/fixtures del commit T12-R:

```text
backend/tests/integration/test_ultimate_pilot_cohort.py
backend/tests/e2e/test_ultimate_pilot_cohort.py
backend/tests/integration/test_ultimate_case_models.py
backend/tests/e2e/ultimate_setup_fixture.py
backend/tests/e2e/ultimate_data_fixture.py
backend/tests/e2e/ultimate_certification_support.py
```

Los fixtures inscriben únicamente su workspace sintético A; B continúa con comportamiento legacy. El reset local del harness preserva la configuración de release. **El workspace ID autorizado para el Production Pilot sigue pendiente de definición**; no se debe sustituir por un UUID de los fixtures ni habilitar cuentas existentes.

## D — Storage JSON PASS

Hostname del proveedor: `gijiinufjjurgfeehufj.supabase.co`. Bucket: `dda-inputs`.

La causa comprobada fue la lista de MIME permitidos: faltaba `application/json`. La sonda previa recibió HTTP 400 con error interno 415 `InvalidMimeType` / `invalid_mime_type`. Antes del checkpoint se agregó únicamente ese MIME a la configuración del bucket; se conservaron privacidad, nombre, límite **10 MiB (10485760 bytes)** y los cuatro MIME previos: `text/csv`, `application/csv`, `application/vnd.ms-excel`, `text/plain`.

Resultados de la sonda sintética ya ejecutada:

- Upload JSON HTTP 200; retrieve HTTP 200, MIME `application/json` y bytes canónicos idénticos.
- SHA-256 del objeto de prueba de 61 bytes: `9f49a77940c422927c1d32b9265a9c3f2eb2850db51979e61fbc7bc947d42bb3`.
- Intento de reemplazo corrupto sin upsert rechazado; bytes originales preservados.
- Lectura sin credenciales y ruta pública rechazadas; bucket privado.
- Objeto sintético eliminado y ausencia posterior verificada; cero Runs productivos, ningún dato comercial copiado.

Esta modificación de configuración fue realizada durante la remediación anterior; **no se repite durante el handoff**. No se cambió código de publicación, canonicalización, manifest, contrato de artifact ni `result_fingerprint`. Los focales locales de tenant/Run, corrupción, fingerprint y manifest también pasaron.

## QA ejecutado: 22 pruebas únicas PASS

Se cuentan los últimos resultados válidos de cada caso, no los reintentos. No se repitió T11 completo ni se ejecutó QA productivo.

| Suite o caso | Cantidad | Resultado y cobertura |
| --- | ---: | --- |
| `test_ultimate_pilot_cohort.UltimatePilotCohortSQLTests` | 6 | PASS: defaults cerrados, allowlist, roles, ACL/RLS, payload, kill switch e historial |
| `test_ultimate_case_models.UltimateCaseSQLTests` focales 10, 11, 12, 13, 14, 18, 24, 25 | 8 | PASS: ownership, Admin/Operator/Viewer, aislamiento, flags, permisos y archive/restore |
| `tests.e2e.test_ultimate_pilot_cohort.UltimatePilotCohortE2E` casos 01–05 | 5 | PASS: API y Chromium real, bypass, ambos kill switches, denegación de uploads y nuevas Runs, draining, replay, approvals y lectura |
| `tests.e2e.test_ultimate_d1_result.UltimateResultE2E.test_06_corrupt_missing_wrong_fingerprint_and_foreign_access_fail_closed` | 1 | PASS: integridad y aislamiento de resultados |
| `tests.e2e.test_ultimate_consumers.UltimateConsumerTests.test_07_full_json_missing_corrupt_artifact_is_explicit_failure` | 1 | PASS: export JSON falla explícitamente ante artifacts ausentes/corruptos |
| Restore/rollback focal identificado arriba | 1 | PASS: SQL/ACL, Storage e imagen dual compatible reales en local |

La sonda Storage del proveedor es evidencia adicional, no una de las 22 pruebas.

Incidencias del runner resueltas sin modificar producto: instalación de Playwright desde `backend/requirements-browser.txt` con hashes existentes; corrección del nombre de clase del focal de export; ajuste de la expectativa del test de upload cerrado a HTTP 404, que es el contrato existente `P0002`. Se verificó que ambos kill switches no escriben uploads ni Runs. El test E2E 02 pasó en su ejecución final aislada; el log previo de la suite conserva el fallo de expectativa inicial.

## Evidencia preservada y límites de portabilidad

Los archivos originales permanecían en `/workspace/work/dation-t12-r` al preparar este handoff. Esa ruta, sus logs, contenedores, imágenes y dumps locales **pueden no existir en la nueva tarea**. No se copiaron esos archivos en bloque. Este documento conserva sus resultados y las identidades mínimas para reconocerlos si sobreviven; los tests y la migración sí están en Git.

| Evidencia original | SHA-256 |
| --- | --- |
| `qa-results.json` | `c34fb815506f06b0b3fa1fa75fa45c0028e509d38b5de091eb8f32e545b2cf45` |
| `scope-preservation.json` | `b2cfbdf08e542989e8c670d6245e0c3dfe50598c992e654508d169ad4596479d` |
| `storage-json-apply.json` | `f86939d8dd133d41bceefd39443f2e44c7a83d00bcf363185bd3917c409629b9` |
| `gcp-explicit-host-recheck.json` | `67534a9d39375817c1693d5f7bc4f7c1ba1e9c529af11a871b286fa178c6b952` |
| `frontend-image-rollback-verification.json` | `40aca92efd2b8e48670ee2b594151893c8761213c0d4b1a966b2251180f57a18` |
| `cohort-sql.log` | `b66aeff58f619c32515f0b3bc168ce9abb624867e7955bff65df837b6c871b9d` |
| `auth-sql-focals.log` | `69db12b12004cf568832a62f650e7a758899b52323c99bda7a770f6964eaa824` |
| `cohort-e2e-final.log` — contiene el fallo de expectativa previo | `2fcf48dc6a0c5c683c2d9ac2dffcf74372c7b5e3fd197eae18a3d0a3e1b63fbf` |
| `cohort-kill-final.log` — caso 02 final PASS | `67c382cc0b51f3b9a2c2ded9d9f6d4f55c62cc5adc95b44e4e6c3182cf0c062e` |
| `storage-integrity-focals.log` — E8 PASS; error inicial del selector de E10 | `cc10546f1a41fc47bfec717d3e9f987933ff527f4f5d2995941998d2ac20d449` |
| `export-integrity-focal.log` — E10 final PASS | `0321571d6e1ce6a77db4362595b2bc570c9e0c8b0f9dd87174a2fc926447b25d` |
| `restore-rehearsal.log` | `8194b68e11a0ce14ffc43ce85b4edd785ec2b1b858cf6d2b4249fcd1e2252f8a` |

`recovery-checkpoint.json` fue inspeccionado: contiene metadata, referencias y hashes, sin valores de secretos. Se trasladó aquí únicamente la información necesaria; no se copia el archivo completo ni se arrastran sus flags históricos de autorización como si fueran el estado actual.

## Próximos pasos en la nueva tarea

1. Recuperar la rama publicada `recovery/t12-t12r-environment-20261029`, comprobar HEAD real, historial, working tree y que `b4b22f0` siga siendo ancestro. Comparar `origin/main` sin sobrescribir cambios remotos. No reiniciar T0–T11 ni hacer una auditoría general.
2. Leer este handoff, el Master Execution Plan y el dossier T12. Reutilizar resultados de QA documentados. Si faltan recursos locales necesarios para una verificación pendiente, reconstruir sólo el ensayo focal correspondiente; no presentar hashes de imágenes locales antiguas como imágenes disponibles en el nuevo environment.
3. Con el environment republicado, verificar únicamente el acceso GCP pendiente y el target real mediante la identidad autorizada: proyecto, API/worker, revisiones, imágenes, configuración no secreta y permisos efectivos necesarios. Reportar hostnames antes de requests. No volver a investigar autenticación en el environment anterior ni exponer el secreto.
4. Mantener explícitamente pendientes el workspace piloto y el destino autorizado de backups hasta que el usuario los defina. No crear una cohorte productiva ni copiar datos productivos hacia destinos nuevos. Completar la evidencia de recuperación productiva únicamente con acceso y destino autorizados.
5. Revalidar en lectura la configuración Storage y el estado de migraciones antes de cualquier futura operación. El MIME ya fue corregido; la migración de cohorte está preparada y probada, pero no aplicada. No activar el piloto por defecto.
6. Completar `docs/execution/ultimate/t12/t12-remediation-report.md`, todavía pendiente, con A–D, identidad R1, QA y riesgos. Sólo cerrar T12-R cuando todos sus gates reales estén demostrados; el PASS local no sustituye la recuperación productiva. La autorización de este handoff termina en su push a la rama de recuperación: no incluye merge, push de `main`, PR, deploy ni Production Pilot.
