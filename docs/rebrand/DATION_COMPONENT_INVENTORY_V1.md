# Dation — Component Inventory y Migration Map V1

**Estado final de la saga:** consultar [Design System vigente](DATION_DESIGN_SYSTEM_V1.md) y [limpieza Fase 7](DATION_DARK_PHASE7_IMPLEMENTATION.md). Las tablas siguientes conservan el inventario de Fase 0 como baseline histórico; sus columnas «actual», «objetivo» y «fase» describen aquel momento. El grafo publicado ya no incluye los siete módulos retirados ni el bridge light; Map/Config comparten loader y los filtros tienen propietario CSS. `analysisDepthUi` y los renderers históricos con consumidores permanecen.

**Fase 0, 14 de octubre de 2026.** Auditoría sobre `main` remoto/local `bcda3e55f80ec216711e428c9451ac6ef8d86756`. Sólo documentación; las columnas «objetivo» y «fase» describen trabajo futuro.

Referencias: [wireframes y baseline](DATION_DARK_WIREFRAME_V1.md), [contratos y contraste](DATION_DESIGN_SYSTEM_V1.md).

## Rutas y renderers activos

Todas viven bajo `/app`. `app.html` proporciona shell, paneles, Inicio y Overview; `workspace.mjs` coordina recursos, sesión y ciclo de vida. `navigation.mjs` valida vistas/UUID y serializa los parámetros. El lineage de la corrida prevalece sobre el workspace seleccionado.

| Recurso | Renderer activo | CSS principal | Observación |
|---|---|---|---|
| `view=inicio` | `app.html`, `app.js` para librería/summary | `home-dda.css`, `app.css` | No sustituir por otro Home |
| `view=overview` / `logistics-overview` | `app.html`, `dda-logistics-landing.js` | `dda-logistics-landing.css` | Dual CTA, cases-ready y BFCache |
| `view=logistics-data` | `upload/index.mjs` y submódulos | `dda-logistics-upload.css`, `dispatch.css` | Upload, reuse, preflight y dos footers actuales |
| `view=logistics-map&case_id=…` | `decision-map.mjs`, `traceability-controller.mjs` | `decision-map-case-v2.css`, `decision-trace-v3.css` | Progreso fuera del contexto |
| Config + nodo Assignment | `assignment-config.mjs` | `assignment-config-v2.css` y CSS de caso | Comparte `decision-config-ui.mjs` |
| Config + nodo Scheduling | `scheduling-config-v2.mjs`, módulos de reglas | CSS Scheduling, shared-phase2, rule-editor-phase3 | Assignment aprobada y recursos heredados |
| Dashboard Assignment | `dashboard.mjs` → `assignment-dashboard-shell.mjs` | `assignment-dashboard-v2/essential/comparative.css` | Resumen/evidencia/validación y comparative progresivo |
| Dashboard Scheduling | `dashboard.mjs` → `scheduling-dashboard.mjs` | `dispatch.css`, `dashboard-toolbar.css` | Timeline/SLA y toolbar compartida |
| Error/loading de corrida | `workspace.mjs`, `run-polling.mjs`, `scheduling-execution-phase4.mjs` | `dispatch.css`, `scheduling-execution-phase4.css` | Distinguir terminal de lectura transitoria |
| `traceability` / `library`, `settings` | `app.js`, `ui.js`, `state.js` y paneles HTML | `app.css` | Alcanzables por URL/API de navegación; entran en smoke de shell |

`run_id` sólo permanece en Dashboard; `node_id` en Config/Dashboard. Aliases y URLs frías se conservan. La decisión final figura en `DECISION_META` con `implemented:false`; no se implementa en esta saga.

### Legacy y alcance real

