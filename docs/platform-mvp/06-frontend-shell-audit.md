# Platform MVP v1 — frontend y plan de shell

Estado: Fase 0, inspección estática. Base: `22f1187451429c8e98dfcb9874f89b974500cb35`. Fecha de referencia del cliente: 2026-10-17. No se añadieron rutas, views, auth, CSS ni componentes en esta entrega.

## Decisión de arquitectura

Conservar FastAPI + template + módulos ES y evolucionar la app única. El shell ya separa panels de contenido y roots de Dispatch; tiene History API, restauración por URL, cancelación, scopes y protección frente a respuestas tardías. Crear una segunda aplicación o migrar de framework no resuelve el riesgo principal: aclarar ownership de navegación, estado y estilos sin alterar el workflow D1/D2.

## Mapa de superficies y owners

Rutas de archivos relativas a `backend/app/`.

| Superficie actual | Owner HTML/JS real | Owner CSS principal | Observación de migración |
| --- | --- | --- | --- |
| Shell, sidebar y topbar | `templates/app.html:18`, script inline `:1071` | `app.css`, `tokens.css` | Sidebar global, journey nav y workspace nav contextual. No existen aún páginas SaaS separadas de login/equipo/perfil. |
| Inicio | `app.html:96`, `static/js/home-dda-catalog.mjs`, montaje en `app.js:639` | `home-dda.css`, `.d-page-hero` | Es introducción + catálogo de DDA; no es la Platform Home operativa descrita por el roadmap. |
| Catálogo de DDA | `home-dda-catalog.mjs:3`/`:12` | `home-dda.css` | 7 entradas: sólo Logística disponible; 6 próximas. Categorías, estado, capabilities y target son datos, no autorización ni entitlement de workspace. |
| Logistics overview | `app.html:156`, `static/js/dda-logistics-landing.js` | `dda-logistics-landing.css` + legado `app.css` | Hero con iniciar nueva decisión/ir al mapa y disclosures. Mantener la diferenciación de los dos CTAs. |
| Flujo contextual DDA | `dda-workflow-config.js:2`, renderer inline en `app.html:1237`/`:1289` | Final de `app.css:8097` | Cuatro pasos: datos, mapa, configurar, dashboard; separado de las tres decisiones del caso. |
| Upload / Data Pack | Panel `app.html:473`; `dispatch/workspace.mjs:3` y `dispatch/upload/index.mjs:235` con submódulos dropcard/library/guide/validation | `dispatch.css`, `dda-logistics-upload.css`, design system | Validación local, preflight y selección/reuso de órdenes/flota. Mantener como entrada de DDA hasta diseñar Data Hub; no reemplazar por un uploader global desconectado. |
| Decision Map | Panel `app.html:480`; `dispatch/decision-map.mjs`, `decision-case.mjs`, `decision-ui.mjs` | `decision-map-case-v2.css`, `dispatch.css` | Es workflow de un caso DDA; no equivale al Decision Center global de muchos casos. |
| Config D1 | Panel `app.html:487`; `assignment-config.mjs:454`, `decision-config-ui.mjs`, `workspace.mjs` | `assignment-config-v2.css`, mapa compartido, design system | Scopes, filtros, objetivo y action bar. Preservar serialización y borradores. |
| Dashboard D1 | Panel `app.html:492`; `dashboard.mjs`, `assignment-dashboard-shell.mjs`, `assignment-essential.mjs`, summary/advanced/evidence/selectors | Toolbar + 4 hojas Assignment | Renderer nuevo bajo `#dispatch-dashboard-root`; original histórico sigue en template y se oculta mediante body classes. |
| Config D2 | `scheduling-config-v2.mjs:601`, módulos rules, `dda-variable-config.js` | Assignment compartido + 4 hojas Scheduling/config | Consume Assignment bloqueada; no es una configuración independiente sin source run. |
| Dashboard D2 | `dashboard.mjs`, `scheduling-dashboard.mjs:12`, shell/essential/selectors/timeline/advanced | `scheduling-dashboard-v21.css`, toolbar, dispatch | Conserva calendar/timeline, Advanced y chat; no hay cambio de estos módulos en la foundation de plataforma. |
| Trazabilidad/recuperación | `app.html:912`, `app.js:264`, `dispatch/traceability-controller.mjs` | `app.css`, `decision-trace-v3.css` | Coexisten librería histórica de datasets/runs y recuperación de casos DDA. Reusar adaptación a Decision Center, no duplicar listas sin contrato de datos. |
| Configuración actual | `app.html:1026`, `app.js:649`, `ui.js` | `app.css` | Muestra estado técnico del workspace privado. No es todavía settings multiusuario. |

