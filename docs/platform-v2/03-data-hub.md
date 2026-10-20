# Fase 3 · Data Hub V2

## Fase completada

Biblioteca transversal de datasets con resumen global, filtros independientes y detalle contextual. Publicación y resultados finales: PR `phase-3-data-hub-v2` y evidencia de entrega del entorno; las fases 4–7 siguen pendientes.

## Decisiones de arquitectura

Los DDAs incorporan datos; Data Hub conserva validación, uso y ciclo de vida. Se retiran únicamente las entradas globales a Data Packs, carga, reutilización y demo. Los endpoints y helpers existentes se mantienen para consumidores y enlaces externos autorizados. No cambian motores, dashboards, Home ni permisos técnicos.

El resumen cuenta todos los datasets persistidos del workspace, incluidos archivados y eliminaciones pendientes hasta que finalizan. `validated` significa `profile_json.valid=true`; `issues` significa `false`; avisos en un CSV válido no lo convierten en inválido. El resumen no depende de búsqueda, filtros ni paginación. La lista abre en activos; Total limpia filtros y muestra todos los estados.

## Archivos afectados

`data-hub.mjs` conserva el lifecycle y reutiliza `mountDialog`, `mountDropdown`, `createScope`, navegación, descarga autenticada y formato del workspace. `data-presentation.mjs` concentra nombre/tipo/calidad/estado/uso y usa el registry compartido. `data-resource.mjs` conserva filtros y selección en URL. CSS y SVG locales tienen ownership exclusivo del Data Hub.

## API y SQL

`GET /api/platform/data/datasets` conserva `items/total/limit/offset/incomplete_uploads`, añade `summary` y admite `type`, `validation`, `state`, `q`, `limit`, `offset`. El antiguo `filter` sigue compatible. No se crean endpoints de escritura.

Migración aditiva `20261020030000_platform_dataset_library.sql`: dos helpers privados y RPC de lectura `platform_dataset_library`. El RPC anterior `platform_data_hub`, sus packs y todos los RPC de upload/delete permanecen intactos. Sin backfills, tablas, índices, movimientos de objetos ni cambios de ACL existentes. Sólo service_role puede ejecutar el RPC público; helpers sin acceso directo de los roles API.

El detalle reutiliza los permisos conservadores del RPC anterior, añade `case_total` y relaciones de uso paginadas con etiqueta, ID amigable y DDA real. Incluye referencias actuales de Cases y referencias mediante runs históricos. No infiere relaciones ni metadatos a partir de nombres de archivos. Se omite atribución desconocida y no se inventa uso por nodo.

## UX/UI

Hero de gobernanza; cuatro KPIs; búsqueda literal y filtros compuestos; tabla semántica de nueve columnas y tarjetas móviles. Selección conserva portfolio, búsqueda y página. Drawer no modal desde 1100px, overlay en tablet y pantalla completa móvil. Preview lazy de cinco filas, paginada y con truncado existente. Calidad con avisos desplegables y detalles técnicos cerrados inicialmente.

`dataset_id`, `data_q/type/validation/state/offset` y `data_cases_offset` soportan reload y Back/Forward. Selección e historial de uso no recargan el portfolio. Cambios de filtros/página cierran selección. Bookmarks de packs vuelven a la biblioteca mediante replace; filtros antiguos se canonicalizan. `Utilizado en` abre Decision Center con `center_case_id`, también si el DDA está deshabilitado, y Back recupera el dataset.

Archivado/restauración y eliminación requieren confirmación. El delete sólo se ofrece con permiso real del detalle: archivado, sin referencias/evidencia y sin ser flota vigente. Fallos conservan intent y permiten completar eliminación. Las cargas interrumpidas se revisan/descartan desde un banner discreto; aquí no se inicia ninguna carga.

## Seguridad

TenantClient ya filtra cada operación REST y valida ownership antes de leer Storage. Se conserva y añade comprobación explícita `ctx.workspace_id` en lookup previo a preview, download, reuse y archivado/restauración. El RPC comprueba membresía activa y workspace. Viewer conserva lectura/preview/download según política actual y no obtiene mutaciones. Se mantienen locks, journals y guards de evidencia.

Los enlaces de descarga conservan el interceptor Bearer de `session.js`; no generan URLs públicas ni tokens en UI. Nombres, CSV, avisos y etiquetas se insertan con textContent. Sólo SVG del registry local usa HTML confiable.

## Pruebas

Cobertura real de dos workspaces contra detalle/preview/download/archive/unarchive/delete; resumen independiente y filtros compuestos; historial por runs; ACL anon/authenticated/service; Viewer; guards de flota/evidencia; fallos de Storage; cleanup explícito y respuesta perdida tras commit. Journey real: carga desde Logística → Hub → preview/bytes → archive/restore/delete y dataset → Decision Center → Back.

Chromium sintético verifica filtros/KPIs, canonicalización legacy, selección conservada sin refetch, preview lazy, XSS, descarte, delete recuperable, respuesta tardía, Viewer y foco/trap/Escape/Back/Forward. Se ejecutan además las suites generales Python/Node/Chromium/PostgreSQL y E2E reales antes del merge.

## Regresión

Se preservan Data Packs/reuse en backend, biblioteca previa dentro de Logística, aprobación vigente, ejecución D1/D2, responsabilidades, Free universal y todos los datos del workspace. No se habilitan gates de Fase 5.

## QA visual

Viewports 1440, 1280, 1024, 768 y 390px; sin overflow de página, preview con scroll propio, contraste del tema y comportamiento aside/dialog. Artefactos sintéticos se guardan fuera de Git.

## Limitaciones conocidas

No se ejecutan journeys con una cuenta personal de producción ni se crean fixtures o usuarios allí. La evidencia funcional se obtiene en stack aislado con Auth/REST/PostgreSQL/Storage/API/worker reales. El respaldo de aplicación no restaura contraseñas ni cuentas Auth.

## Siguiente fase

Fase 4: Home V2. No se inicia automáticamente.
