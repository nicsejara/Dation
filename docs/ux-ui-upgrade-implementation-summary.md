# Dation — UX/UI upgrade implementation summary

Estado: **Completed — fases 0 a 8**. Fecha: 2026-10-23 (America/Buenos_Aires).

Base: `ee404b1 Add UX UI upgrade audit and roadmap`. Rama local: `ux-ui/commercial-mvp-upgrade`.
El master prompt autorizó implementación autónoma por fases. Este trabajo no incluye push ni despliegue.
La documentación funcional vigente sigue siendo la fuente de verdad. La auditoría y la propuesta originales permanecen sin cambios.

## Resultado y decisiones visuales

Se conserva Dation: Inter, paleta mineral oscura, teal reservado para acciones/selección y navegación aprobada. El upgrade mejora lectura, densidad, feedback y acceso a la evidencia. No incorpora dependencias, framework, store, fuentes, archivos CSS paralelos ni KPIs.

- Tokens antes de consumidores: títulos de trabajo 24–32 px, secciones 16–20 px, labels operativos 12–13 px y captions auxiliares de 11 px. Se conservan escalas de espacio y roles de radio distintos para panel, control, hero y overlay.
- Acciones primarias con contraste consistente; roles secundarios, ghost y destructivos mantienen su función. Disabled y busy siguen ligados a los guards existentes.
- Ayuda contextual desplegable en el Workflow Hero; Case Flow visible y desplazamiento horizontal al paso actual. No aparece un segundo selector global de Case.
- La barra de acciones fluye con el documento en anchos limitados y durante edición. Los requisitos y la progresión no desaparecen.
- Números alineados y unidades explícitas. El launcher IA ocupa espacio real en la toolbar y no cubre tablas o exportación.
- Las animaciones repetidas se retiran. El foco, la selección, los estados de trabajo y los mensajes siguen dando feedback inmediato.

## Commits por fase

| Fase | Commit | Alcance |
| --- | --- | --- |
| 0 | `ebd4089` | define visual system roles |
| 1 | `5b0c717` | upgrade shell and primitives |
| 2 | `c4afce0` | compact core decision workflow |
| 3 | `93af44b` | refine decision configuration |
| 4 | `6017263` | upgrade decision dashboards |
| 5 | `9aa532c` | align supporting screens |
| 6 | `c0fd0fb` | polish interaction feedback |
| 7 | `42c0703` | close responsive accessibility gaps |
| 8 | Este commit de estabilización | break-ui, correcciones finales, fixtures y documentación |

## Findings

Los estados scoped respetan los límites del master prompt. No representan cambios del modelo de decisión.

