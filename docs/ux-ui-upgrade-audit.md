# Dation · UX/UI transversal product audit

Fecha: 2026-10-23 · Base inspeccionada: `1477b41 Add project UX/UI skills for Codex`.
Estado: auditoría y planificación. No se implementaron cambios de producto.

## 1. Executive Summary

Dation tiene una base funcional y visual reconocible: tema oscuro, identidad teal, componentes compartidos, contexto del Case, evidencia persistida y separación real entre Assignment y Scheduling. El upgrade debe consolidar esa base. El mayor retorno está en recuperar espacio operativo, hacer legibles los estados y presentar números y responsabilidades con precisión.

| Prioridad | Hallazgos únicos | Tratamiento |
| --- | ---: | --- |
| P0 · Critical UX | 2 | Resolver antes de una presentación comercial del flujo afectado |
| P1 · Product Quality | 9 | Núcleo del upgrade MVP |
| P2 · Polish | 9 | Consolidación y calidad de uso frecuente |
| P3 · Optional | 4 | Preferencias; requieren una decisión explícita de diseño |
| Total | 24 | Sin duplicar los hallazgos transversales por pantalla |

Los P0 son concretos: el Overview explica partes de un modelo logístico anterior y la barra sticky oculta completamente el campo Descripción enfocado a 375 px. No se encontraron desbordamientos horizontales de página en la matriz principal. La muestra de texto auditable pasó el umbral de contraste aplicable; esto no constituye una certificación WCAG completa.

### Fuente de verdad y límites

Prevalecen `architecture.md`, `domain-model.md`, `navigation.md`, `component-map.md`, `decision-runs.md`, `naming-conventions.md` y `foundation-refactor-summary.md`. Se contrastaron ADR 0001–0010, `data-contracts.md`, auditoría y plan de foundation y documentación de plataforma. Las notas de fases anteriores no reinstalan roles, aprobación de sesión ni limitaciones de motores ya reemplazadas.

Quedan protegidos: identidad de Case y Data Pack; cuatro requisitos de preparación; Apply atómico de atributos/Data Owner; Decision Owner y autoridad real; Runs e idempotencia; aprobación e invalidación al admitir un nuevo Run; motores, handoffs, evidencia, historial, tenancy, APIs, rutas y formatos de sesión. D3 y otros DDAs siguen sin ejecución. El upgrade no cambia estas reglas.

### Método y evidencia

- Lectura de los tres `SKILL.md` solicitados: `ui-ux-pro-max`, `design-taste-frontend` y `emil-design-eng`; para Taste se utilizó la metodología de revisión de aplicaciones existentes de `references/app-screens.md`.
- Inspección del código y la cascada real, sin cargar CSS sustituto. Chromium renderizó el template y los assets actuales mediante un servidor estático local; las APIs fueron interceptadas con los fixtures existentes de `backend/tests/browser/fixtures.json` y el harness de navegación.
- Se capturaron 56 observaciones a 1440×900, 1024×768, 768×1024 y 375×812, más dos dashboards expandidos. Son 13 superficies distintas y una repetición del alias de catálogo/Home; no se cuentan como 14 pantallas independientes.
- Se observaron revisión de D1, detalle de Center/Hub, exportación, ejecución activa/error, movimiento reducido y recuperación de foco. Una comprobación adicional esperó el asentamiento del scroll y muestreó nueve puntos del campo enfocado para confirmar UX-002.
- Se ejecutaron el lint de Taste en modo app y sus funciones `probe`, `app` y `judgeApp` dentro del contexto autenticado del fixture. No se utilizó una nueva sesión del inspector CLI contra producción. Sus señales se revisaron manualmente: una alerta de ausencia de título no se acepta frente al H1 visible medido; tampoco se convierten gradients, iconos, paletas o sombras en problemas críticos por su sola presencia.
- UI UX Pro Max: la primera búsqueda de sistema completo devolvió recomendaciones de sitio comercial; se descartaron. La búsqueda acotada `dense analytics dashboard` produjo una referencia pertinente de BI. Las búsquedas de foco, teclado y resumen de errores complementaron el checklist. No hubo un resultado verificado para Gantt/scheduling; la recomendación temporal se apoya en ADR 0010 y criterio general de información, sin atribuirle una coincidencia inexistente al buscador.
- No se persistió un Design System ni se ejecutaron `break-ui`, `improve-animations` o `review-animations`. No hubo cambios de código, commits, altas de usuarios, decisiones ejecutadas ni aprobaciones. Los POST permitidos al fixture para preflight/preview son consultas; el endpoint local de invitaciones no implementado rechazó su consulta, sin escritura de negocio.

Los scripts, capturas y mediciones de trabajo están fuera del repositorio, en `/workspace/work/ux-audit/`: `measurements.json`, `states.json`, `focus.json`, `taste-measurements.json`, `taste-judgement.json` y `list-states.json`. Los nombres y números sintéticos no describen la operación de un cliente. La fila de Equipo reutiliza únicamente la identidad existente del fixture. No se introdujo contenido ficticio en Dation.

Los primeros sondeos rápidos de oclusión, que no esperaban el scroll, se descartaron como prueba. Las capturas temporizadas de Home no prueban carga/error de datos: el Home actual no consulta esa API. Las verificaciones definitivas se identifican por el estado y el ancho registrado en JSON, no por un nombre provisional de captura.

### Cobertura de superficies

