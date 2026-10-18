# Platform MVP v1 — auditoría del design system

Estado: Fase 0, documentación. Base inspeccionada: `22f1187451429c8e98dfcb9874f89b974500cb35`. Fecha de referencia del cliente: 2026-10-17. Este documento no implementa la Fase 1 ni cambia la apariencia productiva.

La auditoría siguiente se conserva como baseline histórico. Implementación posterior de Fase 1: [09-phase1-foundation.md](09-phase1-foundation.md); contrato vigente: [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## Conclusión

La base dark actual es reutilizable: Inter, superficies navy, teal/cyan, violet secundario y estados semánticos ya tienen tokens. Existen primitives opt-in y componentes de workflow compartidos. El riesgo está en la cascada histórica y en la coexistencia de tres contratos de controles (`.button`, botones genéricos bajo `.dispatch` y `.d-button`), no en la ausencia de un sistema visual.

No conviene sustituir las hojas en bloque. La Fase 1 debe añadir contratos opt-in y comprobar los consumidores actuales antes de migrar cada componente. En particular, el hero D1/D2 recién normalizado debe conservar su contrato específico, no adoptar automáticamente los tamaños del page header de plataforma.

## Inventario real y ownership

La carpeta `backend/app/static/css` contiene 21 hojas, 18.085 líneas en esta base. El conteo es una medida de superficie, no evidencia de reglas sin uso. `app.css` tiene 8.324 líneas y `dispatch.css` 4.742; ambas mezclan componentes vigentes, compatibilidad y evoluciones históricas.

| Hoja | Clasificación observada | Owner y decisión para la migración |
| --- | --- | --- |
| `tokens.css` | **Tokens**: paleta base `--d-*`, aliases semánticos `--color-*`, tipografía, espacio, radios, tamaños, sombras y geometría de workflow/hero/shell | Fuente compartida. Mantener aliases usados; añadir roles semánticos gradualmente, con mapa de consumidores. |
| `dation-design-system.css` | **Primitives + components** opt-in: `.d-button`, `.d-page-hero`, `.d-hero-meta`, `.d-execution-review`, `.d-workflow-action-bar`, `.d-data-context`, atención | Capa compartida actual; distinguir base reusable de composición de workflow. Evitar cambiar defaults para rediseñar una única pantalla. |
| `app.css` | **Shell + components + page-specific + legacy + overrides**: reset, títulos/formularios globales, sidebar/topbar, `.view`, `.button`, tablas y renderer histórico; ampliaciones sucesivas y bloque final de marca/nav | Separar por ownership sólo después de mapear consumidores y orden. No borrar por antigüedad. |
| `home-dda.css` | **Page-specific**: Inicio actual, catálogo, filtros, cards, iconos | `home-dda-catalog.mjs` y template. Fuente para futura DDA Library; no equivale a la futura Platform Home. |
| `dda-logistics-landing.css` | **Page-specific**: Logistics overview y disclosures | Template + `dda-logistics-landing.js`. Conservar composición y CTAs hasta la fase de navegación correspondiente. |
| `dispatch.css` | **Components + page-specific + legacy + overrides**: aislamiento del renderer moderno, elementos `.dispatch`, upload, map/config/dashboard y estilos acumulados | Owner DDA compartido, no foundation global de plataforma. Los selectores descendientes amplios requieren atención. |
| `dda-logistics-upload.css` | **Page-specific/components de carga**: hero, archivos, errores, reuso y paneles | `dispatch/upload/*`; preservar validaciones y estado de archivos. |
| `dispatch-lifecycle.css` | **Componente técnico de interacción**: límites de roots, aliases locales, foco visible y reducción de movimiento | Mantener junto al contrato de lifecycle; no es un tema visual global. |
| `decision-map-case-v2.css` | **Components + page-specific**: Decision Case, mapa, cards, estados y configuración compartida | `decision-map.mjs`; también requerido por configuraciones D1/D2. No asumir que sólo afecta al mapa. |
| `decision-trace-v3.css` | **Page-specific**: recuperación/trazabilidad y listado de casos | `traceability-controller.mjs`. Su carga usa un link propio; candidato futuro al helper común. |
| `assignment-config-v2.css` | **Page-specific + shared config**: configuración D1 y estilos consumidos también por D2 | `assignment-config.mjs`, `scheduling-config-v2.mjs`, `decision-config-ui.mjs`. No eliminar antes de separar contratos compartidos. |
| `scheduling-config-v2.css` | **Page-specific**: configuración D2 | `scheduling-config-v2.mjs`. |
| `scheduling-config-shared-phase2.css` | **Components de configuración D2** y adaptación del shared config | `scheduling-config-v2.mjs`/`dda-variable-config.js`; conservar dependencia actual. |
| `scheduling-rule-editor-phase3.css` | **Page-specific/components**: editor de reglas D2 | `scheduling-config-v2.mjs` y módulos de reglas. No es primitive global. |
| `scheduling-execution-phase4.css` | **Page-specific/components de ejecución**: revisión/ejecución D2 | `scheduling-execution-phase4.mjs`, importado por `dda-variable-config.js`; mantener el montaje actual hasta auditar esa extracción. |
| `assignment-dashboard-v2.css` | **Page-specific + capa previa de composición** D1 | `dashboard.mjs`, shell D1. Sigue cargándose; no es automáticamente código muerto. |
| `assignment-dashboard-essential.css` | **Page-specific/components** D1: Essential, divulgación y módulos ejecutivos | `assignment-essential.mjs`, `assignment-summary.mjs`, shell D1. Parte queda sobrescrita por la capa decision. |
| `assignment-dashboard-comparative.css` | **Page-specific** de comparación D1 | `comparative-upgrade.mjs` y módulos relacionados. Fuera de la foundation de plataforma. |
| `assignment-dashboard-decision.css` | **Page-specific + overrides controlados**: layout vigente D1, hero/Contexto/KPI y refinamientos de viewport bajo | `assignment-dashboard-shell.mjs`, `assignment-essential.mjs`. Mantener contrato actual y especificidad mientras se prepara una extracción probada. |
| `scheduling-dashboard-v21.css` | **Page-specific + overrides controlados**: layout D2, hero/Contexto/KPI, timeline, Advanced, chat | `scheduling-dashboard-shell.mjs`, `scheduling-essential.mjs`, módulos D2. |
| `dashboard-toolbar.css` | **Component compartido + composición scoped**: toolbar, menús/drawer, y contrato común de hero D1/D2 | `dashboard-toolbar.mjs` y shells. No promover su geometría específica a todos los page headers. |

Referencias: [tokens](../../backend/app/static/css/tokens.css), [primitives actuales](../../backend/app/static/css/dation-design-system.css), [shell/histórico](../../backend/app/static/css/app.css), [DDA compartido](../../backend/app/static/css/dispatch.css).

## Contratos existentes que deben preservarse

| Contrato | Evidencia | Restricción |
| --- | --- | --- |
| Identidad | `tokens.css:1`: `color-scheme:dark`, Inter, paleta y aliases | Evolucionar semántica sin cambiar toda la paleta ni el contraste por accidente. |
| Espaciado/radios | `tokens.css:104`: escala 4/8/12/16/20/24/32/40/48, control 10, panel 16, hero 24 | Crear nombres funcionales sólo si aportan un rol; evitar una segunda escala paralela. |
| Acciones | `dation-design-system.css:2` y `:28`: `.d-button` y `.d-button--workflow`; controles 36/40/46 px | La acción workflow tiene composición, busy y tamaños propios. No reducir su área táctil para hacerla coincidir con un icon button. |
| Hero previo al dashboard | `dation-design-system.css:111`, `decision-config-ui.mjs:56` | `.d-page-hero--workflow` comparte copy/meta/panel entre carga, mapa y configuración; no convertirlo en hero de marketing. |
| Hero de resultado D1/D2 | `dashboard-toolbar.css:95`, `assignment-dashboard-decision.css`, `scheduling-dashboard-v21.css` | Desktop: min-height 480 px; hasta 1100: 520 px; hasta 760: crecimiento natural. Padding 32/20 px, copy 70/85/100%. Son contratos específicos del resultado. |
| Toolbar de resultado | `dashboard-toolbar.css:106` y `dashboard-toolbar.mjs` | Aprobar a la izquierda; Reconfigurar/Exportar/Más a la derecha; botón principal 46 px, secundarios desktop 44 px, móvil todos 46 px. Selectores semánticos, no posición del hijo. |
| Contexto/KPI D1/D2 | Hojas de ambos dashboards | Cards con base 112/240 px, cuatro columnas, dos hasta 1100 y una hasta 600. Conservar headings visibles y la fuente de datos actual. |
| Imágenes de resultado | `assignment-summary.mjs:15`, `assignment-dashboard-decision.css:9`, `scheduling-dashboard-v21.css:18` | Conservar `assignment-hero-truck.webp` y `scheduling-hero-road.webp`, overlay y crecimiento por contenido. |
| Ejecución | `decision-config-ui.mjs:22`, `dation-design-system.css:62` | Revisión mediante `<dialog>` nativo; contenido/validación/ejecución pertenecen al caller. |

## Cascada, duplicaciones y deuda identificada

1. **Selectores globales activos.** `app.css:1` aplica reset universal; `:23` herencia de fonts de controles; `:46` títulos, `p` y `small`. Una nueva página recibe estilos aunque no use clases de plataforma. Añadir headers/formularios mediante clases opt-in, no modificando `h1`, `button` o `.content` para resolver una pantalla.
2. **Dispatch tiene defaults descendientes.** `dispatch.css:10` a `:32` aplica títulos, párrafos, botones, labels e inputs bajo `.dispatch`, con exclusiones para upload/dialog y `.d-button`. Esas exclusiones demuestran contratos coexistentes; nuevas pantallas globales no deben montar bajo `.dispatch`.
3. **El orden determina el resultado.** `app.html:9` carga tokens, app, home, landing, dispatch, upload, lifecycle y después design system. Las hojas de mapa/config/dashboard se añaden de forma diferida y permanecen en `head`. Un cambio inocuo en un selector compartido puede aparecer sólo después de visitar otra vista. Verificar D1→D2 y D2→D1 además de carga directa.
4. **Superposición real de D1.** `dashboard.mjs:28` carga cuatro hojas de Assignment más toolbar; `assignment-dashboard-decision.css` sobreescribe composición previa, por ejemplo padding/background con `!important` y ajustes posteriores de cards. No eliminar `essential`/`v2` sin evidencia por componente.
5. **La especificidad es parte del contrato actual.** Los selectores scoped con `#dispatch-hero` y `:is()` en `dashboard-toolbar.css:101` ganan a defaults históricos. `assignment-dashboard-decision.css:8` conserva `!important` en padding/background. Promover una regla a un selector corto puede alterar ambos dashboards aun si el valor nuevo parece idéntico.
6. **Hay overrides legítimos de interacción.** `[hidden]{display:none!important}`, menús/drawer del toolbar y posicionamiento del chat necesitan resistir reglas antiguas. No aplicar una prohibición indiscriminada de `!important`; registrar motivo y retirar sólo al eliminar la colisión que lo exige.
7. **Repetición de shell/marca.** `app.css:82` define sidebar y `:7949` vuelve a definir su background en el bloque de marca; `.button--primary` también tiene evolución posterior. Migrar un selector sin sus estados hover/focus/disabled dejaría una mezcla parcial.
8. **Loading de estilos heterogéneo.** `styles.mjs:8` deduplica por pathname, espera load y permite retry. `traceability-controller.mjs:55` construye un link directamente; `scheduling-execution-phase4.mjs:23`, importado por `dda-variable-config.js`, también tiene carga propia. Esta diferencia es deuda técnica para una fase posterior, no motivo para cambiar lifecycle durante Fase 0.

## Responsive y accesibilidad: evidencia y límites

El shell actual usa sidebar 252 px; `app.css:1895` la reduce a 218 hasta 1180 y `:1930` a 72 hasta 860, ocultando labels visuales. La navegación contextual usa scroll horizontal hasta 900 (`app.css:8241`) y ajustes hasta 620. No existe un único breakpoint universal: upload/hero usa 1100/700, toolbar 1100/760/520 y cards D1/D2 1100/600. Conservar los contratos actuales al añadir el shell futuro; no normalizar todos los media queries en esta fase.

Ya existen `:focus-visible`, `prefers-reduced-motion`, estados disabled/busy, `aria-pressed` en filtros y live regions (`home-dda-catalog.mjs:109`, template `:129`), diálogos con trap/retorno de foco (`lifecycle.mjs:18`, `decision-config-ui.mjs:241`) y menú Advanced con `aria-expanded`. El catálogo no vuelve navegables los DDA no disponibles. Estos patrones son reutilizables.

Huecos que requieren implementación/validación futura: no hay un contrato global uniforme de fields/help/error, page header de plataforma, empty state, tabla, sidebar item y dropdown. La existencia de CSS focus no demuestra auditoría WCAG completa. El símbolo de Inicio actual del template es texto Unicode; el shell futuro debe consumir el registry SVG `decision-ui.mjs`, sin nueva dependencia y sin extrapolar placeholders del roadmap a iconos productivos.

## Plan exacto de Fase 1, pendiente de solicitud

| Paso incremental | Archivos/ownership previstos | Criterio de salida |
| --- | --- | --- |
| 1. Fijar baseline visual | Fixtures existentes + pruebas focalizadas de navegación/toolbar/D1-D2; capturas de Inicio, carga, mapa, config y resultado | Capturas antes de editar en 1440, 1280, 1024, 768 y 390; mismo dataset/run para comparación. No ejecutar motores reales para probar CSS. |
| 2. Completar roles semánticos | `tokens.css` | Añadir tipografía, densidad y roles de superficie/control que falten; mantener todos los aliases y valores actuales de workflow/hero hasta verificar consumidores. |
| 3. Consolidar primitives opt-in | `dation-design-system.css` | Definir button roles existentes, field/help/error, badge/status, divider, focus/disabled/busy con estados explícitos. No selectors nuevos globales ni cambio de reglas `.dispatch`. |
| 4. Añadir componentes de plataforma | `platform-components.css` sólo si la separación aporta ownership | Page header con breadcrumb/title/subtitle/actions, cards, empty state, tabla, filter toolbar, dropdown y modal; nombres `d-` documentados. Reusar `iconSvg`, native dialog y scope actual. |
| 5. Preparar estilos de shell | `platform-shell.css` si se necesita | Contrato de sidebar/topbar/nav responsive para el shell futuro, activación opt-in. No crear aún rutas/auth/Decision Center ni una segunda app. |
| 6. QA visual de primitives | Página de desarrollo o fixture, si útil, no nueva pantalla productiva obligatoria | Validar los nueve tipos pedidos: button, form, status, header, table, modal, empty state, sidebar item y dropdown; teclado, focus visible, retorno de foco, texto largo, zoom y estados. |
| 7. Adoptar sólo lo seguro y retirar duplicados probados | Owner exacto de cada consumidor; nunca reemplazo masivo en `app.css`/`dispatch.css` | Cambios de un componente por vez; comparar cascada y rutas directas. Mantener métricas, handlers, imágenes y geometría D1/D2. |

El primer lote puede cerrar la foundation sin migrar pantallas completas. Cambiar navegación global es Fase 3; Platform Home, Data Hub y Decision Center pertenecen a sus fases del roadmap. No usar la Fase 1 como excusa para anticiparlas.

## Validación requerida al implementar Fase 1

- Tests de catálogo, navegación y lifecycle ya existentes: `tests/test_home_dda_catalog.mjs`, `tests/test_navigation.mjs`, `tests/test_lifecycle.mjs`, contrato landing y selectors de D1/D2/upload.
- Browser focalizado: interacción y geometría de toolbar D1/D2, headers visibles, objective largo, aprobación ausente, dropdown fuera/Escape, viewport bajo y navegación entre vistas. `tests/browser/test_navigation.py` contiene esa cobertura reutilizable.
- Medir contrastes de combinaciones reales, labels/errores de formularios, orden Tab, foco de dialogs/menus y overflow. No afirmar accesibilidad completa por pasar pruebas unitarias.
- Mantener el CI normal; ampliar las pruebas sólo al cambiar comportamiento o descubrir una regresión. Esta Fase 0 es inspección estática y no reclama haber ejecutado nueva validación visual ni tests pesados.

La documentación de ownership del shell y la evolución de rutas está en [06-frontend-shell-audit.md](06-frontend-shell-audit.md).