| ID | Estado | Resultado / motivo |
| --- | --- | --- |
| UX-001 | Implemented | Overview fiel al Data Pack progresivo, D1/D2 y capacidades condicionadas; D3 futura. |
| UX-002 | Implemented | Barra en flujo normal en anchos limitados y mientras un campo tiene foco; cuatro requisitos conservados. |
| UX-003 | Implemented | Workflow Hero compacto con ayuda nativa desplegable; menos espacio previo al trabajo. |
| UX-004 | Implemented | Case Flow revela el paso actual horizontalmente al entrar y al redimensionar, sin mover el foco. |
| UX-005 | Implemented | Estados del Decision Navigator y metadatos operativos a 12 px; captions auxiliares a 11 px. |
| UX-006 | Implemented | KPI de Center con palabras completas, fila numérica propia y cifras extensas sin truncar. |
| UX-007 | Implemented | Columnas numéricas identificadas y alineadas a derecha, con tabular figures. |
| UX-008 | Implemented | Launcher IA único integrado en toolbar D1/D2; mismos callbacks y conversación. |
| UX-009 | Implemented — scoped | La narrativa de own_weight_share describe carga transportada en flota propia; sin rename general. |
| UX-010 | Implemented | Upstream D2 identificado como asignación aprobada, con viajes y vehículos fijos. |
| UX-011 | Implemented — scoped | Invitaciones y Profile presentan fallos sin exponer el parser; preservan status, conflictos y guards. |
| UX-012 | Implemented | Roles Primary/Secondary/Ghost/Destructive y tamaños compactos sobre la familia existente. |
| UX-013 | Implemented | Roles de superficie y radio en tokens; paneles de Config y componentes compartidos consolidados. |
| UX-014 | Implemented | Carga de Team/Settings/Center reutiliza geometría y skeletons del sistema existente. |
| UX-015 | Implemented | Labels visibles en filtros de Center, con asociación nativa preservada. |
| UX-016 | Implemented | Áreas operables ampliadas en Abrir DDA y detalles de viajes; tablas locales alcanzables por teclado. |
| UX-017 | Implemented | Margen SLA nombrado y expresado en días; mismo signo, valor y categoría. |
| UX-018 | Implemented — presentation | Formato compartido de peso; kg en evidencia detallada y t en resúmenes. Sin mutar valores ni exportaciones. |
| UX-019 | Implemented | SVG del registro existente en navegación global, con nombres accesibles. |
| UX-020 | Implemented | Skip al main y foco tras navegación explícita por teclado; no sigue polling ni cambios de workspace. |
| UX-021 | Deferred | Fotografía de dashboards conservada por instrucción expresa. Sin cambios de assets. |
| UX-022 | Deferred | Catálogo futuro conservado; compactarlo queda fuera de esta etapa. |
| UX-023 | Deferred | Inter conservada; no se incorporó otra familia. |
| UX-024 | Reviewed / Deferred additive motion | Se retiró movimiento sin propósito; no se añadió motion ornamental. Feedback y reduced-motion conservados. |

## Componentes y archivos principales

- `backend/app/static/css/tokens.css`, `dation-design-system.css`, `platform-components.css`: roles, acciones, foco, barra de workflow y geometría de carga.
- `workflow-context.css`, `decision-map-case-v2.css`, `dda-logistics-upload.css`, CSS de Config D1/D2: densidad, formularios, metadatos y reflow.
- `backend/app/static/js/dispatch/decision-config-ui.mjs`, `navigation/case-flow.mjs`: ayuda nativa y revelado del paso actual. Las funciones de disponibilidad y destino mantienen su lógica.
- Shells D1/D2, `runs/dashboard-toolbar.mjs`, `assignment-essential.mjs`, `assignment-evidence.mjs`, `scheduling-essential.mjs`, `scheduling-advanced.mjs`, `shared.mjs`: presentación de evidencia, unidades, alineación y launcher. Exportadores y selectors de negocio no cambian.
- `backend/app/static/js/platform/{shell,components,decision-center,team,workspace-settings,invitations,data-hub}.mjs`: acceso al contenido, carga, filtros, mensajes e iniciales por grafema.
- `backend/app/templates/app.html`, `dda-logistics-landing.js`, `ui.js`: copy vigente, skip, SVG y scroll inmediato de activación de vista.
- `backend/tests/browser/test_ux_upgrade.py`, `test_ux_upgrade_stress.py` y fixtures adyacentes: regresiones de foco, estado, payload/evidencia y contenido extremo.

## Preservación funcional

Se verificó que los **120 archivos protegidos de backend, motores, SQL y dependencias** mantienen el SHA-256 de la base. Ningún cambio afecta servicios, rutas API, migrations, workers, configuración funcional, assets o Skills. Los cambios de aplicación están en HTML/CSS/JS de presentación.