- `dashboard-stage.js` **sí se descarga** desde `app.html`; no equivale al renderer moderno. `recoverRun()` delega schemas Assignment/Scheduling/Dispatch a `DationDispatch`, y `restoreExecution()` evita su restauración cuando existe el workspace moderno o una ruta `view`.
- `decision-stage.js` no se carga desde el template ni desde el bootstrap `app.js` actual. No se debe tematizar como Config publicada ni eliminar sólo por ese dato: revisar el grafo completo y bridges en Fase 7.
- `interpreter-stage.js`, `dashboard-selectors.js`, `dashboard-formatters.js`, `app.js`, `ui.js` y `state.js` siguen cargados o consumidos por librería/bridges. No clasificarlos como muertos por el nombre.
- `dispatch.css` oculta hermanos legacy de los roots modernos mediante `dispatch-enabled`/`dispatch-result`, y oculta launchers de chat anteriores. Mantener estas reglas hasta demostrar que sus consumidores desaparecieron.
- Los módulos `hero.mjs`, `assignment.mjs`, `review.mjs`, etc. siguen participando en fallbacks/otros schemas del dispatcher. La limpieza debe basarse en consumidores y cobertura histórica, no en que no aparezcan en un screenshot.

## Inventario de componentes

Los JS abreviados pertenecen a `backend/app/static/js/dispatch/`, salvo `app.html`, `app.js` y `ui.js`. Los CSS pertenecen a `backend/app/static/css/`. **DS** significa el futuro `dation-design-system.css`; «DS + dueño» mantiene la composición en la hoja actual y mueve sólo primitivas compartidas. Riesgo A = alto, M = medio, B = bajo.

