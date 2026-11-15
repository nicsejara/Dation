# UX06 — propuesta de activación manual y rollback

Estado de esta entrega: código para revisión. **No concede GO de integración, publicación, despliegue ni tráfico.** No se ejecuta ninguno de los comandos mutadores de este documento. Proyecto anterior fuera de alcance.

## Gates de revisión

1. Revisar PR, SHA completo, capturas y matriz [QA](QA.md). FAST, FULL y required-gate deben ser terminales GREEN en el mismo candidato. El clasificador vigente se conserva; los fixtures/tests nuevos elevan el cambio a R3 y excluyen autodeploy G6.
2. GO_MERGE explícito del propietario. Verificar de nuevo HEAD, ausencia de conflictos y CI. Tras integrar, verificar SHA y CI automática de main antes de publicar; no iniciar suites duplicadas mientras haya una activa.
3. UX06 no agrega migraciones ni flags. UX04/UX05 y sus contratos deben continuar presentes. La reconciliación histórica `20261114225017` es una tarea separada: **no repetir la migración, usar db push ni modificar su historial como parte de UX06**.
4. Guardar en recibo privado el SHA validado, digest, revisión READY y distribución de tráfico reales de rollback. `dation-core-00015-gap` es la última revisión informada por el propietario, no un destino que deba suponerse vigente al desplegar.

## Publicación: autorización separada

Reutilizar únicamente `runtime-v2-publish.yml`, sin modificar workflows, WIF/IAM, Cloud Build o triggers. Una ejecución manual después de GO_PUBLISH_IMAGE y del gate de main:

```sh
test "${GO_PUBLISH_IMAGE:-NO}" = UX06_PUBLISH_APPROVED
: "${DATION_UX06_VALIDATED_SHA:?SHA completo integrado con CI GREEN}"
gh workflow run runtime-v2-publish.yml --repo nicsejara/Dation --ref main \
  -f application_sha="$DATION_UX06_VALIDATED_SHA" -f confirm_publish=true
```

Verificar el artefacto oficial y el digest remoto inmutable; no reconstruir ni sobrescribir otra imagen ante una respuesta ambigua. La publicación no autoriza despliegue. No usar Cloud Shell Docker, Cloud Build, cuentas nuevas o credenciales permanentes.

## Preparación sin tráfico: autorización separada

GO_PREPARE_CLOUD_RUN permite preparar exclusivamente una revisión de `dation-core` en Runtime V2. Antes, lectura del estado real: tráfico sin release concurrente, revisión de rollback READY, imagen por digest, identidad runtime y secretos versionados. Registrar sólo campos seguros; no exportar valores de secretos ni configuración completa a GitHub.

```sh
test "${GO_PREPARE_CLOUD_RUN:-NO}" = UX06_PREPARE_APPROVED
: "${DATION_UX06_IMAGE:?Imagen del recibo oficial exclusivamente por digest}"
python3 - "$DATION_UX06_IMAGE" <<'PY'
import re, sys
assert re.fullmatch(r'us-west1-docker\.pkg\.dev/dation-runtime-v2-2026/dation-runtime/dation-core@sha256:[0-9a-f]{64}', sys.argv[1])
PY
gcloud run services describe dation-core --project=dation-runtime-v2-2026 --region=us-west1 \
  --format='table(status.traffic.revisionName,status.traffic.percent)'
gcloud run deploy dation-core --project=dation-runtime-v2-2026 --region=us-west1 \
  --image="$DATION_UX06_IMAGE" --no-traffic --tag=ux06-smoke \
  --min-instances=0 --max-instances=2 --cpu-throttling
```

Conservar entorno, Secret Manager, IAM, concurrencia, memoria y demás límites existentes. No cambiar flags SQL/runtime para habilitar UX06: consume el Unified Journey ya autorizado en UX04. Verificar explícitamente `DATION_CLOUD_EXECUTION_ENABLED=false`, despacho/admisiones cerrados y Scheduler OFF. No actualizar ni ejecutar Jobs. `apply` permanece bloqueado.

## Smoke manual sin motores

Sobre la URL exacta de la candidata, con cuenta existente y sin compartir credenciales por chat:

- Health, login/logout, cuatro niveles globales y tres pasos internos. Core01/02/03 y configuración/dashboard conservan sus rutas.
- Core01/02/03: Anterior local preserva el mismo formulario y sus gates; Core01 sale a overview con guard. Retorno compacto único Graph/Config/Dashboard/Center, con Case/Node/Run exactos y fallback explícito sin latest. Studio: rail sólo04/05/06 en Graph, Configuration y Dashboard, sin Editar Decision Case lateral; toolbar Graph conserva esa acción. Graph inicialmente cerrado: sólo D1/D2, tres badges, dependencia real y `+` ilustrativo. Abrir/cambiar/cerrar por click, teclado, Escape y X; sin ejecución ni cambio de URL al seleccionar.
- Resumen readonly con el Case/Model/Pack/owners reales; selector Case paginado. Verificar Core02/Core03 y retorno. Con runs, cancelar el modal de derivación y comprobar que el original permanece intacto.
- Viewer readonly y archivados sin acciones mutadoras; Anterior sigue disponible. Back/Forward y CSV/draft: cancelar salida mantiene el DOM/File, confirmar no implica guardado remoto. Histórico con Case/node/run exactos. No crear ni aprobar corridas productivas para probar UX06: la evidencia D1/D2 de este PR es local.
- 1536/1280/1024/768/390/320: rail216/gap20 donde corresponde, círculo y flechas dentro de content, panel sin solape, ningún overflow horizontal. Verificar que no haya errores JS.

NO-GO: digest/SHA distinto, drift de tráfico/identidad/secretos/flags, autorización insuficiente, fallo de login/permisos/linaje, contratos UX04 ausentes, motores habilitados o regresión visual/geométrica. No corregir infraestructura ni datos incidentalmente.

## Promoción y rollback: autorizaciones separadas

Sólo después de smoke PASS y GO_PROMOTE_TRAFFIC:

```sh
test "${GO_PROMOTE_TRAFFIC:-NO}" = UX06_PROMOTE_APPROVED
: "${DATION_UX06_READY_REVISION:?Revisión exacta READY del recibo y smoke PASS}"
gcloud run services update-traffic dation-core --project=dation-runtime-v2-2026 --region=us-west1 \
  --to-revisions="$DATION_UX06_READY_REVISION=100"
```

Verificar nueva100, login y Graph sin motores. Preservar escala0–2, CPU por solicitud, presupuesto/alertas/spend cap existentes; no son un techo económico garantizado. Build, Registry, solicitudes y retención pueden generar costos sólo en la futura activación autorizada.

Rollback autorizado: volver 100% a la revisión UX04 exacta guardada y todavía READY mediante el mismo update-traffic, con el valor explícito de rollback del recibo. **No desactivar Unified Journey**, no tocar Supabase/flags/historial SQL, ni borrar Cases, Packs, Runs o snapshots. UX06 no requiere rollback de datos. Conservar las evidencias y retirar un tag/candidata sólo con autorización específica. Ninguna de estas operaciones se realiza durante esta implementación.
