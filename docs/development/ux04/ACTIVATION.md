# UX04 — activación manual, no ejecutada

**CODE_READY_DB_ROLLOUT_PENDING.** Este documento no concede GO. No se aplicó SQL productivo, publicó imagen, desplegó, promovió tráfico ni cambió Billing, IAM, Jobs, Scheduler o G6. No usar `apply`. El proyecto anterior permanece fuera de alcance.

## 1. Revisión e integración (GO_MERGE separado)

- Revisar PR, matriz AC y capturas. HEAD exacto debe coincidir con FAST/FULL/required-gate GREEN.
- R3/R4 queda excluido del autodeploy de UX según G6 existente. No reclasificar ni modificar sus guards.
- Sólo el propietario puede autorizar merge. Tras él, verificar el SHA de main y su gate automático; no publicar un SHA distinto al validado.
- Guardar SHA, run de CI, digest/revisión de rollback y tráfico actual en un recibo privado. No imprimir credenciales ni configuración completa.

## 2. Migración única (GO_APPLY_SUPABASE_MIGRATION separado)

Supabase DDA: `gijiinufjjurgfeehufj`. No recrear DB, resetear, modificar datos operativos históricos ni repetir migraciones anteriores. Se conserva la dispensa expresa de backup restaurable para este entorno de pruebas; la migración es aditiva y el rollback no borra datos. No se requiere contratar Pro para revisar este PR.

En el checkout exacto revisado:

```sh
git rev-parse HEAD
sha256sum supabase/migrations/20261114225017_unified_decision_journey.sql
```

Después del GO SQL, aplicar **sólo** ese archivo íntegro mediante SQL Editor del proyecto confirmado. Incluye BEGIN/COMMIT, timeouts, RLS, grants y reload de PostgREST. No usar `db push` indiscriminado: podría incluir migraciones históricas pendientes de reconciliar. Registrar esta versión y checksum en el historial de migraciones siguiendo el mecanismo del proyecto, sin alterar entradas anteriores. Si la versión ya consta, comparar el checksum y los objetos; no reaplicarla a ciegas.

Comprobaciones posteriores de sólo lectura:

```sql
select to_regprocedure('public.platform_decision_journey(uuid,uuid,text,jsonb)');
select unified_journey_enabled, ultimate_foundation_enabled, ultimate_data_pack_enabled
from dation_private.platform_release where singleton;
select n.nspname,c.relname,c.relrowsecurity,c.relforcerowsecurity
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='dation_private' and c.relname in
 ('journey_preparations','journey_uploads','journey_case_events');
select has_function_privilege('anon','public.platform_decision_journey(uuid,uuid,text,jsonb)','EXECUTE') as anon_must_be_false,
 has_function_privilege('authenticated','public.platform_decision_journey(uuid,uuid,text,jsonb)','EXECUTE') as authenticated_must_be_false,
 has_function_privilege('service_role','public.platform_decision_journey(uuid,uuid,text,jsonb)','EXECUTE') as server_must_be_true;
```

**NO-GO:** objetos ausentes, grants públicos, RLS sin forzar, discrepancia de versión, flag activado inesperadamente o bucket público/incompatible. Conservar `unified_journey_enabled=false` hasta completar el gate de activación. No agregar nuevos buckets/roles GCP ni cambiar contratos Storage: se usa el bucket privado de inputs actual con CSV/JSON y límite 10 MiB.

## 3. Publicación manual de imagen (GO_PUBLISH_IMAGE separado)

La ruta existente sigue siendo `runtime-v2-publish.yml`. Una sola ejecución manual después de validar main; no builds Cloud Shell/Cloud Build ni triggers nuevos.

```sh
: "${DATION_UX04_VALIDATED_SHA:?Asignar el SHA completo con CI GREEN y merge autorizado}"
test "${GO_PUBLISH_IMAGE:-NO}" = UX04_PUBLISH_APPROVED
gh workflow run runtime-v2-publish.yml --repo nicsejara/Dation --ref main \
  -f application_sha="$DATION_UX04_VALIDATED_SHA" -f confirm_publish=true
```

Esperar la ejecución existente, obtener su recibo y comprobar SHA, imagen y digest remoto inmutable. Si hay un intento interrumpido, recuperar el mismo recibo/imagen; no volver a construir ni sobrescribir una etiqueta. La imagen y los logs/Registry pueden tener costo. El presupuesto USD5 no es suspensión automática ni un límite garantizado.

## 4. Preparar revisión sin tráfico (GO_PREPARE_CLOUD_RUN + GO_ENABLE_NEW_STAGING_FEATURE separados)

El helper Rapid que conserva exactamente el entorno existente sirve para preparar una revisión con UX04 OFF. **Activar UX04 requiere además un env nuevo y un flag SQL**, por lo que no basta sólo con publicar una imagen. No editar un recibo de preparación anterior ni modificar su revisión después del snapshot: se invalidaría su protección contra drift.

Con GO específico para una candidata UX04 ON, el propietario puede realizar una preparación manual única con el digest ya verificado. Esta operación está fuera de este PR ejecutado. Se conservan los restantes env/Secret Manager/IAM/Jobs. Antes, obtener por lectura la revisión exacta con 100% y guardarla para rollback; si hay tráfico repartido o una release concurrente, detener.