| Componente | Implementación actual / duplicación | Componente objetivo | CSS actual → dueño objetivo | JS / markup owner | Riesgo; fase |
|---|---|---|---|---|---|
| Shell | Light canvas y raíces operativas dinámicas | Shell dark, mismos roots | `app.css`, `tokens.css` → mismos | `app.html`, `workspace.mjs` | A; 1 |
| Sidebar | Navy, labels y rail responsive propios | Misma navegación y roles semánticos | `app.css` → `app.css` | `app.html`, inline nav | M; 1 |
| Topbar | Superficie light sticky | Surface dark translúcida | `app.css` → `app.css` | `app.html` | M; 1 |
| Journey navigation | Generación inline, alias y estado actual | Misma jerarquía con tokens | `app.css` → `app.css` | `dationRenderJourney`, `dda-workflow-config.js` | A; 1 |
| Workspace navigation | Pasos con gates y ocultación en Dashboard | Preservar gates y ocultación | `app.css`, `dispatch.css` → mismos | `app.html`, `workspace.mjs` | A; 1 |
| Page hero | Home/Overview/Upload/Map separados; Config comparte helper | `.d-page-hero`, contenido local | Home/landing/upload/map/config → DS + dueño | `app.html`, `makeHero`, `heroMarkup`, `decisionHero` | M; 1–4 |
| Section header | Markup de páginas y helper Config | Número/eyebrow/H2/ayuda común | `dispatch.css`, config y páginas → DS + dueño | `decisionSectionHeader`, renderers | B; 1–5 |
| Card | DDA, node, resource y depth con estilos distintos | `.d-card` + variantes semánticas | Múltiples hojas → DS + dueño | Home, Map, `decisionChoiceCard` | M; 2–5 |
| Panel | `.dispatch-panel` y paneles específicos | Surface-1 con borde y padding común | `dispatch.css`, dashboard CSS → DS + dueño | `dashboard.mjs`, módulos de evidencia | M; 5 |
| KPI card | Cuatro KPIs ejecutivos, comparación, SLA | Base KPI y semántica de valor | essential/comparative/dispatch → DS + analytics | `assignment-summary`, `assignment-comparison`, Scheduling | A; 5 |
| Primary button | `.button`, CTAs Upload/Config/toolbar distintos | `.d-button--primary`, gradiente AA | app/landing/upload/config/toolbar → DS | Handlers existentes de cada flujo | A; 1–5 |
| Secondary button | Map, botones genéricos y controles locales | `.d-button--secondary` | Múltiples hojas → DS | Landing, toolbar, Config | M; 1–5 |
| Ghost button | Acciones ligeras y controles de panel | `.d-button--ghost` | app/dispatch y páginas → DS | `ui.js`, renderers | B; 1–5 |
| Danger button | Sin variante propia localizada en el flujo principal; hay tonos de error | Variante reservada, sin agregar operaciones destructivas | Tokens/estados actuales → DS | Sin handler nuevo | B; 1 |
| Icon button | Copy ID, close, detalles con tamaños propios | `.d-button--icon`, label accesible | case/config/toolbar/dispatch → DS | Contexto, overlays, `iconSvg` | M; 1–5 |
| Menu item | Botones con símbolo Unicode y descripción | SVG + título + apoyo + foco | `dashboard-toolbar.css` → DS + toolbar | `dashboard-toolbar.mjs` | M; 5 |
| Dropdown | Dos `<details>` independientes | Exclusión mutua, outside, Escape | toolbar/dispatch → DS + dueño | `bindDashboardToolbar`, scope | A; 5 |
| Details/disclosure | FAQ, filtros, comparative, contexto | Summary/chevron/foco consistente | landing/config/map/essential → DS + dueño | Nativo + handlers locales | M; 2–5 |
| Dialog | Review, filtro, cambio de datos, case selector/historial | Superficie overlay y foco común | config/trace/map/dispatch → DS + dueño | Config, `traceability-ui`, `decision-map` | A; 3–6 |
| Drawer | Guía/reuse/detalles con builders distintos | Header/cierre/scroll/foco común | upload/toolbar/dispatch → DS + dueño | `upload/guide-drawer`, `upload/library`, toolbar | A; 3–6 |
| Tooltip | `title`, ayudas, ECharts richText | Ayuda accesible; theme de chart separado | CSS del dueño + opciones de gráfico | Data cards, `shared.chart`, charts | M; 1, 5–6 |
| Status badge | `STATUS_UI`, toolbar y estados de archivo | Icono + label + tono, sin depth | case/trace/toolbar/upload → DS | `decision-ui`, selectors, upload | M; 2–5 |
| Chip | Variables, objetivo, archivo y summary | Escala/radio/selección común | landing/config/essential/upload → DS + dueño | Config, summary, upload | M; 2–5 |
| Progress | Map + ejecución/polling | Estado semántico y aria | case/dispatch/execution → DS + dueño | `decision-map`, `run-polling`, scheduling-execution | A; 2–6 |
| Empty state | `errorBox`, notas y estados específicos | Explicación y siguiente acción válida | dispatch/config/essential → DS + dueño | `decisionEmptyState`, módulos | M; 3–5 |
| Error state | Lectura transitoria, terminal y validación | Recuperación distinta por tipo | dispatch/execution/upload → DS + dueño | `workspace`, `shared.errorBox`, upload | A; 3–6 |
| Upload dropcard | Órdenes/Flota, drag/drop, perfil y estado | Composición existente dark | `dda-logistics-upload.css` → mismo + DS | `upload/dropcard`, `upload/index` | A; 3 |
| Data Pack cards | Map tiene `datasetCard`; Config `decisionDataFileCard`; Upload es editable | Base de archivo compartida, edición separada | case/config/upload → DS + dueño | Map, config-ui, dropcard | A; 3–4 |
| Decision Case disclosure | Config comparte helper; Map usa markup propio | Contrato visual común, acciones propias | case/config/trace → DS + dueño | `decisionCaseCard`, Map `caseCardMarkup` | A; 1, 3–4 |
| Workflow Action Bar | Upload final + sticky; Config comparte summary con cuatro chips | Una barra común, tres summary items en Config | upload/config/shared-phase2 → DS workflow | `makeFinalBar`, `makeSticky`, `configSummaryBar` | A; 3–4 |
| Dashboard Toolbar | Ya compartida, badge depth y menús independientes | Identidad/estado/run, acciones SVG y exclusión | `dashboard-toolbar.css` → mismo + DS | `dashboard-toolbar.mjs`, dashboard-actions | A; 5 |
| Dation IA FAB | Assignment/Scheduling y launchers legacy ocultos | Mismo icono/área/foco/tono | dispatch/dashboard CSS → DS + dueño | Shell Assignment, Scheduling, explanation | M; 5 |
| Chat drawer | Burbujas, historial, retry y procedencia | Surface overlay, input y estados dark | dispatch/app/dashboard CSS → DS + dueño | `explanation.chat`, `lifecycle.mjs` | A; 5–6 |
| Table | Evidencia, guía, library, SLA y comparación | Header dark, separadores y scroll local | app/dispatch/upload/dashboard → DS + dueño | `assignment-evidence`, Scheduling, upload, `ui.js` | A; 3–6 |
| Chart container | ECharts SVG, fallback tabla; tema nulo | Theme por roles + resize/dispose intactos | dispatch/dashboard + opciones JS → analytics | `shared.chart`, `assignment`, `compare`, Scheduling | A; 5 |
| Input text/number/search | Filtros, reglas, custom y chat | `.d-field`, label/error y estados | app/config/upload/dispatch → DS + dueño | Config, rules, chat, library | A; 1, 3–6 |
| Select | Objetivos, anomalías, comparación y filtros | Native dark y foco común | app/config/dashboard → DS + dueño | Config, assignment-comparison | M; 1, 4–6 |
| Date input | Ventana y reglas temporales | Native dark + validación ISO conservada | scheduling CSS → DS + dueño | scheduling-config, scheduling-focus-rules | A; 4, 6 |
| Range slider | Pesos con valor efectivo | Track/thumb/disabled/foco legibles | config/dispatch → DS + dueño | `assignment-config.mjs` | A; 4, 6 |
| Checkbox | Filtros categóricos y opciones temporales | Selected/focus/error reconocibles | config/scheduling → DS + dueño | Assignment, Scheduling y reglas | A; 4, 6 |
| Advanced options | No existe; depth ocupa sección 04 | Sección compartida con placeholders disabled | Config CSS → DS + dueño | Futuro `decisionAdvancedOptionsSection` | M; 4 |
| Loading/skeleton | Pending, polling y análisis local | Animación dark, aria y cancelación | dispatch/execution/dashboard → DS + dueño | polling, comparative-upgrade, workspace | A; 5–6 |