| Superficie | Evidencia revisada | Foco de la evaluación |
| --- | --- | --- |
| Shell y navegación | Runtime, template, CSS y controles | Jerarquías, iconos, labels, foco y espacio útil |
| Home / catálogo | Runtime en cuatro anchos y módulo actual | Hero, accesos, un DDA disponible y seis futuros |
| Decision Center | Lista, vacío de actividad, detalle y fallo local; fuente | KPIs, atención condicional, filtros, historial y archivado |
| Overview Logística | Runtime y texto del template | Explicación, variables, límites y CTA |
| Datos del Case | Runtime con preparación aplicada; fuente | Atributos, Owner, Orders/Fleet, validación y cuatro requisitos |
| Decision Map | Runtime con D1 aprobado/D2 review; fuente | Progreso, nodos, responsables, bloqueo y acciones |
| Configuración D1/D2 | Runtime y revisión D1; fuente de ambas | Alcance, objetivos, recursos, reglas, revisión y Run |
| Execution | Estados locales running/error y reduced motion | Etapa real, espera y vuelta a configuración |
| Dashboards D1/D2 | Esencial y expandido; fuente | Resultado, aprobación, KPIs, evidencia, gráficos, exportación e IA |
| Data Hub | Lista y detalle en escritorio/móvil | Calidad, trazabilidad, preview, acciones y filtros existentes |
| Team | Estado de una persona; error local; fuente | Acceso, responsabilidades, invitaciones y acciones |
| Settings / Profile | Runtime y fuente | Formularios, tabs, estados de guardado y lectura |

Los estados de usuarios ineligibles, conflicto CAS, archivo e invalidación se revisaron en los contratos y consumidores. No se provocaron cambios de asignación ni transacciones para esta auditoría. No se presenta esa revisión como un nuevo E2E de autorización.

## 2. Current visual maturity

Evaluación cualitativa: **producto funcional con foundation reutilizable y consolidación visual incompleta**. Hay coherencia de marca, buenos pares de contraste y patrones sólidos de recuperación, pero la composición combina una aplicación operacional con presentaciones extensas de tipo onboarding.

El problema principal no es falta de decoración. En Config móvil, el hero comienza aproximadamente en y=522 y el primer bloque operativo en y=1193; el hero por sí solo mide unos 528 px. En escritorio, el hero vacío de Datos conserva 260 px. Estos valores corresponden a la muestra demo y varían con contenido y estado; muestran una oportunidad real de densidad, no un límite universal de diseño.

No se asigna una nota numérica de madurez: no hubo prueba con usuarios ni benchmark experimental que la justifique.

## 3. Strengths

- Modelo de producto distinguible: datos → decisiones → evidencia → aprobación humana.
- Case Context, Workflow Hero, Case Flow, Decision Navigator, toolbar y revisión ya tienen implementaciones compartidas. No hace falta un framework nuevo.
- Contraste de texto sólido en la muestra: los mínimos conservadores por superficie principal estuvieron aproximadamente entre 5,52:1 y 6,62:1. El cálculo compone fondos y gradientes; no cubre por completo opacidad heredada, SVG, todos los controles deshabilitados ni todos los estados.
- Estados con texto, iconos y contexto; la selección y la aprobación tienen mecanismos diferentes.
- Tablas alternativas para evidencia gráfica, regiones desplazables con nombre, detalles nativos y exportación conservada.
- Revisión D1, drawers Center/Hub y menú de exportación restituyeron el foco en las comprobaciones realizadas.
- Execution muestra etapas backend e indicador indeterminado, sin porcentaje inventado. Con movimiento reducido no quedaron animaciones activas en la comprobación.
- Los cuatro anchos conservaron el ancho de página. El scroll local de tablas no se confunde con un fallo de reflow de toda la aplicación.

## 4. P0 findings

### UX-001 · El Overview describe restricciones y objetivos históricos

| Campo | Detalle |
| --- | --- |
| ID | UX-001 |
| Severity | P0 · objective UX issue: información que puede inducir decisiones equivocadas |
| Screen / Component | DDA Logística Overview: variables, inputs, límites y FAQ |
| Current | El template anuncia costo/viajes/tiempo como variables actuales, pide fechas/plazo como núcleo y afirma que la flota limita salidas diarias sin ocupación de retorno. Evidencia: `backend/app/templates/app.html:337`, `:431`, `:465`, `:483`; capturas `overview-*`. |
| Problem | Contradice el Data Pack progresivo y la separación Assignment no temporal / Scheduling con ocupación de ciclo. También dificulta distinguir capacidades condicionadas por datos y decisiones futuras. |
| Recommendation | Reescribir esas explicaciones desde los contratos canónicos: núcleo mínimo, objetivos habilitados por evidencia y frontera D1/D2. Mostrar D3 como futuro. Mantener los CTAs, capacidades y gates efectivos. |
| Why | La pantalla que presenta el producto debe explicar el motor y sus límites actuales antes de que alguien configure o apruebe. |
| Skill source | UI UX Pro Max: claridad, jerarquía e información contextual; Taste app: palabras del dominio y evidencia honesta. La autoridad funcional es `domain-model.md`, `data-contracts.md` y ADR 0009/0010. |
| Scope | Page-specific |
| Implementation effort | NORMAL |
| Functional risk | LOW: copy y presentación; no habilitar objetivos ni modificar motores |

### UX-002 · La barra sticky oculta un campo que recibe foco