Evidencia central: [template](../../backend/app/templates/app.html), [workspace](../../backend/app/static/js/dispatch/workspace.mjs), [navigation](../../backend/app/static/js/dispatch/navigation.mjs), [catálogo](../../backend/app/static/js/home-dda-catalog.mjs). El detalle CSS completo está en [04-design-system.md](04-design-system.md).

## Navegación: quién decide y quién dibuja

La implementación vigente tiene tres capas compatibles, pero fáciles de confundir:

1. El script inline de `app.html:1071` mantiene `currentView`, readiness y contexto de decisión. Instala `window.dationNavigate` (`:1470`), alterna `.is-active` en panels, actualiza sidebar/journey/workspace nav, emite `dation:view` y mueve scroll. Es el renderer visual de shell.
2. `dispatch/workspace.mjs:118` captura esa función en `renderView`. Al final (`:737`) sustituye el global por el router de recursos `navigateResource`. El router decide contexto, URL, hidratación, montaje y cancelación; invoca al renderer capturado. El orden de carga del template (`workspace.mjs` antes de `app.js`) y la función bootstrap anterior forman parte de ese contrato.
3. `app.js:64` tiene un wrapper que actualiza `state.js.activeView` y delega al global; `ui.js:277` ofrece un fallback visual parcial. El fallback no reproduce todas las responsabilidades del router. No eliminarlo ni convertirlo en fuente canónica sin revisar los consumidores históricos.

Hay `onclick` de fallback en el template y click delegation en `app.js:409`. El botón del catálogo también tiene handler propio con `stopPropagation` (`app.js:447`). Esto no prueba una regresión, pero exige inventariar los caminos antes de mover listeners al shell futuro. Evitar instalar otro router/delegation sobre los existentes.

### Semántica actual de URLs

`dispatch/navigation.mjs:1` define views y nodos permitidos. `readResource` acepta `view`, `case_id`, `node_id`, `run_id`; valida UUIDs y nodos, y soporta el alias legado `dda=scheduling_v1`. Con `run_id` sin view el destino es dashboard; sin ambos el recurso por defecto es `overview`, que el router traduce a Logistics overview. El template pinta Inicio antes de la restauración: el panel inicial del HTML no debe confundirse con el destino estable de una carga limpia de `/app`.

`resourceUrl` borra sólo los cinco parámetros de recurso conocidos, preserva otros parámetros, siempre escribe view y limita node a config/dashboard y run a dashboard. `workspace.mjs:699` conserva aliases `overview → logistics-overview` y `library → traceability`; por ello el nombre visible y el query param pueden diferir. Los links existentes no deben romperse al introducir rutas de plataforma.

Ejemplos del contrato actual, con IDs de formato ilustrativo:

```text
/app?view=overview
/app?view=logistics-data&case_id=<uuid>
/app?view=logistics-map&case_id=<uuid>
/app?view=logistics-config&case_id=<uuid>&node_id=logistics_scheduling
/app?view=decision-dashboard&case_id=<uuid>&node_id=logistics_scheduling&run_id=<uuid>
/app?view=library
```

`navigateResource` usa `pushState` normalmente y `replaceState` cuando se solicita; `restoreResource` en `workspace.mjs:740` usa `history:false`. `popstate` y `pageshow.persisted` restauran recursos. Los errores de URL o recuperación dibujan una recuperación explícita, no una corrida ficticia. `navigation.mjs:34` prioriza lineage persistido de la corrida sobre el workspace actualmente seleccionado; mantener esa precedencia.