## Carga CSS y duplicaciones comprobadas

El HTML carga tokens → app → home → landing → dispatch → upload → lifecycle. `mountTraceability()` agrega `decision-trace-v3.css` al iniciar. Map, Assignment, Scheduling y toolbar añaden otras hojas por ID. Scheduling añade además `scheduling-rule-editor-phase3.css`; ejecución agrega `scheduling-execution-phase4.css`. Esas hojas también forman parte del rebrand, aunque no figuren en la lista inicial del prompt.

En el probe SPA Scheduling → Assignment, los mismos archivos de caso y Config quedan cargados **dos veces**. Cada owner deduplica su propio ID, no la URL canónica. Cambiar sólo el primer archivo visible puede dejar reglas light activas por la otra carga y por reglas de `decision-trace-v3.css`.

El conteo de estilos señala dónde concentrar la revisión: `dispatch.css` 5044 líneas/204 `!important`; `app.css` 9661/14; Config Assignment 128/135; Upload 2881/34. Las líneas minificadas no equivalen a menor complejidad. No borrar esas reglas mediante búsqueda ciega de `#fff`.

Acción futura: definir propietario único e IDs estables para estilos compartidos al tocar sus loaders; probar rutas frías y ambos órdenes de visita. Cualquier consolidación conserva los reset de grid, estados y selectores de visibilidad del baseline.

## Contrato analysis_depth e históricos

