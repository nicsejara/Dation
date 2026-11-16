# UX07 — activación posterior y rollback

Esta entrega termina en un PR abierto: no autoriza merge, publicación, despliegue ni tráfico. No hay migración ni flag nuevo de UX07. Motores, Scheduler y demás gates mantienen su configuración anterior.

## Antes de integrar

1. Revisar el SHA del PR, los seis bloques, [QA](QA.md) y las capturas. FAST, FULL y required-gate deben estar terminales GREEN sobre ese candidato, sin conflictos. Conservar el clasificador actual; R3 queda fuera del autodeploy G6.
2. Obtener autorización expresa de merge. Verificar nuevamente HEAD y main antes de integrar. Registrar el SHA resultante y la CI post-merge por separado, sin duplicar una ejecución activa.
3. Para una futura activación, obtener GO separado de publicación/despliegue. No ejecutar comandos de esta propuesta durante la revisión de UX07.

## Publicación y despliegue controlados

Reutilizar los runbooks de Runtime V2/UX06 y los workflows existentes. No crear triggers, permisos o mecanismos nuevos. Antes de mutar, registrar en un recibo privado el digest, revisión READY y distribución de tráfico vigentes para rollback; no asumir que una revisión histórica sigue siendo actual.

Con GO_PUBLISH_IMAGE y main validado, la publicación manual existente acepta:

```sh
test "${GO_PUBLISH_IMAGE:-NO}" = UX07_PUBLISH_APPROVED
: "${DATION_UX07_VALIDATED_SHA:?SHA integrado completo con CI GREEN}"
gh workflow run runtime-v2-publish.yml --repo nicsejara/Dation --ref main \
  -f application_sha="$DATION_UX07_VALIDATED_SHA" -f confirm_publish=true
```

Verificar artefacto, SHA y digest remoto inmutable. Desplegar ese digest mediante el procedimiento aprobado, inicialmente sin promoción de tráfico; comprobar autenticación, salud y navegación. Mantener min_instances=0, CPU por solicitud, límites existentes, ejecución de motores/admisiones cerradas y Scheduler OFF según los gates vigentes. UX07 no requiere IAM nuevo ni SQL.

Smoke visual propuesto: Home seis tarjetas → landing/Decision Center filtrado → Core01/02/03 (guardar/reintentar, CSV local y guard), Previous conservando borrador → Graph con estados reales → D1/D2 abrir, segundo click cerrar, conmutar, X/Escape/exterior → configuración/dashboard y retorno a la misma corrida. Comparar escritorio y móvil con la evidencia del PR. No ejecutar optimizadores para validar CSS.

Promover tráfico únicamente con autorización específica, después de comprobar la revisión y el rollback capturados. No usar `apply` ni modificar protección de release como atajo.

## Rollback

Ante una regresión visual o de navegación, devolver tráfico a la revisión READY/digest capturados previamente con el procedimiento ya aprobado. Conservar las identidades Case/Node/Run y los datos: UX07 no necesita rollback de base de datos. Revertir el PR con otro PR si se requiere retirar el código; ejecutar los gates correspondientes. No borrar recursos, cambiar flags de motores, reinicializar Supabase ni repetir migraciones como parte del rollback.

La reconciliación histórica UX04 `20261114225017` queda fuera de esta saga. Proyecto GCP anterior fuera de alcance. Ninguna operación productiva de este documento se ejecutó para UX07.