| Campo | Detalle |
| --- | --- |
| ID | UX-002 |
| Severity | P0 · objective UX issue: foco y edición inaccesibles en la condición reproducida |
| Screen / Component | Datos del Case / Workflow action bar / Case Attributes |
| Current | A 375×812, tras enfocar Nombre, Categoría y Descripción, el textarea queda en y≈554–654 mientras la barra cubre sus nueve puntos muestreados. Se esperaron 450 ms por foco. `focus.json` y `focus-description-375.png`; barra en `dation-design-system.css:188`, offsets en `workflow-context.css`. En escritorio la oclusión de Descripción fue parcial. |
| Problem | El usuario puede escribir sin ver el campo. El foco completamente oculto afecta WCAG 2.2, 2.4.11; la oclusión parcial de escritorio requiere atención, pero no equivale por sí sola a ese incumplimiento AA. |
| Recommendation | Ajustar la ocupación y reserva real de la barra; limitar su altura en móvil y garantizar exposición del campo al tabular. Mantener cuatro requisitos, mensajes, Apply separado y CTA canónico. Verificar con teclado virtual y zoom. |
| Why | La accesibilidad debe funcionar con la geometría final y contenido real, no depender sólo de un `scroll-margin` declarado. |
| Skill source | UI UX Pro Max: focus-not-obscured, fixed-element-offset; Emil: respuesta inmediata y componentes que manejan sus bordes. |
| Scope | Shared component |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM: afecta sticky, scroll y foco compartidos; no cambia readiness |

## 5. P1 findings

### UX-003 · El contexto desplaza el trabajo operativo

| Campo | Detalle |
| --- | --- |
| ID | UX-003 |
| Severity | P1 · objective UX issue |
| Screen / Component | Context Navigation, Case Flow, Workflow Hero y shells D1/D2 |
| Current | En Config a 375 px, hero ≈528 px y primer bloque ≈y1193; Map comienza sus decisiones cerca de y959. Datos conserva un hero copy-only de 260 px en escritorio. `measurements.json`; `tokens.css:123`, `dation-design-system.css`. |
| Problem | Navegación, explicación y marcos consumen la primera vista; la información para operar queda subordinada. |
| Recommendation | Crear variantes de densidad de los componentes existentes y alturas dependientes del contenido. Compactar explicación secundaria manteniendo accesibles las tres responsabilidades de navegación y los límites de cada decisión. |
| Why | La frecuencia de uso exige orientación breve y acceso temprano a la tarea. No se propone encajar todo el dashboard en un viewport. |
| Skill source | Taste app §§2, 4, 10; UI UX Pro Max: jerarquía, densidad y responsive; Emil: frecuencia de uso. |
| Scope | Shared component |
| Implementation effort | FULL |
| Functional risk | MEDIUM |

### UX-004 · El paso actual puede quedar fuera de la franja visible móvil

| Campo | Detalle |
| --- | --- |
| ID | UX-004 |
| Severity | P1 · objective UX issue |
| Screen / Component | Case Flow en Config y Dashboard a 375 px |
| Current | La franja muestra Datos y parte de Map mientras Config/Dashboard están fuera del encuadre inicial. `case-flow.mjs:24` crea el paso actual, sin revelar su posición al montar; capturas `config-d1-375`, `dashboard-d2-375`. |
| Problem | El usuario no ve dónde está aunque exista `aria-current`. La franja parece ofrecer sólo el comienzo del flujo. |
| Recommendation | Hacer visible el paso actual dentro del mismo contenedor o resumir visualmente su estado con acceso a la secuencia existente. Conservar botones, destinos, disabled y jerarquía. |
| Why | El reflow debe preservar orientación además de evitar overflow de página. |
| Skill source | UI UX Pro Max: navegación y estado actual; Taste app §12. |
| Scope | Shared component |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM |

### UX-005 · Texto operativo de 9–10 px disperso

| Campo | Detalle |
| --- | --- |
| ID | UX-005 |
| Severity | P1 · objective UX issue de legibilidad; el tamaño solo no prueba una infracción WCAG |
| Screen / Component | Decision Navigator, heroes, badges, Center e información de evidencia |
| Current | Estados de rail de 9/9,5 px, metadatos y progreso de Center de 10 px, títulos auxiliares de Workflow Hero de 9 px. `dation-design-system.css:126`, `platform-decision-center.css:16`, `measurements.json`. |
| Problem | La información necesaria para distinguir aprobación, revisión y contexto cuesta más que el título decorativo. |
| Recommendation | Reutilizar roles tipográficos actuales: cuerpo operativo 13–14 px, labels/meta normalmente 12–13 px y captions de 11 px sólo donde el espacio lo justifique. Migrar overrides por rol, sin agrandar toda la interfaz. |
| Why | La densidad debe reducir marcos y padding sobrante antes que el texto decisivo. |
| Skill source | UI UX Pro Max: tipografía y contraste; Taste app §9. |
| Scope | Global token, con adaptación de consumidores |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-006 · Los KPIs de Center rompen palabras en móvil

| Campo | Detalle |
| --- | --- |
| ID | UX-006 |
| Severity | P1 · objective UX issue |
| Screen / Component | Decision Center / KPI filters |
| Current | A 375 px, “Pendientes de aprobación” y “Aprobadas” se fragmentan dentro de tarjetas estrechas. `center-375.png`; `.center-kpi` en `platform-decision-center.css`. |
| Problem | El contador queda separado de una etiqueta difícil de reconstruir; la grilla no contempla icono, flecha y texto largo juntos. |
| Recommendation | Mantener los cuatro KPIs y sus filtros. Reajustar las pistas internas y el wrapping por palabras; si hace falta, variar el span o disponer label/valor en filas. |
| Why | Una etiqueta de estado debe poder leerse de un vistazo. |
| Skill source | UI UX Pro Max: compact-label-overflow; Taste app §§5, 12. |
| Scope | Page-specific |
| Implementation effort | FAST |
| Functional risk | LOW |

