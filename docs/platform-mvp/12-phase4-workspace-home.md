# Fase 4 · Workspace Home

La entrada autenticada `/app` responde qué requiere atención, qué continuar y dónde ir. El catálogo conserva `/app/ddas` y su diseño aprobado. No se implementan entitlements, Data Hub, Decision Center ni colaboración de fases posteriores.

El header muestra workspace y saludo con el nombre del perfil; usa la zona horaria del workspace sin añadir reloj. La sección de atención sólo aparece si hay versiones reales para revisar. Admins y operadores comparten actualmente la facultad de aprobar dentro del workspace; la Home describe ese alcance y no inventa owners ni asignaciones personales. Los lectores ven casos recientes sin solicitudes de aprobación.

`GET /api/platform/home` requiere Bearer y membresía activa, igual que las API existentes. El servidor fija user/workspace; no acepta identificadores de tenant del navegador como autoridad. La RPC `platform_home` sólo permite ejecución a service_role, vuelve a comprobar identidad confirmada, workspace y membresía activa y devuelve un snapshot STABLE de lectura:

- `recent_cases`: hasta tres casos activos/completados, por `last_activity_at DESC, id DESC`; excluye archivados. El estado se reconstruye con el historial real, usando la lógica existente de Assignment/Scheduling. La respuesta pública es compacta, sin resultados, configuraciones ni metadata de archivos.
- `attention`: total real y hasta cinco candidatos, considerando todos los casos activos, incluso los anteriores a esos tres recientes. Sólo la última versión completada, no aprobada ni sustituida, de Assignment/Scheduling. Scheduling exige el upstream Assignment vigente y aprobado. Una nueva versión puede requerir revisión aunque se conserve una aprobación anterior. Las corridas en cola/en ejecución, errores y casos archivados no se anuncian como listos para aprobar.
- `activity`: contrato explícito `{available: false, items: []}`. La Fase 10 implementará el feed transversal. No se infieren actores ni se presentan eventos de demostración como actividad real; la UI muestra un estado vacío.

Revisar abre el dashboard exacto de caso/nodo/corrida. Continuar abre el resultado de una ejecución pendiente/revisable o el mapa del caso según el estado real. Si una nueva versión está ejecutándose, falló o espera revisión mientras se conserva una aprobación anterior, se reanuda esa versión nueva; no se confunde con el siguiente nodo habilitado por la aprobación anterior. Las versiones de Scheduling con upstream sustituido se señalan como pendientes de actualización. Los enlaces son URLs válidas para recarga, pestaña nueva y atrás/adelante; se usa el owner existente de navegación sin duplicar entradas. No crea casos ni cambia el contexto de datos al mostrar la Home.

Accesos rápidos: Logística, Decision Center y Datos. Workspace sin casos recientes muestra una invitación a explorar DDAs. Carga, error con Reintentar y retorno a Inicio tienen estados distintos; al salir se cancela la lectura y se descartan respuestas antiguas. BFCache conserva listeners y renueva el snapshot al regresar. Todos los nombres/etiquetas se insertan como texto.

## Validación y publicación

Pruebas nuevas: Home vacía/catálogo, loading/error/retry/reentrada/BFCache, links con lineage real y una entrada de historial, labels no ejecutables y responsive. Dos E2E adicionales verifican límites/orden, lectura sin cambios de casos, identidad A/B, roles y bloqueo de RPC directa, además de versiones reales ejecutadas por worker, reemplazos, aprobación y archivo. El recorrido autenticado existente ahora comprueba Home -> dashboard -> back -> continuar con API/DB/worker reales.

Validación local: 357 unittest, 78 Node; tres browser focalizados, dos E2E de Home y recorrido autenticado real. Doce capturas sintéticas a 1440/1024/768/390, contraste y overflow verificados. La batería completa de navegador, SQL histórico y E2E del esquema final se exige al SHA del PR antes de integrar. Resultados exactos, commit, CI y revisiones de producción se registran en el PR y el informe de entrega; artifacts sintéticos/privados fuera del repositorio.

Migración `20261018110000_platform_home.sql`: sólo crea una función STABLE con privilegios mínimos y notifica el schema cache. No altera tablas, evidencia, permisos previos ni admissions. Aplicar antes del despliegue de API, con comprobación de definición ausente y hashes agregados de negocio antes/después. No repetir migraciones de identidad ni freeze. API y worker anteriores siguen compatibles durante el despliegue. Siguiente alcance: Fase 5, catálogo + entitlements.
