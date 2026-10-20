# V2 · Fase 2 · Decision Center

Base técnica: main `ed7888c`, Fase1 publicada en PR86. Alcance: Decision Center V2 completo del master plan, incluidas sus subfases visuales internas. Se mantienen Home/Data Hub/Team/Settings/Auth/Map/dashboards y los motores. No se inicia Fase3 automáticamente.

## Contrato incremental

- `GET /api/platform/decisions` conserva items/total/limit/offset y añade `summary`, `dda_options`, `owner_options`. SQL calcula KPIs sobre todo el workspace, independientes de búsqueda/filtros/página. Excluye archivados. Cases activos incluye casos en revisión; review cuenta candidatas completadas con linaje vigente. Approved cuenta aprobaciones canónicas, incluidas las que siguen vigentes durante una sustitución pendiente. Pending sólo cuenta review aprobable por el usuario actual según Access Role, aprobador asignado y DDA habilitado. Viewer tiene cero pendientes.
- Filtros nuevos: `pending_approval`, `approved`; `in_progress` incluye todos los activos según la especificación V2. Owner acepta all/me/unassigned/UUID y consulta asignaciones Data/D1/D2 del mismo workspace. Las opciones se limitan a 100 personas asignadas y conservan la selección explícita. No se usa uploader como responsable ni se confunden Case completado y nodo aprobado.
- Nuevo RPC de servicio `platform_decision_portfolio` y helper privado `center_portfolio_facts`: latest/approved de metadatos livianos en consultas por conjunto, sin cargar resultados/configuraciones de todos los runs. Se enriquecen únicamente los 25 Cases paginados con helpers existentes. No se cambia el RPC legacy ni se persiste otro estado. El agregado se contrasta con el historial canónico, incluido reemplazo y stale.
- Detail/history delegan en el RPC existente; detail añade el snapshot de responsabilidades Fase1 dentro de la misma llamada SQL. Actividad e historial se cargan sólo al seleccionar/expandir. Lecturas sin escrituras ni reparaciones del estado persistido.
- Objetivos normalizados con el registro Fase1: aprobación vigente → último run → Por definir. No existe configuración pendiente persistida en Case; los borradores de un navegador no se presentan como verdad compartida. Se informa el run/source del objetivo y el objetivo distinto de la candidata. Navegación oficial conserva prioridad de aprobación; la acción explícita Revisar abre la candidata exacta y su dashboard aprobado sigue disponible en disclosure. Aprobador asignado y actor real se muestran separados.

## UI y navegación

Hero local SVG abstracto, cuatro KPIs enlazados a filtros, atención sólo si hay pendientes accionables, búsqueda/filtros compactos y tabla Case-first. Registry DDA en presentación/validación; sólo aparecen DDAs con Cases reales. No hay segundo motor/DDA ni datos ficticios productivos. Nuevos DDAs requerirán su adaptador de dominio; no se enrutan Cases desconocidos hacia Logística.

Case seleccionado permanece en `center_case_id`, con filtros/owner/offset y `center_node`/`center_runs_offset`. Escritorio ≥1100 usa aside no modal; tablet/móvil usan dialog nativo y gestión compartida de foco/Escape/backdrop. Cerrar conserva filtros; Back/Forward/reload conserva selección. Portfolio y detalle tienen estados de carga/error independientes y cancelan respuestas tardías. Seleccionar o paginar historial no vuelve a descargar el portfolio.

Drawer: contexto, objetivo, responsables Data y decisión, CTAs exactos, archivos y descarga protegida existente (`session.js` incorpora Bearer), cadena, aprobación/actor, historial apilado con paginación y actividad reciente (5, ampliable con el componente existente). Mantenimiento pasa a menú accesible; los diálogos CAS existentes se conservan. Las asignaciones usan candidatos/API Fase1 por responsabilidad; Admin mantiene autoridad. D3 conserva visibilidad de históricos sin ofrecer ejecución/asignación de un motor futuro. Gates obligatorios continúan desactivados hasta Fase5.

## Seguridad, migración y rollback

Migración aditiva `20261020020000_platform_decision_portfolio.sql`: dos funciones de lectura, sin tablas, backfills ni alteración de evidencia, permisos existentes o RPC legacy. Helper privado sin grants directos; RPC sólo service_role revalida actor/workspace. No se aceptan claims de autoridad desde payload. Descargas/edición/archivo/asignación conservan controles backend. Free universal intacto. Una imagen tenant-aware anterior funciona con el DDL aditivo conservado; no borrar datos para revertir.

## Evidencia de cierre

Las pruebas verifican semántica global con más de una página, permisos, aislamiento, linaje, objetivos, lectura pura y 5.000 Cases sintéticos únicamente en stack descartable. Chromium/E2E verifica drawer, URLs, descargas, mantenimiento, teclado, responsive y regresión D1/D2. Capturas y evidencia exacta de CI/despliegue se guardan en `/workspace/dation-audit/platform-v2-phase2/ENTREGA.md` al cerrar; esta documentación no certifica publicación por sí sola.