### UX-007 · Las cifras tabulares no comparten borde numérico

| Campo | Detalle |
| --- | --- |
| ID | UX-007 |
| Severity | P1 · objective UX issue de comparación |
| Screen / Component | Tabla comparativa D1, datos/evidencia y columnas cuantitativas del Hub |
| Current | D1 usa cifras tabulares, pero sus importes, viajes y porcentajes se alinean a la izquierda. Hub también alinea registros a la izquierda. `dashboard-d1-section-950.png`, `measurements.json`, CSS de tablas. |
| Problem | Importes y magnitudes de longitudes distintas no forman columnas fáciles de comparar. |
| Recommendation | Alinear a derecha cada columna numérica y su header, conservar tabular-nums y precisión por métrica. Mantener identificadores y texto a izquierda. |
| Why | Acelera comparación sin quitar evidencia ni modificar valores. No se recalculan totales desde cifras redondeadas. |
| Skill source | UI UX Pro Max: number-tabular; Taste app §7.4. |
| Scope | Shared component: patrones de tabla, con adaptadores de dominio |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-008 · El acceso flotante a IA se superpone a contenido

| Campo | Detalle |
| --- | --- |
| ID | UX-008 |
| Severity | P1 · objective UX issue |
| Screen / Component | Dashboards / Dation IA launcher |
| Current | A 375 px el launcher cruza el relato de fechas; a 1024 px se superpone parcialmente con la zona de herramientas. `dashboard-d2-375-fold.png`, `dashboard-d2-1024-fold.png`; `.dation-chat-fab` en `app.css:7495` y overrides. |
| Problem | El control secundario compite con evidencia y acciones del Run. |
| Recommendation | Reservar una zona segura o integrar el acceso en el marco existente según ancho. Mantener el mismo asistente, conversación y callbacks; verificar launcher, drawer y teclado virtual. |
| Why | La explicación IA no debe tapar lo que explica ni la acción humana principal. |
| Skill source | UI UX Pro Max: fixed-element-offset; Taste app §3.4; Emil: utilidad y respuesta. |
| Scope | Shared component |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM |

### UX-009 · El Hero D1 deja ambiguo qué significa “100 % de flota propia”

| Campo | Detalle |
| --- | --- |
| ID | UX-009 |
| Severity | P1 · objective UX issue de interpretación |
| Screen / Component | Assignment / result summary |
| Current | El texto usa `own_weight_share` pero dice “utilizando 100 % de flota propia”; el KPI inferior sí aclara que mide peso transportado. `assignment-summary.mjs:10`, `:20`; captura de Hero D1. |
| Problem | Puede leerse como uso de toda la flota disponible o utilización de capacidad, dos conceptos diferentes. |
| Recommendation | Explicitar “100 % de la carga en flota propia”, adaptado al valor real. Mantener fórmula y evidencia actuales; usar “Asignación de carga” como nombre canónico donde hoy aparece “Asignación de flota”. |
| Why | El relato ejecutivo debe tener la misma precisión que el detalle técnico. |
| Skill source | Taste app: una pregunta, unidades y baseline explícitos; UI UX Pro Max: labels de datos. Autoridad: `domain-model.md` y naming actual. |
| Scope | Page-specific |
| Implementation effort | FAST |
| Functional risk | LOW |

### UX-010 · “Assignment bloqueada” mezcla dos significados de bloqueo

| Campo | Detalle |
| --- | --- |
| ID | UX-010 |
| Severity | P1 · objective UX issue de estado |
| Screen / Component | Scheduling Hero y contexto upstream |
| Current | D2 muestra “Assignment bloqueada” para explicar que conserva viajes y vehículos ya aprobados. `scheduling-essential.mjs:14`, `:24`; el dominio también usa `locked` para una dependencia todavía no habilitada. |
| Problem | La misma palabra parece indicar tanto una aprobación válida de entrada como falta de habilitación. |
| Recommendation | Aclarar “Asignación aprobada · viajes y vehículos fijos” o equivalente, conservando estado canónico, fuente y restricciones. Diferenciar estado del workflow, calidad del resultado e inmutabilidad upstream. |
| Why | Una aprobación que habilita D2 no debe parecer un impedimento para operar. |
| Skill source | UI UX Pro Max: estado y semántica; Taste app: vocabulario del producto. |
| Scope | Page-specific |
| Implementation effort | FAST |
| Functional risk | LOW |

### UX-011 · Algunos fallos exponen mensajes técnicos sin normalizar