### Contrato que debe tener la evolución de rutas

- Mantener lectura de deep links actuales y alias durante transición. Una URL legacy debe resolver el mismo caso/nodo/corrida.
- Una sola tabla de definiciones resolverá tipo de página, view/handler y contexto; una sola autoridad actualizará History. No añadir parsing competidor en cada componente.
- Separar route state de presentation state y drafts. URL conserva el recurso; apertura de un disclosure/tab puramente visual no necesita reemplazar el recurso.
- Cambiar a `/app/decisions/:id` o `/app/ddas/logistics/...` requiere verificar fallback del servidor y refresh, además del router cliente. La Fase 0 no cambia rutas FastAPI ni promete esos paths como disponibles.
- Back/forward, reload y bfcache deben mantener identidad de caso, source run, selección y cancelación. No usar el último `sessionStorage` como autorización o como reemplazo de la URL.

## Estado y recuperación

| Capa | Estado observado | Límite/acción futura |
| --- | --- | --- |
| `state.js:1` | View, DDA, datasets/runs, selección histórica, objetivo/pesos, intérprete/chat, servicios y tab de trazabilidad | Es store mutable histórico. No es contexto de usuario/workspace multiusuario ni la única fuente del DDA. |
| Inline template | View visual, readiness de datos/dashboard, contexto resumido de decisión | Debe convertirse en controller de shell con API explícita en una fase posterior; no copiarlo a otro bootstrap. |
| `workspace.mjs:81` | Estado DDA restaurado de `dation.dispatch.workspace.v5` en sessionStorage: órdenes/flota, criterios, caso, nodo y flags | Es caché de sesión; datos canónicos se hidratan del backend. En tenancy futura necesitará aislamiento por identidad/workspace y limpieza al cambiar sesión. |
| `workspace.mjs:119` | Drafts por caso en `dation.dispatch.drafts.v1`; allowlist `draftFields`/`cleanDraft` | Preservar borradores al navegar y no mezclarlos entre casos. Evitar almacenar JWT/secretos en esta capa. |
| `hydrateCase`, `show`, `runContext` | Caso/datasets y lineage persistido de corrida | Ya verifica coherencia del Data Pack antes de montar; no seleccionar un caso porque coincide el último tab abierto. |

No se propone un store global nuevo en Fase 0. La separación futura mínima es `SessionContext` (identidad/workspace validado), `RouteContext` (recurso actual) y estado del DDA ya existente. La implementación y seguridad de SessionContext pertenecen a Fase 2; no se simulan con `activeDda` o con el catálogo estático.

## Lifecycle y ownership de eventos

`dispatch/lifecycle.mjs:1` usa WeakMap por root. `createScope` dispone el scope anterior, tiene AbortController, cleanups idempotentes, `listen`, `timeout`, `observe` y scopes hijos. `trapFocus` existe como helper separado.

- `navigateResource` aborta la petición de ruta anterior, incrementa `routeGeneration`, detiene polling e incrementa `pollGeneration`; dispone scopes y vacía roots antes de volver a montar (`workspace.mjs:704`). Las respuestas se contrastan con generation antes de mutar UI.
- `pagehide` aborta/cierra recursos; `pageshow.persisted` restaura; `popstate` rehidrata. El shell futuro debe conservar estos caminos, no limitarse a limpiar en click.
- `app.js:649` dispone/remonta `libraryScope` para Inicio, trazabilidad y settings; fetches usan signal y verifican `scope.active`.
- Dashboard y shells registran interacciones mediante `scope.listen` y limpian chat/gráficos/submódulos por scope. Upload y config crean su scope por root y lo usan para IO/cleanups.
- Persisten listeners directos en nodos reemplazables (`assignment-config.mjs:628`, `scheduling-config-v2.mjs:534`, `upload/index.mjs:288`) y listeners globales de duración de app (`app.js:409`, `workspace.mjs:741`). Un listener directo de un nodo eliminado no es, por sí solo, prueba de fuga. Sí debe registrarse con scope cualquier listener global/observer/timer nuevo creado durante un mount.
- `mountHomeCatalog` usa WeakSet para montaje único y conserva cards al filtrar; hoy vive durante toda la app. Si se convierte en panel recreado o cargado por workspace necesitará mount/dispose explícito, no confiar sólo en WeakSet.

