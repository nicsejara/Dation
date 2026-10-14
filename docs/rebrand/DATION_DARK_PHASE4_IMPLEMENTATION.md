# Dark Rebrand / Grow-Up — Fase 4: Configuración

## A. Alcance

Assignment y Scheduling adoptan superficies, formularios, filtros, revisión y editor temporal dark. Se retira «Profundidad del análisis» de configuración, review, resumen y badge/detalles de la toolbar. No cambia la serialización de históricos, la API, el esquema de Supabase ni el motor. Las páginas de dashboard y sus menús siguen en Fase 5.

## B. Componentes y propietarios

`decisionAdvancedOptionsSection()` contiene la sección 04 compartida. Sus tres opciones por decisión son botones nativos disabled, con `aria-disabled`, texto y «Próximamente». Carecen de handlers, nombres de formulario, estado o campos de payload. Assignment: límite de tercerización, utilización mínima y reglas por proveedor. Scheduling: buffer, ventanas por recurso y penalización por atraso.

`workflow-action-bar.mjs` es el componente DOM de Data Pack, Assignment y Scheduling. `configSummaryBar()` entrega el adaptador; `mountConfigActionBar()` lo monta y mide con ResizeObserver bajo el lifecycle existente. Cada rerender desconecta la medida anterior. La configuración conserva validación y revisión antes de ejecutar. Tres chips navegan a Alcance/Ventana, Objetivo y Recursos. El CTA estable dice «Revisar y ejecutar». La reserva inferior usa la altura medida más gap y safe area, incluso en móvil.

Las hojas de Config y del editor son dueñas de su migración; el DS contiene sección avanzada y variante compacta de la barra. Los diálogos nativos de Config salen del bridge light. Los loaders de estas hojas comparten identidad por pathname y actualizan su versión sin duplicar links. El disclosure nativo de Data Pack y la fuente aprobada de Scheduling se mantienen.

## C. Estado, ejecución e históricos

Las nuevas Assignment envían explícitamente `options.analysis_depth: "essential"`. Se retira `state.analysisDepth`, su default/reset, draftFields y restauración desde runs anteriores. Los borradores existentes conservan los criterios activos y descartan esa propiedad obsoleta; no se reescribe ninguna corrida. Scheduling restaura y persiste sólo los campos vigentes de su configuración; no añade profundidad ni opciones avanzadas al contrato temporal.

Los históricos essential, comparative y deep siguen abriendo con sus datos técnicos y evidencia. `analysisDepthUi` y la lectura de JSON persistido siguen disponibles internamente. Abrir un histórico no ejecuta de nuevo el motor. Los tests conservan aprobación previa, errores terminales, IDs nuevos, retry, filtros, criterios personalizados, ventanas, reglas y lineage.

La revisión de Assignment se actualiza con los pesos actuales al abrirse; mover un slider actualiza la validación de la barra sin reemplazar el control que tiene foco.

## D. Medición del cambio a essential

Se compararon los seis objetivos, mismos CSV `sample_data/v3`, cuatro dimensiones y opciones de solver iguales en cada par. Custom usa pesos 0.4/0.3/0.2/0.1. Se repitió con presupuesto corto y con defaults normales: 10 s, límite determinista 0.12 y presupuesto global 90 s. **El cambio tiene efecto funcional y no implica equivalencia de planes.** No se modificó el algoritmo para ocultarlo.

| Objetivo | Essential / comparative: escenarios | Métricas seleccionadas con defaults |
|---|---:|---|
| Menos viajes | 1 / 5 | Iguales: 48 viajes |
| Costo mínimo | 1 / 5 | 57 / 48 viajes; costo 31,679,400 / 28,106,000 |
| Mayor flota propia | 1 / 5 | Iguales: 100% peso propio |
| CO₂ mínimo | 1 / 5 | 24,791.8 / 22,344.6 kg CO₂ |
| Balanceado | 5 / 5 | Iguales en esta muestra |
| Personalizado | 4 / 5 | Iguales en esta muestra |

Los doce planes son factibles y asignan las 30 órdenes / 519 unidades / 430,100 kg. Essential reduce las referencias de objetivos simples; el motor usa un conjunto de candidatos diferente y puede devolver un plan distinto. La muestra no garantiza equivalencia en otros datos. La comparación progresiva existente conserva su contrato y el resultado seleccionado histórico. Evidencia local: `rebrand-phase4-depth-defaults.json` y `rebrand-phase4-depth-measure.json` bajo `/workspace/dation-audit/`.

## E. Validación funcional

Suites: 349 Python, 37 Node, 82 Chromium, 7 E2E reales; CI añade 46 SQL sobre PostgreSQL 17. Total esperado: 521. El gate exige verde en el head exacto y después en main, sin fallos ni omisiones. Los siete nuevos casos Chromium ejercitan drafts legacy, payload essential, opciones inactivas, limpieza de Scheduling, apertura de los tres tipos históricos sin recalcular, pesos/review, filtros, teclado y footer a cinco anchos.

El E2E real usa API, worker, base y storage desechables, con creación, ejecución, aprobación, reemplazo e historial. La prueba browser comprueba el payload enviado sin seleccionar profundidad. No usa datos productivos para escrituras de prueba.

## F. QA visual y producción

Anchos: 1440, 1280, 1024, 768 y 390 px. Se verifican formularios base/custom, ventanas, reglas, opciones inactivas, revisión y filtros. Contraste compuesto WCAG AA: 4.5:1 normal y 3:1 grande, incluyendo valores nativos, placeholders y texto de opciones futuras. Los estados disabled conservan su semántica. Se comprueban foco, Escape, contexto cerrado, upstream visible, ausencia de overflow del documento y último control libre sobre la barra.

Capturas e informe local: `/workspace/dation-audit/rebrand-phase4-visual/`. La publicación se valida por Cloud Build y source SHA, hashes de template y 27 assets, acceso privado, readiness, dependencias y heartbeat del worker. La QA de producción sólo usa lecturas y preflight/preview de cálculo: bloquea escrituras persistentes y compara hashes de casos, corridas y comparativa antes/después. Evidencia final en el PR y `rebrand-phase4-production-final.json`.

## G. Riesgos y deuda

El cambio de cobertura de candidatos essential es el riesgo funcional medido en D; no presentarlo como un ajuste puramente visual. No hay migraciones de datos que revertir. Para rollback, revertir el merge y publicar ese commit por Cloud Build.

La migración dark completa de dashboard, charts y menús corresponde a Fase 5; accesibilidad extendida a Fase 6 y consolidación de hojas legacy a Fase 7. Se preservan las reglas compartidas necesarias para esas superficies hasta su migración. El entorno reutilizable debe fijar el commit publicado y conservar instalación, red y bindings privados actuales.

## H. Gate

**FASE 4 COMPLETA — LISTA PARA FASE 5** sólo después de suites verdes, integración y verificación productiva del commit exacto registradas en el PR. No iniciar Fase 5 automáticamente.