| Campo | Detalle |
| --- | --- |
| ID | UX-011 |
| Severity | P1 · objective UX issue de recuperación |
| Screen / Component | Team / invitaciones recibidas; revisar también errores de formularios e historial |
| Current | El fallo local HTML/501 de `/auth/invitations` mostró un `Unexpected token ... is not valid JSON`. `invitations.mjs:7` parsea JSON directamente y `:18` presenta `error.message`. La consulta falló porque el fixture estático no implementa ese endpoint: no es evidencia de una caída productiva. |
| Problem | El camino de error del frontend puede presentar terminología interna sin explicar qué conserva el usuario ni qué reintentar. |
| Recommendation | Adoptar el vocabulario humano y los estados tipados de recuperación existentes, preservando sesión, permisos, 409 e incertidumbre de red. Mantener el botón local de reintento. |
| Why | Un producto comercial debe explicar el fallo de forma accionable también ante una respuesta no JSON. |
| Skill source | UI UX Pro Max: error-feedback; Emil: perceived performance y estados de error. |
| Scope | Shared component: presentación de errores |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM: no alterar clasificación ni política de reintentos |

## 6. P2 findings

### UX-012 · Las acciones equivalentes usan familias visuales distintas

| Campo | Detalle |
| --- | --- |
| ID | UX-012 |
| Severity | P2 · inconsistencia observable; el estilo final contiene una decisión de diseño |
| Screen / Component | Buttons, hero CTA, review, Apply y toolbar |
| Current | Explorar DDA es teal plano; Ejecutar/Aprobar/Guardar usan gradiente; conviven alturas de 36, 40, 44, 46 y 48 px y estilos locales. `tokens.css`, `platform-components.css:11`, `dation-design-system.css`, mediciones de controles. |
| Problem | La jerarquía depende parcialmente de la página y cuesta distinguir variante, tamaño y estado. |
| Recommendation | Mapear roles primario/secundario/terciario/destructivo y tamaños por contexto sobre las primitivas actuales. Acordar un tratamiento primario coherente; no equiparar Aprobar y ejecutar como acciones funcionales. |
| Why | Consistencia reduce aprendizaje sin exigir controles iguales en todos los contextos. |
| Skill source | UI UX Pro Max: interaction states y primary-action; Emil: press feedback. |
| Scope | Shared component: primitive |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-013 · Bordes, superficies y radios no siempre expresan un rol

| Campo | Detalle |
| --- | --- |
| ID | UX-013 |
| Severity | P2 · inconsistencia observable |
| Screen / Component | Cards, shells, nested panels, badges y dialogs |
| Current | Tokens contemplan radios por rol, pero aparecen 14/16/17/24 px y valores locales; paneles anidados repiten marcos, sombras y fondos. `tokens.css:98`, `platform-data-hub.css`, CSS de dashboards y mediciones de cards. |
| Problem | La elevación y el agrupamiento no siempre corresponden a una diferencia de responsabilidad. |
| Recommendation | Asignar un rol a cada borde/superficie y migrar overrides equivalentes a tokens existentes. Reservar énfasis fuerte para controles, selección y overlays. No hacer una reescritura global de la cascada. |
| Why | Menos marcos repetidos ayuda a distinguir dato, grupo y acción. El valor exacto del radio no es un defecto por sí mismo. |
| Skill source | UI UX Pro Max: elevation y tokens; Taste app §§9–10. |
| Scope | Global token, con migración incremental |
| Implementation effort | FULL |
| Functional risk | MEDIUM |

### UX-014 · La geometría de carga varía entre superficies

| Campo | Detalle |
| --- | --- |
| ID | UX-014 |
| Severity | P2 · mejora de estabilidad percibida |
| Screen / Component | Team, Settings, Hub y Center |
| Current | Center ya tiene skeleton y carga separada de detalle. Team y Settings reemplazan su contenido por un párrafo de carga. `decision-center.mjs:66`, `team.mjs:54`, `workspace-settings.mjs:48`. |
| Problem | La transición entre espera y contenido tiene un peso visual diferente; en formularios puede desaparecer la estructura de trabajo. No se midió CLS ni latencia real. |
| Recommendation | Alinear la presentación de carga por tipo de superficie, mantener shell y geometría útil, y preservar el draft según el contrato existente. Separar consulta inicial, actualización y envío en curso. |
| Why | Una espera comprensible no necesita shimmer ni duración inventada. |
| Skill source | UI UX Pro Max: content-jumping/loading; Taste app §11; Emil: perceived performance. |
| Scope | Shared component |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM |

### UX-015 · La descripción de filtros depende del contexto visual

| Campo | Detalle |
| --- | --- |
| ID | UX-015 |
| Severity | P2 · consistencia y reconocimiento |
| Screen / Component | Search/filter rows de Center y Hub |
| Current | Center usa labels de filtro sólo para lectores de pantalla, mientras Hub muestra labels sobre selects. Los valores largos se recortan en móvil. `decision-center.mjs:76`, `data-hub.mjs`, capturas a 375 px. |
| Problem | “Todos…” pierde significado al truncarse y los dos portfolios enseñan patrones visuales diferentes. Las etiquetas accesibles existentes sí son una fortaleza. |
| Recommendation | Dar identificación visible compacta al filtro cuando el valor no baste; unificar alturas y espacios. Conservar búsqueda, opciones, paginación y semántica de filtros. |
| Why | Se puede mejorar reconocimiento sin crear nuevos filtros ni ocultar los existentes. |
| Skill source | UI UX Pro Max: form labels y truncation; Taste app §4.4. |
| Scope | Shared component |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-016 · Algunas acciones inline tienen un área pequeña

