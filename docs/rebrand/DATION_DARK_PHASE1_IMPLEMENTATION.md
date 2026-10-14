# Dation — Fase 1: Dark Foundation

14 de octubre de 2026. Baseline funcional: `bcda3e55f80ec216711e428c9451ac6ef8d86756`. La especificación de Fase 0 se integró mediante PR #48, base de esta implementación: `7a209866b4720527b4bdddc1a496b2684235918a`.

## A. Diagnóstico

Los tokens y el chrome eran claros; cada hero definía su fondo, espaciado, radio y título. Las hojas cargadas al navegar entre decisiones podían restaurar valores antiguos. Cambiar sólo los tokens dejaba texto claro sobre cards y controles blancos.

El gradiente decorativo de marca sólo alcanza 2.610:1 con el foreground del CTA. Necesita un rol de acción independiente. El foco anterior utilizaba un teal con alpha bajo.

## B. Intención

Crear una base dark nativa, con roles públicos, botones reutilizables y un único contrato de hero. Conservar información, rutas, drafts, validaciones y ejecución. La migración detallada de cada página mantiene la secuencia de Fase 0.

## C. Implementación

- `tokens.css`: palette navy/graphite, superficies, texto, bordes, focus, estados, gradientes de acción AA, sombras dark, espacios, tamaños de control, radios y motion. Los aliases anteriores permanecen.
- Shell: body/main/content sobre canvas oscuro; sidebar con texto de apoyo legible; topbar y workspace nav con superficie dark translúcida; journey, selección actual, pasos completos e inactivos adaptados. El offset de navegación utiliza la altura común del topbar. Se reserva espacio para que el foco del breadcrumb no se recorte.
- `dation-design-system.css`: `.d-button`, primary, secondary por defecto, ghost, danger, icon y menu; tamaños 36/40/46; hover, foco, disabled nativo/aria y reduced motion. Overview consume las variantes compartidas. Los botones existentes conservan sus hooks y los aliases de acción.
- `.d-page-hero`: mínimo 220 px, padding 26/20, gap 24/20, radio 24, título `clamp(28px,3vw,40px)`, lead 14 y fondo dark. Los dueños conservan la composición y transfieren sus propiedades comunes al contrato. Se aplica a Home, Overview, Upload, Map y ambas Config. No hay altura fija ni recorte de texto. Se compactan los paneles de apoyo y se retira el adorno de Home que podía desbordar al eliminar el clipping.
- `dation-legacy-surfaces.css`: boundary explícito `data-dation-surface="legacy-light"` para páginas aún pendientes y overlays conocidos. Preserva los pares claros de texto/fondo, controles nativos y sombras. Los heroes reestablecen sus roles dark. Este bridge no alcanza al shell; se retira por página en fases 2–5.
- Caché: URLs de estilos versionadas; el servidor conserva su contrato no-cache/ETag.

La Fase 1 no equivale a una aplicación completamente oscura: las superficies claras de contenido son una transición explícita. Los heroes pueden crecer con su contenido; la densidad y composición detallada de Home/Overview, Upload, Config y Dashboard se terminan en sus fases.

## D. Archivos exactos

| Área | Archivos bajo `backend/` |
|---|---|
| Roles y primitivas | `app/static/css/tokens.css`, `dation-design-system.css`, `dation-legacy-surfaces.css` |
| Shell y heroes | `app/static/css/app.css`, `home-dda.css`, `dda-logistics-landing.css`, `dda-logistics-upload.css`, `dispatch.css` |
| Heroes dinámicos y foco | `app/static/css/assignment-config-v2.css`, `decision-trace-v3.css`, `dispatch-lifecycle.css` |
| Contrato DOM | `app/templates/app.html`, `app/static/js/dispatch/decision-config-ui.mjs`, `decision-map.mjs`, `upload/index.mjs` |
| Regresiones | `tests/browser/test_navigation.py`, `tests/test_frontend_contract.py`, `tests/test_assignment_config_visual_consistency.py` |

Documentación: este informe y la nota de estado en `DATION_DESIGN_SYSTEM_V1.md`. No se modifican dependencias, lógica de backend, esquema, permisos, autenticación ni datos de negocio.