| Invariante | Evidencia |
| --- | --- |
| DDA → Case → Decision → Run | Navegación y restore vigentes; E2E golden con personas distintas. |
| Mismo Case al editar atributos/owners o ejecutar de nuevo | Saga 3 y Saga 5 E2E; historial preservado. |
| Orders / Fleet / Attributes applied / Data Owner independientes | Browser de atributos antes de CSV y readiness E2E. Aplicar continúa disponible sin CSV. |
| Un Data Owner por Case y un Decision Owner por Case/Decision | E2E de responsabilidades, elegibilidad y aislamiento. No se reintroducen roles eliminados. |
| Aprobación humana de un Run específico | E2E y prueba browser de aprobación única ante clics repetidos; autoridad backend/SQL. |
| Admisión e invalidación downstream | Saga 3 real ejecuta nuevas D1/D2, conserva evidencia e invalida downstream según contrato. |
| Assignment no temporal; Scheduling hereda Assignment aprobado | Engines y contratos sin cambios; E2E con motores reales. D2 no reasigna viajes, cargas ni vehículos. |
| Idempotencia, fingerprints, creator y approval actor | E2E de reruns/historia y golden; exportación JSON browser idéntica al resultado persistido. |
| APIs, tenancy y permisos | Archivos sin cambios; E2E de límites de workspace, Viewer y operadores no asignados. |
| D3 futura y disabled | Guards y routing intactos, más indicación informativa en Overview. |

## QA

Resultados verificados en este entorno, sin pruebas contra producción:

| Comprobación | Resultado |
| --- | --- |
| Python `unittest discover -s tests -v` | **383 pasan**. Baseline previo: también 383 pasan. |
| Node `node --test tests/test_*.js tests/test_*.mjs` | **18 suites/archivos pasan**. |
| Browser de cierre: atributos, Saga 3/5, componentes, plataforma, Settings, UX y break-ui | **33 pasan**. |
| Navegación adversarial | 8 escenarios pasan inicialmente; el noveno detectó el observer global. Tras corregirlo, disposal y revelado del paso actual pasan. |
| Config D1/D2 con review, reglas/custom y footer | Verificada en cinco anchos; el test ahora exige CTA visible y contenido sin oclusión, en lugar del padding vacío anterior. |
| E2E Docker aislado: `test_v2_golden`, `test_saga3`, `test_saga5_attributes` | **11 pasan**, con motores reales y 6 Runs en la prueba de reapertura/invalidez. |
| JS | Sintaxis verificada para 25 archivos JS, incluyendo el toggle de fixture; imports nativos y cleanup cubiertos por browser. |
| Diff / alcance | `git diff --check` limpio; auditoría/propuesta originales idénticas; 120 hashes protegidos sin cambios. |

Matriz principal: **1440×900, 1024×768, 768×1024, 375×812**. Se registraron 57 observaciones de pantallas y disclosures en Phase 7 y 44 de reflow a **320×640, 812×375 y 720×450**. Ninguna tuvo overflow de página, headings ausentes ni fallos en el muestreo de contraste. Tras los últimos ajustes tipográficos, otras 26 observaciones de Home/Overview/Config/dashboards tampoco mostraron overflow ni fallos muestreados. Las tablas extensas conservan scroll local.

Se comprobó foco por tabulación y nueve puntos del campo, skip al main, `aria-current`, labels, status/alert, Escape, cierre/reapertura y retorno de foco, menús/drawers, acciones repetidas, back/forward, reload, selección de Case/Decision/Run y respuestas tardías. La altura **375×420** simula el espacio que puede dejar un teclado virtual; **720×450** es reflow equivalente a 200 % sobre 1440×900. No se presenta esto como una prueba de teclado físico móvil ni como certificación WCAG completa.

Los logs/capturas de esta sesión están en `/workspace/work/ux-upgrade/`. Los tests y fixtures reproducibles permanecen en el repositorio.

### Baseline failures y cambios de expectativas

Tres pruebas históricas se ejecutaron también sobre un checkout limpio de `ee404b1` y fallaron de la misma manera:

- `test_both_configuration_contexts_are_closed_and_scheduling_source_stays_visible`: exige “Cambiar datos”; el baseline ya muestra “Cambiar Data Pack”.
- `test_toolbar_approval_is_unique_direct_and_preserves_continuation`: busca `[data-approve-final]`, retirado antes de esta etapa.
- `test_scheduling_uses_shared_menus_drawer_and_exports_without_format_changes`: exige tres botones en “Más”; el baseline tiene uno.