| Campo | Detalle |
| --- | --- |
| ID | UX-016 |
| Severity | P2 · ergonomía; no se declara incumplimiento automático de WCAG |
| Screen / Component | Acciones del catálogo, detalles/evidencia y summaries |
| Current | Abrir DDA mide unos 18 px de alto y algunos enlaces de viaje unos 13 px en el análisis expandido. `measurements.json`; acciones de evidencia D1 y catálogo. |
| Problem | Requieren más precisión que los botones de 40–48 px, particularmente al compartir fila con otras acciones. |
| Recommendation | Aumentar el hit area sin agrandar el texto ni cambiar la acción. Evaluar 24×24 CSS px y excepciones WCAG 2.5.8; adoptar 40–44 px como objetivo de comodidad donde quepa. |
| Why | Un icono o enlace visualmente pequeño puede tener un área operable mayor. Las unidades pt/dp de las Skills no se trasladan a esta web. |
| Skill source | UI UX Pro Max: web-target-size y touch-spacing; Emil: respuesta al press. |
| Scope | Shared component: primitive |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-017 · El margen SLA aparece sin nombrar la magnitud firmada

| Campo | Detalle |
| --- | --- |
| ID | UX-017 |
| Severity | P2 · claridad analítica |
| Screen / Component | Scheduling / tabla y badges SLA |
| Current | Aparece “Fuera de fecha · -27 d”. El selector calcula margen hasta la fecha objetivo, no una duración negativa de viaje. `scheduling-essential.mjs:6`, `scheduling-dashboard-selectors.mjs:13`. |
| Problem | El signo puede leerse como días negativos de tardanza al no llamarse “margen”. |
| Recommendation | Nombrar la medida: “Margen SLA: −27 días”, con estado y fechas disponibles. Conservar el número y categoría actuales; no cambiar cálculo, umbrales ni SLA. |
| Why | Unidades y significado del signo deben acompañar al valor. |
| Skill source | Taste app: figures, baseline y cambios firmados; UI UX Pro Max: data labeling. |
| Scope | Page-specific |
| Implementation effort | FAST |
| Functional risk | LOW |

### UX-018 · Los cambios de unidad y precisión dificultan la lectura transversal

| Campo | Detalle |
| --- | --- |
| ID | UX-018 |
| Severity | P2 · consistencia de presentación |
| Screen / Component | Result summary, KPI context y tablas D1/D2 |
| Current | La misma carga se presenta compactada en toneladas en D1 y en kg en D2; cantidades, moneda y fechas usan helpers de familias distintas. `assignment-summary.mjs:6`, `scheduling-essential.mjs:22`, `shared.mjs`, `workspace-format.mjs`. |
| Problem | El lector tiene que reconciliar formatos al seguir el mismo Case entre decisiones. No implica que los valores estén mal calculados. |
| Recommendation | Definir formato por rol —resumen, comparación, evidencia— y explicitar conversiones visuales existentes. Respetar configuración de workspace y contratos vigentes; no convertir monedas ni reescribir resultados. |
| Why | La compactación puede ser útil si la equivalencia y precisión son previsibles. |
| Skill source | UI UX Pro Max: number-formatting; Taste app §7.4. |
| Scope | Shared component: presentación de métricas |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM |

### UX-019 · El shell mezcla glifos de fuente y SVG de producto

| Campo | Detalle |
| --- | --- |
| ID | UX-019 |
| Severity | P2 · inconsistencia de representación |
| Screen / Component | Sidebar global frente a acciones y navegación del workflow |
| Current | Inicio, Center, Datos, Equipo y Configuración usan caracteres como `⌂`, `◎`, `♙` y `⚙`; el workflow usa SVG lineales. `app.html:43` y `decision-ui.mjs`. |
| Problem | Los glifos cambian de peso, baseline y representación según el sistema operativo; se nota especialmente en el rail móvil sin labels visibles. |
| Recommendation | Reutilizar el lenguaje SVG local, conservando destinos y nombres accesibles. Verificar identificación del icono compacto mediante ayuda accesible, sin cambiar la arquitectura de navegación. |
| Why | Un solo lenguaje gráfico hace más reconocibles las mismas acciones entre vistas. |
| Skill source | UI UX Pro Max: icon consistency y contexto semántico; Taste app §3.2. |
| Scope | Shared component: shell |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-020 · Falta una vía visible de salto al trabajo principal

| Campo | Detalle |
| --- | --- |
| ID | UX-020 |
| Severity | P2 · eficiencia de teclado |
| Screen / Component | Shell / main / cambio de vista |
| Current | Existe landmark `main`, pero no se encontró skip link para saltar el bloque repetido de navegación. `app.html:78`; shell y navegación mantienen varios controles antes del formulario. |
| Problem | Usuarios de teclado recorren controles globales antes de retomar trabajo. La existencia de `main` evita afirmar que no hay mecanismo alguno de bypass para tecnología asistiva. |
| Recommendation | Añadir una vía de salto visible al foco y una política coherente de foco de vista, compatible con los restauradores de foco existentes. No robar foco en polling ni al abrir disclosures. |
| Why | Reduce repetición sin reemplazar el router ni los destinos. |
| Skill source | UI UX Pro Max: skip-links y focus-on-route-change; Emil: frecuencia de uso. |
| Scope | Shared component: shell |
| Implementation effort | NORMAL |
| Functional risk | MEDIUM |

## 7. P3 findings

### UX-021 · Menor protagonismo de la fotografía de camión