## E. Pruebas y aceptación

Validación local:

| Suite | Casos |
|---|---:|
| Python | 349 |
| Node | 37 |
| Chromium con API sintética | 69 |
| End-to-end con PostgreSQL/PostgREST, storage y worker desechables | 7 |

Los tres nuevos casos de Chromium comprueban el tema bajo preferencia de sistema clara, shell y seis heroes a cinco anchos, transición SPA Scheduling→Assignment, foco con teclado, gradientes calculados del CTA, disabled estable, reduced motion y el límite claro de controles/dialog. Se amplía la regresión del botón Overview deshabilitado. Los contratos de assets y el tamaño del icono compacto se actualizan con el cambio.

El E2E recorre creación, ejecución, aprobación, navegación móvil, historial, reemplazo, comparativa y recuperación de jobs. La infraestructura es desechable y no utiliza Supabase productivo. También se verifican sintaxis de todos los JS, compileall, pip check y `git diff --check`.

La CI requerida añade 46 pruebas SQL: total esperado **508**. La publicación exige CI del head exacto, merge verificado y Cloud Build correcto; el comprobante final de ejecución, revisión y tráfico se registra en el PR y en `/workspace/dation-audit/rebrand-phase1-release.json`.

## F. QA visual y contraste

Se revisan 14 estados a 1440, 1280, 1024, 768 y 390 px, incluidos contexto abierto/cerrado, review, error, drawer, chat y ambos dashboards. Las capturas y geometría se guardan en `/workspace/dation-audit/rebrand-phase1-visual/`. La pasada final no presenta desbordamiento horizontal del documento ni errores JavaScript.

| Hero, escritorio 1440 px | Antes | Fase 1 |
|---|---:|---:|
| Home | 425 | 357 |
| Overview | 470 | 285 |
| Upload | 481 | 325 |
| Map | 426 | 375 |
| Config Assignment | 403 | 297 |
| Config Scheduling | 403 | 310 |

Son alturas observadas con el contenido actual, no límites fijos. En móvil se preservan explicación y acciones; el scroll necesario no se resuelve ocultando contenido operativo.

Contraste de los roles nuevos: texto principal ≥12.801:1, secundario ≥7.961, muted ≥5.354, foco ≥5.956 y borde de control ≥3.406 sobre las superficies evaluadas. Gradientes de acción: ≥6.136 normal y ≥4.913 hover, muestreados en 257 posiciones por segmento. Chromium verifica también los gradientes obtenidos de los estilos computados. Disabled no se usa como texto informativo. Estas mediciones no certifican los componentes legacy ni los gráficos pendientes.

La verificación posterior al despliegue debe comprobar markup y 14 assets por hash, privacidad, readiness, dependencias y heartbeat del worker. La QA de navegador productiva usa casos existentes y bloquea escrituras persistentes; compara hashes de casos, runs y comparativas antes/después. Se mantienen los dos CTA, selección de caso, drafts, Back y copia del ID.

## G. Riesgos y continuidad

El bridge es temporal: retirar el atributo de una página sólo después de migrar todos sus descendientes y overlays. Las hojas dinámicas siguen duplicándose en algunas rutas; los estilos comunes ya no dependen de esas copias, y su consolidación pertenece al cleanup posterior.

Permanecen la caja final de Overview para Fase 2, los Action Bars para Fase 3, profundidad/opciones avanzadas para Fase 4 y menús/gráficos del Dashboard para Fase 5. No se cambia la semántica de `analysis_depth`. Los dos menús de toolbar todavía pueden abrirse juntos; su comportamiento no forma parte de esta fase.

Rollback: revertir el merge de esta implementación y dejar que Cloud Build publique el commit revertido. No hay migraciones ni rollback de datos.

## H. Gate

**FASE 1 COMPLETA — LISTA PARA FASE 2**, sujeto a las comprobaciones de CI y publicación registradas en el PR. La siguiente fase debe migrar Home/Overview, compactar su composición final y retirar la caja CTA final de Overview. No iniciar Fase 2 automáticamente.