| Consumidor actual | Dependencia real | Migración prevista |
|---|---|---|
| `assignment-config.mjs` | `DEPTHS`, `depthSection`, `data-depth`, review y summary | Fase 4: retirar UX y handlers, añadir sección avanzada inactiva |
| `workspace.mjs` | Default/reset comparative, saved state, `draftFields`, persist, restore y payload | Fase 4: leer drafts viejos sin habilitar opción; no persistirla; nuevas ejecuciones envían `essential` constante |
| `scheduling-config-v2.mjs` | Estado essential, cards disabled, summary y review | Fase 4: retirar concepto; mantener ventana, reglas y upstream |
| `decision-config-ui.mjs` | `decisionDepthCard` usado por ambas Config | Retirar cuando ambos consumidores hayan migrado; revisar tests/imports |
| `dashboard-toolbar.mjs` | Badge y fila Profundidad con `analysisDepthUi` | Fase 4 elimina lenguaje de producto; Fase 5 migra presentación dark y menús |
| `assignment-dashboard-shell.mjs` | `data-analysis-depth` y lectura UI | Fases 4–5: un mismo shell y jerarquía; revisar CSS consumidor antes de borrar atributo |
| `dashboard.mjs` fallback | Detalles de profundidad en resultados Dispatch anteriores | Fase 5: auditar representación histórica; conservar JSON y lectura de schemas anteriores |
| `assignment-dashboard-selectors.mjs` | Prioridad result.analysis → result.configuration → configuration_json | Mantener lectura técnica de essential/comparative/deep hasta no tener consumidores |
| `comparative-upgrade.mjs` | Essential restaura/genera artefacto; otros reutilizan resultado original | Fase 5: normalizar apertura del módulo y conservar ambos caminos sin POST innecesario |
| `AssignmentOptions` / `DispatchOptions` | Enum de tres valores, default comparative, extra forbid | Sin cambios previstos: enviar essential explícito es válido; omitirlo no cambia el default |
| Motor Assignment y comparative service | Candidatos, escenarios/sensibilidad; análisis derivado fuerza comparative | No eliminar campo interno ni cambiar el motor para retirar un selector |

**Riesgo de producto:** la descripción actual de Config dice que la profundidad no cambia la asignación, pero el motor condiciona `candidate_dimensions` según depth y objetivo. Antes de dar por equivalente una nueva corrida essential al default comparative, comparar objetivos simples y balanced/custom con iguales datos/criterios. Registrar cambios de métricas y factibilidad; no rebautizar una diferencia de plan como cambio visual. Ninguna corrida histórica o aprobada se recalcula por abrirla.

## Mapa de migración

| Fase | Cambio autorizado cuando se solicite | Archivos / dueños | Gate y dependencias |
|---|---|---|---|
| **0, actual** | Audit, wireframes, DS e inventario | Sólo los tres `.md` en `docs/rebrand` | Rutas verificadas, baseline y riesgos; detener aquí |
| 1 | Tokens, shell, primitives, heroes base | `tokens.css`, `app.css`, `app.html`, `dispatch.css`; nuevo DS acotado y consumidores compartidos de caso/Map | Dark scheme; AA de estados; bridge explícito para páginas aún light; navegación intacta |
| 2 | Home y Overview | `home-dda.css`, landing HTML/CSS/JS | Heroes compactos, final CTA box retirado, dual CTA intacto |
| 3 | Upload, Data Pack y Action Bar común | `upload/index`, dropcard/guía/library/validación, upload CSS, config-ui y contexto Data Pack de Map | Una barra/CTA, pending/error/ready correctos, reuse/CSV/preflight intactos |
| 4 | Assignment/Scheduling Config y Advanced | Config JS/CSS, config-ui, workspace, reglas y shared-phase2; eliminar badge/fila de depth en toolbar | Sin selector ni estado activo depth; essential explícito sólo en nuevo Assignment; placeholders sin payload; upstream y recuperación correctos |
| 5 | Dashboards, toolbar, comparative, IA y analytics | dashboard/shell/selectors/toolbar/comparative/explanation/shared/chart callers y sus CSS; loading/execution | Un Dashboard por decisión, menús exclusivos/outside/Escape, históricos y artefactos intactos, todos los módulos dark |
| 6 | Responsive, accesibilidad, regresión completa | Tests actuales browser/E2E/unit y owners con defectos demostrados | Cinco anchos, keyboard, contraste compuesto, zoom, autofill/date, cold/warm, E2E real |
| 7 | Cleanup de legacy y actualización del DS | CSS/JS/imports demostrados sin uso, documentación | Retirar bridges, reglas light/depth y loaders redundantes; tests verdes y sin romper otros schemas |