## Shell objetivo, sólo propuesta

```text
App bootstrap único
├── SessionContext validado (Fase 2)
├── Route controller + compatibilidad de URLs (Fase 3)
└── PlatformShell
    ├── GlobalSidebar + UserWorkspaceMenu
    ├── PageHeader / breadcrumb
    └── Page outlet
        ├── PlatformHome: resumen y acceso a trabajo reciente
        ├── DdaLibrary: catálogo + disponibilidad real del workspace
        ├── DecisionCenter: listado/recuperación transversal de casos
        ├── DataHub / Team / Settings / Profile
        └── LogisticsHome / DdaContext
            ├── Overview
            ├── Data Pack
            ├── Decision Map del caso
            ├── Config D1 / Config D2
            └── Dashboard D1 / Dashboard D2
```

PlatformHome, LogisticsHome y DecisionCenter tienen responsabilidades distintas. Inicio actual aporta catálogo para DdaLibrary; no debe ser renombrado sin cambiar su función. LogisticsHome conserva contexto/continuidad del DDA y sus dos acciones principales. DecisionCenter consume casos reales y sus estados; reutiliza trazabilidad/recuperación, sin convertirse en otra implementación del Decision Map. No se diseñan aquí sus APIs ni se implementan pantallas vacías que aparenten funcionalidad.

Un sidebar global y navegación DDA dentro del contenido/topbar son suficientes; evitar dos sidebars completos. El footer de usuario/workspace reemplazará stack técnico customer-facing en la fase del shell. El menú de DDA en catálogo expresa disponibilidad; autorización debe venir de backend/entitlements, nunca del botón oculto.

## Secuencia de migración y gates

1. **Fase 1:** foundation visual opt-in descrita en `04-design-system.md`. Mantener renderer/router/URLs/estado actual. No tocar motores, persistencia ni implementar auth por cambios de CSS.
2. **Fase 2:** introducir identidad/workspace y contratos autorizados; definir cómo se limpian/restauran caches/drafts por sesión. Las opciones de navegación futuras no deben acceder a recursos antes de verificar membership.
3. **Fase 3:** extraer renderer visual inline a módulo con comportamiento equivalente; definir tabla de rutas y adapter legacy; integrar un único shell y menú. Realizar por pasos verificables, primero equivalencia y después nuevas entradas. Mantener `window.dationNavigate`/DationDispatch como bridges mientras existan consumidores.
4. **Fases de producto posteriores:** implementar PlatformHome, DdaLibrary, DataHub y DecisionCenter según roadmap; adaptar datos reales y estados loading/empty/error. Reutilizar DDA, no reconstruirlo ni trasladar sus tablas a páginas globales por copiar markup.

Gates de la extracción futura: deep links D1/D2/legacy, refresh, back/forward, bfcache, cambio rápido entre vistas con requests pendientes, selección/restauración de caso distinto, filtros/drafts, upload, error/retry de estilos, permisos, teclado, viewport y conservación de héroes/toolbar. El cambio de un label no justifica alterar engines o source run.

## Validación disponible y límites de esta auditoría

Se revisaron código, imports, selectores, contratos de carga y tests existentes. Referencias reutilizables: `tests/test_navigation.mjs`, `tests/test_lifecycle.mjs`, `tests/test_home_dda_catalog.mjs`, `tests/test_landing_navigation_contract.py`, `tests/test_dispatch_upload_selectors.mjs`, selectors de dashboard D1/D2 y `tests/browser/test_navigation.py`.

La matriz visual requerida para la implementación incluye 1440/1280, 1024, 768 y 390 px; los breakpoints existentes y riesgos de cascada están documentados en el audit del design system. No se ejecutaron aquí pruebas pesadas, motores ni acciones productivas, ni se declara una nueva auditoría WCAG/runtime completa. Los riesgos de múltiples owners son evidencia de complejidad, no un fallo funcional demostrado en producción.