| Campo | Detalle |
| --- | --- |
| ID | UX-021 |
| Severity | P3 · design preference |
| Screen / Component | Heroes de dashboards D1/D2 |
| Current | Fotografías diferentes ocupan una parte considerable del marco. El contraste de texto muestreado pasa; no se presenta la imagen como un fallo de accesibilidad. |
| Problem | Puede acercar el tono a una presentación comercial más que a una herramienta de análisis cotidiano. |
| Recommendation | Comparar una variante más discreta con el tratamiento actual una vez resuelta UX-003, sin quitar narrativa ni evidencia. |
| Why | El beneficio es de dirección de arte y requiere comparar variantes, no una prohibición de Taste. |
| Skill source | Taste app: foco del producto y chrome; Emil: frecuencia de uso. |
| Scope | Page-specific |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-022 · Catálogo futuro más compacto

| Campo | Detalle |
| --- | --- |
| ID | UX-022 |
| Severity | P3 · design preference |
| Screen / Component | Home / DDA Catalog |
| Current | Un DDA disponible y seis futuros se presentan en tarjetas de altura similar; se comunican correctamente los próximos. |
| Problem | La proporción de catálogo futuro puede dominar una demo del MVP, aunque Logística ya tiene un acceso directo. |
| Recommendation | Evaluar menor peso o altura para capacidades futuras, conservando todas sus etiquetas, categorías y estado disabled. No mover el catálogo a otra ruta. |
| Why | Es una elección de énfasis comercial, no una corrección de navegación. |
| Skill source | Taste app: densidad por datos reales y primer trabajo; UI UX Pro Max: jerarquía. |
| Scope | Page-specific |
| Implementation effort | NORMAL |
| Functional risk | LOW |

### UX-023 · Una nueva familia tipográfica no es necesaria para el MVP

| Campo | Detalle |
| --- | --- |
| ID | UX-023 |
| Severity | P3 · design preference |
| Screen / Component | Identidad tipográfica global |
| Current | Se declara Inter con fallbacks del sistema. No se verificó paridad de la fuente realmente utilizada en todos los sistemas operativos. |
| Problem | Una tipografía distinta podría aportar carácter, pero no resuelve por sí sola jerarquía, legibilidad ni densidad. |
| Recommendation | Conservar la familia actual como primera opción y verificar carga/fallback y cifras tabulares antes de considerar otra. No adoptar automáticamente Fira Code/Fira Sans de la búsqueda genérica. |
| Why | Un cambio de fuente abre reflow y QA amplios con retorno incierto. |
| Skill source | UI UX Pro Max: font-loading/number-tabular; Taste app: face from the product, adaptado a marca existente. |
| Scope | Global token |
| Implementation effort | FULL |
| Functional risk | MEDIUM |

### UX-024 · Motion adicional sólo si ayuda a comprender

| Campo | Detalle |
| --- | --- |
| ID | UX-024 |
| Severity | P3 · design preference |
| Screen / Component | Drawers, popovers y feedback secundario |
| Current | Coexisten aperturas instantáneas, transiciones cortas y tokens 140/220 ms. La ausencia de una animación no constituye un defecto. |
| Problem | Podría afinarse continuidad en interacciones ocasionales; añadirla indiscriminadamente haría más lento el uso frecuente. |
| Recommendation | Probar transiciones breves sólo donde expliquen origen/cierre y no difieran el input. Conservar interacción inmediata por teclado y reduced motion; sin librería ni coreografía nueva. |
| Why | El beneficio debe superar el coste de repetir la animación durante la jornada. |
| Skill source | Emil: animation decision framework y origin-aware popovers; UI UX Pro Max: reduced-motion. |
| Scope | Shared component |
| Implementation effort | NORMAL |
| Functional risk | LOW |

## 8. Cross-platform inconsistencies

| Patrón transversal | Observación | Nivel prioritario de intervención |
| --- | --- | --- |
| Jerarquía | Heroes de 260–528 px frente a encabezados sencillos en Team/Settings | Shared hero / page header, UX-003 |
| Tipografía | Roles de plataforma definidos, anulados por 9–10 px locales | Token → consumidores, UX-005 |
| Acciones | Teal plano, gradiente y variantes locales de la misma familia | Primitive → toolbar/action bar, UX-012 |
| Marcos | Radios 14/16/17/24, bordes y sombras apilados | Token por rol → shared component, UX-013 |
| Tablas | Tabular-nums parcial y alineación numérica izquierda | Patrón compartido → adaptadores, UX-007 |
| Estados | Locked vs entrada aprobada fija; nombre de cuota propia ambiguo | Copy del dominio, UX-009/010 |
| Filtros | Label visual en Hub, sólo accesible en Center | Primitive/form row, UX-015 |
| Feedback | Skeleton en Center, párrafo en Team/Settings, mensajes de error de fuentes distintas | Componente compartido, UX-011/014 |
| Iconos | Glifo del sistema frente a SVG local | Shell/primitive, UX-019 |

Orden de resolución: **token → primitive → shared component → page-specific override**. No se deduce que dos componentes con dominio diferente deban compartir todo su markup.

## 9. Accessibility

Prioridad inmediata: UX-002. La legibilidad pequeña, áreas operables, orientación y bypass se abordan en UX-004/005/016/020. La revisión D1 abrió con foco en Volver y lo devolvió al trigger al cerrar con Escape, en 1440 y 375 px; los detalles de Center/Hub también restituyeron foco en ambos anchos.

Los colores de texto aprobados y los estados con texto/icono deben preservarse. Todavía se requiere verificar bordes de control significativos y foco a 3:1, zoom 200/400 %, lectores de pantalla, alto contraste, labels completos al truncar, opacidad compuesta y teclado virtual real. 11 px es aquí un criterio de diseño para captions, no un mínimo WCAG universal. 44 px es una meta ergonómica, no la definición del mínimo web AA de 24 CSS px con excepciones.