No se declaran verdes ni se reinstalan esos controles. Las pruebas nuevas verifican el launcher vigente, retorno de foco, exportación JSON exacta y aprobación única por Run. Las aserciones de fuente que fijaban el copy anterior, la ubicación antigua del launcher, el hover translate y las filas/padding fijos se actualizaron para reflejar los cambios UX autorizados. No se relajan aserciones de payload, permisos, approval o invalidación.

### Motion review

Se aplicaron `improve-animations` y `review-animations` sólo en Phase 6. Auditoría y review de source fueron read-only; el master prompt autorizó implementar las correcciones. La revisión del diff dio **Approve**, complementada por 11 browser tests y observación del review a 375 px con ambas preferencias de movimiento.

| Before | After | Why |
| --- | --- | --- |
| Entradas de vista/trace/Config y review repetidas | Aparición inmediata | Evita movimiento repetido en navegación y teclado. |
| Hover/foco trasladaba tarjetas/iconos | Color, borde, selección y sombra | Feedback sin desplazar el objetivo. |
| Pesos animaban width | Actualización directa | No anima layout mientras se edita. |
| Drawer del Center repetía entrada | Apertura inmediata | Interrupción/cierre sin reiniciar keyframes. |
| Scroll suave al activar una vista | Scroll inmediato | El destino se establece antes de enfocar el nuevo contenido. |

### break-ui

La fixture usa límites reales y valores plausibles. El toggle **Demo data / Worst case / Empty / One** vive en `backend/tests/browser/fixtures/ux-upgrade-stress-toggle.js` y sólo se inyecta desde el test; no está enlazado desde la aplicación ni añade rutas de producto.

| Campo | Fuente / límite | Valor probado |
| --- | --- | --- |
| Nombre/Description del Case | `app/models/case_identity.py`: 120 / 1000 caracteres | Nombre operativo largo; descripción de 1000 caracteres. |
| Perfil | `app/platform/routes.py` y `auth_routes.py`: 100 por nombre, email 254 | Emoji compuesto, nombres multilingües, email extenso. |
| Team | API paginada, default 25, máximo 50 por request | 25 filas de un total de 1284; Admin/Operator/Viewer, responsabilidades y estados distintos. |
| KPI global | Enteros publicados por API, sin límite visual específico | 0, 1, 1284 y 1.000.000. |
| Dataset | Filename y row_count de fixture/API | Nombre CSV extenso; 1284 registros. |
| Números de presentación | Valores existentes formateados | Moneda 12345678.9, cero, null, decimal y signo negativo. |

| Qué se rompió | Causa | Corrección |
| --- | --- | --- |
| 1.000.000 se fragmentaba verticalmente | Valor compartía una pista demasiado estrecha con icono/flecha | Fila numérica completa, formato de workspace y tamaño adaptable sin truncar. |
| Avatar con emoji producía un surrogate incompleto | Inicial tomada por índice UTF-16 | `personInitials` compartido con `Intl.Segmenter` y fallback por codepoint. |
| Observer activo al abandonar Case Flow | Seguía observando una navegación oculta | Observar sólo durante el flujo; disconnect al salir y al disponer el shell. |

Los 4 tests de estrés pasan. Nombres/archivos largos, local scroll, 0/1, paginación y salida de Team durante fetch resistieron. La prueba de descripción se amplió para comprobar el textarea real de 1000 caracteres a 320 y 1440 px.

## Limitaciones y próximo trabajo

- La suite browser histórica completa conserva las tres incompatibilidades de test reproducidas arriba; no se declara que todo ese suite pase.
- Validación visual/interactiva en Chromium. No se probó Safari, lector de pantalla manual ni IME de un dispositivo físico. Contraste es muestreo automatizado, no conformidad WCAG integral.
- UX-021/022/023 se difieren por decisión expresa; UX-024 queda sin motion adicional. No se construyó nueva inteligencia BI ni se alteraron outputs del solver.

Siguiente fase recomendada: **Data Pack / Decision Model / Engine / BI optimization**. El objetivo es mejorar datos, modelo, capacidades y evidencia del motor antes de invertir en otra ronda estética general.
