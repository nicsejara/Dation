# Fase 10 · Auditoría y actividad

Las acciones nuevas se registran en la tabla existente `audit_events`, dentro de la misma transacción que cambia el recurso. No se reconstruyen eventos ni autores a partir de corridas históricas. Los eventos anteriores conservan sus valores; la proyección resuelve en lectura los IDs conocidos en metadata y los nombres de tipos anteriores.

## Captura y autoría

La migración `20261019120000_platform_audit_activity.sql` añade object_type, object_id, decision_case_id, node_id y event_key, todos opcionales para conservar el historial existente. Agrega tres índices, cuatro triggers y seis funciones nuevas. No reemplaza funciones de negocio ni cambia sus estados, cálculos o aprobaciones. Conserva las RLS y ACL anteriores, salvo que revoca UPDATE, DELETE y TRUNCATE de service_role sobre la tabla de auditoría. El trigger previo de inmutabilidad permanece. Product code sólo agrega eventos.

Los headers internos de actor y workspace se sobrescriben en el BFF con la autoridad verificada antes de llamar a REST. Los RPC conservan su contexto SQL autorizado. La captura revalida el actor cuando existe; no usa identidad proporcionada por el navegador ni atribuye la actividad del worker al creador de la corrida. Los eventos automáticos llevan source=system y actor nulo; sin un actor registrado se muestra esa ausencia. El ID del autor permanece aunque ya no haya un perfil/membresía disponible. El nombre mostrado se consulta del perfil actual; no constituye una copia histórica de su nombre.

- Workspace: creación, recuperación del workspace heredado y cambios de preferencias existentes.
- Miembros: invitación, aceptación, revocación, rol, deshabilitación/reactivación y actualización de responsabilidad. Los tipos persistidos `team.*` se conservan para compatibilidad y se proyectan como `member.*`.
- Datos: carga confirmada, validación persistida, archivo/restauración y eliminación completada. Validar un CSV local que no se guarda no inventa un dataset ni un evento. La eliminación fallida o pendiente no figura como completada; reintentar una operación completada no duplica el evento.
- Casos: creación, archivo/restauración y cambio de etiqueta. Una actualización del cache del workflow no crea actividad ficticia.
- Ejecuciones: admisión en cola, inicio, finalización y error por cambios reales de estado. Heartbeats y GET no generan eventos. Un worker no recibe una autoría humana inferida; una cancelación con actor verificado conserva esa identidad.
- Decisiones: la aprobación sigue registrada por la función transaccional vigente y conserva su idempotencia. `decision.submitted` describe la publicación automática para revisión de una corrida completada de Assignment/Scheduling, con caso disponible y linaje válido. La UI dice «El sistema dejó Assignment para revisión»; no hay un envío manual ni un estado nuevo.
- Exportación: generación de CSV/JSON desde la corrida persistida y autorizada. Se registra autor, corrida/caso/nodo, formato, cantidad de bytes y SHA-256; no el archivo completo. Un evento describe generación, no recepción o apertura por el usuario.

Los eventos nuevos de datasets y runs sólo incluyen metadata acotada. Nunca copian CSV, resultados, parámetros completos, errores crudos, credenciales ni tokens. La actividad pública aplica una lista de campos permitidos incluso a eventos antiguos; correos de invitaciones y metadata arbitraria no salen en esa proyección. El registro de configuración anterior conserva sus before/after para Admin; el feed sólo muestra la sección modificada.

## Lectura y navegación

`GET /api/platform/activity` exige membresía confirmada y activa, resuelta en servidor. Limita páginas a 50 y usa cursor compuesto fecha/ID para evitar repeticiones cuando llegan eventos nuevos. `case_id` se comprueba dentro del workspace y un caso ajeno responde 404. Admin, Operator y Viewer pueden consultar la proyección. Los RPC siguen siendo service-only.

Inicio muestra hasta cinco eventos, con autor/acción legibles, fecha según la configuración del workspace, enlace al caso y detalles técnicos secundarios. Sin grant de Logística sólo aparecen eventos transversales de workspace/equipo; la consulta SQL filtra la actividad del DDA. Si falla el feed, los casos y accesos de Inicio siguen disponibles y la actividad permite reintentar.

El detalle de Decision Center añade «Actividad del caso», un disclosure con carga independiente, paginación y reintento. Esta memoria del caso mantiene el acceso de la biblioteca transversal aun sin grant; ejecutar y exportar siguen exigiendo Logística. Al salir, recargar o cerrar el disclosure se cancelan solicitudes y se eliminan listeners. No hay un Audit Center global ni una segunda fuente de estado del workflow.

## Exportaciones

`POST /api/platform/activity/exports` genera el archivo usando el resultado guardado, no un resultado enviado por el cliente. Viewer conserva el permiso de exportación; el backend comprueba membresía y grant. El body sólo admite run_id, formato CSV/JSON y operation_id. Una operación repetida conserva un único evento; cambiar corrida/formato/contenido bajo la misma identidad produce conflicto. Un archivo inválido no se audita como generado.

Las columnas, filenames y protección contra fórmulas del CSV se conservan; una prueba compara bytes contra el exportador JS anterior para D1, D2 y el formato histórico, incluyendo nulos, separadores, comillas y saltos de línea. El JSON conserva el objeto guardado. La entrega del archivo queda condicionada a registrar la auditoría: si falla, la UI ofrece volver a intentar. No se persiste un archivo adicional ni se modifican datos, moneda, unidades o resultados históricos. Free universal continúa vigente.

## Verificación y publicación

Cinco E2E nuevos usan PostgreSQL 17, PostgREST, BFF, API y worker reales en un entorno aislado. Verifican estados, actores reales/sistema, headers de actor falsificados, inmutabilidad, aislamiento, cursores, lectura sin escrituras, metadata filtrada, eventos legados sin backfill, errores, eliminación, nuevo workspace, exportación Viewer, idempotencia y negación sin grant. El recorrido de navegador incluye ocho capturas a 1440/1024/768/390, contraste, teclado, XSS, paginación, reintento y exportaciones reales. Chromium añade una regresión de respuesta tardía al abandonar el caso. La suite de colaboración comprueba también la taxonomía proyectada.

La publicación requiere CI del head exacto, backup/restauración en PG17 con todas las migraciones, comprobación de valores anteriores/funciones/RLS y revisión explícita de la ACL append-only. Tras publicar se verifican CI de main, build, revisiones al 100%, Ready, archivos originales, assets exactos y endpoints protegidos. El timeout de CI pasa de 20 a 30 minutos para alojar los nuevos recorridos completos sin recortar cobertura. No se crean cuentas ni fixtures productivos; la prueba manual del usuario sigue prevista al terminar las fases.

Siguiente: Fase 11, onboarding, demo y estados vacíos. No se inicia automáticamente.