Map no tiene una fase nominada propia en la propuesta: consume la fundación de hero/superficies/estados en Fase 1 y la card de contexto Data Pack en Fase 3; su revisión completa entra en Fase 6. Se conserva su composición y comportamiento, sin crear una fase ni un rediseño paralelo. Las fases no se ejecutan automáticamente.

### Gates de regresión por frontera

| Frontera | Checks que deben conservarse o evolucionar |
|---|---|
| Shell/Overview | Rutas y aliases, back/forward/BFCache, cero/un/varios casos, dos CTAs, contexto y drafts |
| Datos/Action Bar | CSV real, validación, reuse y lineage; un CTA; invalid no continúa; último control visible con footer |
| Config/depth | Payload essential constante de nuevas Assignment; placeholders disabled/no estado/no payload; error terminal conserva criterios y crea otro run ID |
| Dashboard/históricos | essential/comparative/deep abren; cuatro KPIs y cálculos canónicos; artefacto original/derivado sin recalcular; exportaciones y aprobación única |
| Overlays/IA | Menús excluyentes y outside; Escape/restore/trap; historial, retry idempotente, procedencia y cancelación al salir |
| Cleanup | Imports y consumidores buscados en JS/MJS/Python; estilos cargados por rutas frías/cálidas; no romper librería/settings/fallbacks |

## Tests a conservar y actualizar en la fase correspondiente

- `test_assignment_config_redesign.py` y `test_assignment_config_visual_consistency.py`: hoy esperan parte de la UX de profundidad; actualizar sus expectativas sólo con Fase 4.
- `test_assignment_dashboard_phase0_contract.py` y fases 1/2/3: protegen contrato histórico, selectors y composición. No eliminar soporte de JSON porque desaparezca una etiqueta visible.
- `test_assignment_executive_kpis.mjs` y `test_dashboard_selectors.js`: conservar cálculos, unidades y escenarios.
- `test_frontend_contract.py`, `test_landing_navigation_contract.py`, `test_traceability_phase3.py`: evolucionar contratos de tema/layout preservando navegación y trazabilidad.
- `tests/browser/test_navigation.py`: baseline de 66 casos; la recuperación de Assignment actualmente comprueba `state.analysisDepth`, por lo que Fase 4 debe sustituir esa expectativa por la nueva constante de payload sin perder las de objetivo/recursos/historial.
- `tests/e2e/browser_journey.py` selecciona `data-depth=essential`; cambiar ese paso en Fase 4 y comprobar que la ejecución sigue enviando essential sin elección del usuario. Mantener recuperación real de Scheduling y contexto nuevo desde Overview.
- CI exige suites Python/Node/Chromium, 46 SQL, siete E2E reales y auditorías de locks. No desactivar tests para retirar una opción.

En Fase 0 pasan los **349 Python y 37 Node** existentes y se capturan 70 estados Chromium sin errores JS/overflow de documento. Los defectos de menú se registran de forma explícita. No se agregan tests que reflejen sólo texto de estos documentos.

## Deuda concreta y salida

La migración depende de resolver propiedad/cascade, evitar texto claro en superficies todavía blancas, medir el cambio de default técnico essential y comprobar popovers/footer sobre pantallas pequeñas. No requiere Supabase, DDL, endpoints nuevos ni cambios de engine en Fase 0. Si Fase 4 revela un contrato que lo impida, deberá documentarse el bloqueo antes de ampliar el cambio.

**FASE 0 COMPLETA — LISTA PARA FASE 1.** Inventario cubierto, migración asignada y contratos críticos identificados. No se ha implementado ninguna fase posterior.