Gráficos: conservar resúmenes y tablas. El renderer no aporta navegación de puntos con teclado; no se declara toda la visualización inaccesible porque ya hay alternativas. Comprobar por gráfico si todo dato exclusivo de tooltip tiene una alternativa equivalente. No añadir controles de zoom o filtrado que cambien la funcionalidad sin evaluar su alcance.

## 10. Responsive

| Ancho | Resultado observado | Prioridad |
| --- | --- | --- |
| 1440 px | Página sin overflow; hero copy-only de Datos sobredimensionado; números de tabla desalineados | Densidad y BI; revisar oclusión parcial sticky |
| 1024 px | Página sin overflow; sidebar conserva labels y se estrecha el canvas; launcher IA invade herramientas en la muestra D2 | Revisar combinación de navegación, toolbar y contenido |
| 768 px | Rail compacto y grillas replegadas; barra de datos puede ocupar una banda importante | Altura sticky y labels antes de reducir tipografía |
| 375 px | Página sin overflow; paso actual fuera de vista, labels KPI fragmentados, textarea oculto y largos preámbulos | UX-002/003/004/006/008 |

Center y Hub ya convierten sus filas en tarjetas a anchos pequeños; Team conserva scroll local de tabla. No se propone rehacer móvil. En Team, reforzar la orientación del scroll y el acceso a rol, responsabilidades y acciones sin quitar columnas. La nueva validación debe incluir nombres largos, teclado virtual, orientación horizontal y estados vacíos/errores, no sólo la muestra poblada.

## 11. Dashboard/BI presentation

**Assignment:** conservar el relato de carga/viajes, evidencia de distribución, políticas y comparación. Precisar la cuota por peso de flota propia; distinguir utilización por viaje de disponibilidad temporal. Alinear cifras y reducir el peso de marcos para llegar antes a la conclusión y al plan.

**Scheduling:** conservar horizonte, SLA, espera, recurso crítico y timeline de ocupación con retorno. Nombrar el margen firmado y explicar que los viajes provienen del Assignment aprobado. La timeline debe seguir mostrando calendario, no convertirse en una curva de tendencia por una sugerencia genérica de Skill.

En ambos: unidades explícitas, cero distinto de ausente, ejes/leyendas cercanos, semántica estable de series y una alternativa tabular. Reducir tinta decorativa antes de reducir datos. Mantener comparación esencial/avanzada, resumen IA, warnings y exportación. Un panel de validación en otro lugar de la página no debe esconder las excepciones ya resumidas en el Hero.

No se cambian cálculos, objetivos, certificación del solver ni precisión persistida. Tampoco se confunde `analysis_depth`, que puede controlar escenarios ejecutados, con el disclosure visual de análisis avanzado.

## 12. Interaction quality

La siguiente tabla es una revisión de Emil: **After es propuesta, no implementación**.

| Before | After | Why |
| --- | --- | --- |
| Campo enfocado bajo sticky | Área operativa libre y scroll/foco verificados con altura real | El feedback sólo sirve si el control permanece visible |
| Acciones inline diminutas | Misma acción con hit area y foco suficientes | Menos precisión manual sin inflar densidad |
| Error técnico de parsing en invitaciones | Mensaje humano y reintento local, con clasificación preservada | Explica recuperación sin exponer implementación |
| Párrafo de carga en Team/Settings y skeleton en Center | Geometría estable por tipo de superficie | Reduce incertidumbre y saltos percibidos |
| Press/hover definidos por distintas familias | Estados por rol, sin mover la distribución de la página | Consistencia al usar la herramienta repetidamente |
| Motion elegido por disponibilidad técnica | Movimiento sólo con propósito; teclado inmediato y reduced motion | Evita coste repetitivo en una aplicación de jornada completa |

Ya funcionan bien: Escape y devolución de foco en las muestras; stages reales; error terminal que conserva evidencia y ofrece Volver a configuración; ausencia de porcentaje ficticio; cleanup compartido y cancelación por ruta. No se midieron INP, FPS, duración de solver ni rendimiento de producción.

## 13. Areas already strong and that should NOT be changed

1. La arquitectura funcional y la autoridad de SQL/backend, incluidos ownership, aprobación, invalidación e idempotencia.
2. Los componentes canónicos y límites de responsabilidad: shared behavior, contenido D1/D2 específico y un único coordinador de workspace.
3. Los cuatro requisitos independientes de preparación y la separación entre Apply, review y ejecución.
4. Case Context nativo, revisión antes del Run y herramientas de evidencia/exportación; mejorar su presentación sin sustituir contratos.
5. Datos persistidos, históricos, fingerprints, actores de aprobación y compatibilidad de motores/URLs/sesiones.
6. El tema oscuro y la identidad teal como punto de partida. Taste no autoriza convertirlos automáticamente a negro puro o a otra paleta.
7. Los pares de contraste sólidos, textos de estado, tablas accesibles y comportamiento reduced motion ya presente.
8. El catálogo honesto de capacidades futuras deshabilitadas y la frontera Assignment/Scheduling.

Siguientes documentos: [propuesta](ux-ui-upgrade-proposal.md) y [roadmap](ux-ui-upgrade-roadmap.md). Su existencia no autoriza implementación.