```sh
test "${GO_PREPARE_CLOUD_RUN:-NO}" = UX04_PREPARE_APPROVED
test "${GO_ENABLE_NEW_STAGING_FEATURE:-NO}" = UX04_STAGING_APPROVED
: "${DATION_UX04_IMAGE:?Imagen del recibo oficial, exclusivamente por digest sha256}"
python3 - "$DATION_UX04_IMAGE" <<'PY'
import re,sys
assert re.fullmatch(r'us-west1-docker\.pkg\.dev/dation-runtime-v2-2026/dation-runtime/dation-core@sha256:[0-9a-f]{64}',sys.argv[1])
PY
gcloud run services describe dation-core --project=dation-runtime-v2-2026 --region=us-west1 \
  --format='table(status.traffic.revisionName,status.traffic.percent)'
gcloud run deploy dation-core --project=dation-runtime-v2-2026 --region=us-west1 \
  --image="$DATION_UX04_IMAGE" --no-traffic --tag=ux04-smoke \
  --min-instances=0 --max-instances=2 --cpu-throttling \
  --update-env-vars=DATION_UNIFIED_JOURNEY_ENABLED=true
```

No ejecutar el bloque sin ambas autorizaciones. Registrar revisión nueva exacta, URL del tag y digest; confirmar antigua100/candidata0 y revisión READY, cuenta runtime, secretos versionados y escala 0–2. Mantener `DATION_CLOUD_EXECUTION_ENABLED=false`, admisiones y despacho cerrados, Scheduler OFF. No ejecutar D1/D2 productivos en el smoke de UX04 sin otro GO.

Con el GO de flag ya concedido y los checks SQL PASS, habilitar únicamente:

```sql
begin;
set local lock_timeout='5s';
update dation_private.platform_release set unified_journey_enabled=true where singleton;
select unified_journey_enabled from dation_private.platform_release where singleton;
commit;
```

La revisión anterior no consume el flag nuevo; verificarlo en el SHA anterior antes de esta fase. No activar otras columnas de release. Si el rollout previo ya tiene UX04, resolver la compatibilidad antes de continuar.

## 5. Smoke por URL exacta, sin promoción

- `/health`, login y logout con usuario existente, sin enviar credenciales por chat. Health solo no certifica la experiencia.
- Breadcrumb cuatro niveles, Core01/02/03 y Studio04/05/06 con destinos disponibles reales.
- Usar exclusivamente CSV sintéticos en el piloto autorizado: descarga exacta, error estructural, dos candidatos válidos, refresh y finalización de un Case de prueba. Validado/candidato/publicado deben distinguirse.
- Confirmar datos en Graph, Data Owner, edición administrativa y regreso al origen. No arrancar motores. La validación D1/D2 real de este PR es local, no autorización productiva.
- Viewer no escribe; ningún archivo o secreto aparece en Storage público, URL o sessionStorage.
- Si login en el tag requiere un redirect Auth adicional, detener ese smoke y pedir GO puntual para ese ajuste; no reemplazar redirecciones válidas ni modificar Auth dentro de esta tarea.
- Verificar que el almacenamiento privado y sus cuotas soporten la duplicación transitoria stage→Case. No prometer costo cero: requests/egress, Registry, logs y almacenamiento retenido pueden facturarse.

## 6. Promover o revertir (GO_PROMOTE separado)

Guardar recibo con SHA/digest, nombres exactos de las dos revisiones, URL de smoke, resultado funcional, flags y tráfico. Releer estado inmediatamente antes de escribir; NO-GO ante drift/otra release. No usar `latest`.

```sh
test "${GO_PROMOTE_TRAFFIC:-NO}" = UX04_PROMOTE_APPROVED
: "${DATION_UX04_READY_REVISION:?Revisión READY exacta del recibo y smoke PASS}"
gcloud run services update-traffic dation-core --project=dation-runtime-v2-2026 --region=us-west1 \
  --to-revisions="$DATION_UX04_READY_REVISION=100"
```

Confirmar nueva100, repetir health/login/UX y registrar resultado real. Rollback autorizado: cerrar primero `unified_journey_enabled=false` en SQL y devolver 100% a la revisión anterior exacta, tras comprobar que sigue READY. Mantener tablas/journals/Case/Pack/linaje, nunca DROP, reset o borrado de snapshots. No modificar los motores, trabajos ya aceptados ni Billing. El flag runtime podrá volver a false sólo en una revisión controlada con su propio recibo, sin cambiar tráfico incidentalmente.

## 7. Limpieza sin proceso residente

La UI permite limpiar una preparación expirada e iniciar otra. La API `POST /api/platform/data-preparations/{id}/cleanup` opera sólo sobre preparaciones propias EXPIRED/CONSUMED, con sesión de negocio válida; nunca compartir el token por chat ni incluirlo en GitHub. Eliminar sólo objetos exclusivos de staging, registrar conteo y reintentar el mismo cleanup ante fallo. FINALIZING se recupera sobre el mismo Case: no limpiarlo ni crear un reemplazo.

TTL 24h es lógico, no una garantía de eliminación física automática. Revisar periódicamente con autorización los residuos de actores dados de baja/abandonados y preparar limpieza administrativa separada si fuera necesaria. No se creó Scheduler, Job ni servicio de limpieza. La cota actual es por actor: 5 sesiones pendientes/con bytes retenidos, 10 intentos × (raw10MiB + JSON10MiB), hasta 1.000MiB de stage más sus copias de Case, compartidos con la cuota real de Supabase. El piloto debe cargar archivos pequeños y limpiar después.
