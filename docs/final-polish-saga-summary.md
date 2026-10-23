# Dation — Final UX/UI Polish Saga

Estado: C1–C9 implementados y validados. Baseline real de main/origin/main: `ff8134c6a19fc98c7e6a81029d830b4ab5285560`. Rama: `ux-ui/final-polish-saga`.

El master definitivo se leyó completo antes de editar. Se conservan Dation Precision, navegación, dominio y contratos; no se realiza una auditoría transversal nueva. Baseline: 813 archivos con SHA-256 y 14 capturas de Overview, Datos, Config D1/D2, Dashboard D1/D2 y ejecución a 1440×900 y 375×812. Evidencia local: `/workspace/work/final-polish/`.

## Fases

1. Shared workflow chrome: metadata de paso/decisión separada y sin ceros; command bars con estado canónico, geometría medida, safe-area y viewport de scroll separado. El layout reserva espacio para que los controles no queden detrás de la barra y expone el foco sin animar. ResizeObserver, focus y visualViewport se disponen con el scope existente. Z-index 35, por debajo de menús y overlays. No cambia readiness, Apply, defaults, revisión ni ejecución. La prueba de foco ahora espera un campo visible y comprueba que realmente tenga foco antes de evaluar sus nueve puntos; antes podía evaluar una vista todavía oculta.

## Invariantes

DDA → Case → Decision → Run; Data Pack inmutable; atributos/Data Owner aplicados conjuntamente, cuatro requisitos independientes; Decision Owner/authority actuales; aprobación humana por Run e invalidación downstream en admisión; idempotencia, historia y fingerprints intactos. Assignment no temporal; Scheduling consume Assignment aprobada sin reasignar; D3 permanece disabled. Backend, motores, API, SQL, persistencia, tenancy, roles, permisos, exportación e infraestructura quedan fuera de las modificaciones.

Phase 1 QA: C4/C5 pasan en seis viewports; nueve puntos de cada control enfocado quedan visibles. Ocho browser distintos verificados (cuatro de preparación antes de CSV, dos de aceptación y dos de foco/reflow), seis unitarios y 18 observaciones visuales sin overflow ni fallos de contraste muestreado. Los viewports bajos compactan la barra y permiten desplazar los headers; no se reintroduce una animación de entrada.

2. Overview: titular con énfasis teal, arte 3D local decorativo y bloque compacto Entrada / Inteligencia / Decisión; CTA, permisos y rutas intactos. El aviso demo usa exclusivamente `is_sample === true` de datasets del recurso actual, después de hidratar su contexto, comprobando identidad Case/Run y datasets. No infiere demo por nombres o categorías. Copy contextual compacto; no se oculta mediante CSS. Arte generado para la dirección aprobada, integrado como PNG local sin hotlinks ni UI incrustada.

Phase 2 QA: C1/C2 pasan: hero en seis viewports, procedencia real/sample en Datos, Map, Config y Dashboard; tres tests Node de procedencia, doce observaciones visuales sin overflow. La primera prueba C2 esperaba un h1 oculto de ejecución; se corrigió el selector a h1 visible. Una prueba histórica de Navigation sobre un botón Map sin Cases falla en su aserción disabled; se compara contra el baseline antes de clasificarla.

3. Dation IA: launcher etiquetado, flotante fuera de la toolbar, mismo callback de conversación. Panel compartido D1/D2 con contexto del Run y workspace, drawer desktop / hoja mobile, safe-area y adaptación al teclado. `Analizando…` deriva de la petición existente, se limpia al disponer el scope. Escape retorna al launcher; foco atrapado en la hoja mobile. Menús/detalles ocultan temporalmente el launcher y los controles enfocados ajustan su posición si colisionan. Sin cambios en endpoints, historial, retry/turn_id ni autoridad del asistente.

Phase 3 QA: C3 pasa en ambos dashboards y seis resoluciones, busy y retorno de foco; chat retry/history, navegación durante respuesta y limpieza/listener único pasan; export JSON conserva el resultado persistido. Cuatro capturas desktop/mobile revisadas. La prueba histórica Map falla idénticamente ejecutada contra el árbol baseline `ff8134c` (evidencia baseline-navigation.log); se conserva como limitación previa, sin cambiar su lógica.

4. Decision Intelligence: shell compartido con dos capacidades equivalentes, Insight IA / Análisis avanzado. Cada selección abre su evidencia full-width inmediatamente debajo; no modal ni mini acordeón. Cache, freshness, retry, generación explícita, copia y chat siguen en sus módulos existentes. El CTA de Insight abre el mismo asistente. Se preservan lazy rendering, destinos de plan y claves per-Run de sessionStorage. Navegación al plan instantánea, sin smooth al usar teclado. Estados inviables de D2 mantienen oculta esta evidencia como antes.

Phase 4 QA: C7 pasa en D1/D2 y seis resoluciones: cache sin inferencia nueva, selección/cierre, retorno de foco, chat único y ancho completo. Los tres tests de Foundation pasan, incluida persistencia aislada por Run, lazy init y cleanup de acciones encoladas; sólo se adaptan las expectativas del antiguo label Mostrar/Ocultar al nuevo nombre estable. Doce capturas de cards/Insight/avanzado revisadas. review-animations aprobó el diff estático: expansión instantánea, color/borde 140ms, reduced-motion y tokens definidos.

5. Presentación: los KPIs base D1/D2 comparten background, elevación y jerarquía tipográfica; se elimina el énfasis objetivo/primer KPI sin cambiar su dato o semántica. Se conservan advertencias y selección real de escenarios. Heroes con PNG locales distintos: Assignment warehouse/carga/flota; Scheduling ruta/tiempo/secuencia. Arte decorativo integrado detrás del contenido, oculto en mobile, sin hotlinks; trazabilidad sobre superficie legible.

Phase 5 QA: C6/C9 pasan en ambos dashboards y seis tamaños; resultados persistidos y exportación idénticos. Doce observaciones visuales sin overflow, errores JS ni fallos de contraste muestreado. Se corrigió la diferencia subpíxel entre fuentes dependientes de cqi a un tamaño compartido; los separadores entre filas responsive siguen teniendo su geometría real, sin simular selección.

6. Decision Engine Flow: renderer compartido de cuatro nodos, labels de stages reales y actualización estable durante polling. `validating` → Datos; `constructing` / `optimizing:*` → Motor; `summarizing` → Evidencia; `completed` → todos completos / Decisión lista. Admisión, recovery, cola y running sin stage no acreditan etapas completadas. Sin porcentajes, barras ficticias ni demoras. Pulso sólo de opacidad en nodo activo, estático con reduced-motion. Se conserva polling/reload/error; el adapter legacy usa la misma presentación y mantiene su export pendingMarkup.

Phase 6 QA: C8 pasa; test Node del mapping y browser de todos los stages/reduced-motion; polling real de ambos dashboards hasta éxito/error pasa después de adaptar el selector visual de barra a flujo. Seis capturas responsive sin overflow ni errores JS. review-animations: Approve, sin hallazgos nuevos. Un test histórico de contexto espera el primer summary del root y está pendiente de contraste baseline; la ejecución y sus contratos no se modifican.

7. Estabilización y QA: normalización mobile de los valores KPI; check del flujo dibujado con CSS; encabezado del chat desplazable en viewport bajo para que no tape Enviar al 400%. El parser de contraste de QA ahora entiende `color(srgb … / alpha)` y compone su alpha; no descarta muestras. Las únicas excepciones del lint de CSS corresponden al scrim neutro sobre las imágenes locales (permitido por la Skill), documentadas en las dos reglas.

## Aceptación

| Cambio | Estado | Evidencia |
| --- | --- | --- |
| C1 | PASS | Hero, arte local, proceso y CTA intactos; seis resoluciones |
| C2 | PASS | Procedencia estricta y correlación Case/Run; real/sample y caché ajena |
| C3 | PASS | Launcher fuera de toolbar, contexto, busy, chat existente, foco y sheet |
| C4 | PASS | Paso y decisión independientes, sin ceros iniciales |
| C5 | PASS | Command bars canónicas, foco visible y zona reservada |
| C6 | PASS | KPIs estáticos equivalentes; métricas y advertencias conservadas |
| C7 | PASS | Dos capacidades, evidencia full-width, cache y lazy/per-Run intactos |
| C8 | PASS | Stages reales, sin porcentaje, polling/éxito/error y reduced-motion |
| C9 | PASS | Arte distinto D1/D2, narrativa/approval/actions legibles |

## QA final y limitaciones

- Python: 383/383 PASS (`final-python-accepted.log`). Cuatro aserciones estáticas de la presentación anterior se adaptaron al hero, componente extraído de launcher y flujo compartido; contratos funcionales siguen cubiertos. La primera ejecución sin acceso loopback se interrumpió y se repitió con la red del sandbox de pruebas habilitada.
- Node: 20 archivos de tests PASS, incluidos procedencia y mapping nuevos (`final-node.log`). Sintaxis de los 18 módulos de aplicación modificados comprobada con Node.
- Browser principal: 41 casos distintos; 40 PASS en la corrida conjunta y un fallo de bootstrap transitorio antes de montar la app. Ese caso de foco se repitió aislado y pasó (`final-keyboard.log`). Los ocho nuevos casos C1–C9 pasan; stress específico adicional PASS, así como retry/history de chat, descarte al navegar, limpieza de listeners, menús, drawer y foco. No se presenta el primer log como una suite completamente verde.
- E2E: 11/11 PASS, API/worker/PostgreSQL desechables: personas distintas, permisos/tenancy, atributos/Data Owner, aprobación, múltiples Runs, invalidación downstream y conservación de evidencia (`final-e2e.log`). Ningún acceso mutante a producción.
- Responsive: 42 capturas finales, siete superficies × 1440×900, 1280×800, 1024×768, 768×1024, 375×812 y 320×640. Las 42 muestras de contraste pasan y no hay overflow ni errores JS (`accepted/`). Se suman capturas de Insight/avanzado/chat y datos extremos.
- Teclado/zoom: focus, Escape, Tab y retorno al origen PASS. Reflow al 200% y 400% PASS (`final-zoom-fixed.log`); el problema real de Enviar detrás del header sticky se corrigió, sin animar el cambio. Viewports bajos y barras se verificaron también por sus pruebas específicas.
- Motion: review-animations Approve en fases 4, 6 y estabilización; pulse sólo de opacidad, sin geometría animada ni demoras, alternativa estática con reduced-motion. No se reivindica prueba en un teléfono físico.
- Taste: inspector sin FAIL en las 42 observaciones; WARN de densidad/metadata, bordes/radios y composición heredados no reabren la dirección cerrada. Headline editorial responde al master; estados SLA conservan colores semánticos, y los iconos de Config pertenecen a elecciones reales. Los huecos de pares de evidencia y secciones bajo el fold mantienen la composición ya aprobada. Lint del CSS añadido en modo app: 0 FAIL y 2 WARN por sombras del panel/launcher, overlays explícitos requeridos. Los scrims son exclusivamente de legibilidad sobre arte real; no una nueva paleta.
- Limitaciones previas comprobadas contra `ff8134c`: test Navigation de Map sin Cases espera disabled; test Saga4 de contexto espera el primer summary genérico del root. Ambos fallan igual en el baseline; no se modificó su lógica ni se declara la suite monolítica Navigation en PASS.
- Preservación: los 120 archivos protegidos conservan su SHA-256. Cambios limitados a presentación frontend, pruebas y este documento; sin backend, motor, SQL, API, persistencia ni infraestructura.

## break-ui

Invocación focalizada con fix autorizado por el master; no auditoría nueva. Toggle exclusivamente de fixtures browser (`ux-upgrade-stress-toggle.js`), nunca importado por el producto. Fixture durable nueva: `tests/browser/fixtures/final-polish-stress.json`.

| Valor dinámico | Fuente / límite | Caso probado |
| --- | --- | --- |
| Label/description del Case, archivos | metadata actual; label 120, descripción 1000, filename sin límite UI | nombres largos plausibles, 1000 caracteres, filenames regionales |
| Workspace/actor/identificadores | contexto actual; nombre/email sin límite en el renderer | nombres con diacríticos, multilingües, cortos y email largo; IDs actuales |
| Valores/fechas de ambos heroes y KPIs | métricas persistidas del Run; sin límite de ancho UI | cero/uno, importe 123456789012.9, 1284 días, signos y decimales de fixtures |
| Insight: resumen, drivers, caveats | interpretación existente; texto/listas sin límite UI | 2000 caracteres, email largo y texto literal con markup escapado |
| Conversación / pregunta | historial existente; pregunta maxlength 2000 | historial largo, compositor al límite, busy/error/retry y cierre |
| Capacidades y flujo | labels fijos / stages del worker | pendientes, completed, error y stage desconocido neutral |
| Colecciones existentes | API con paginación; preview limitado por su módulo | Demo/Worst/Empty/One, 25 filas de 1284 miembros, planes y tablas con scroll |

El único break nuevo verificable fue el foco de Enviar al 400%; causa: header sticky en un panel de altura insuficiente; solución: header en el flujo del scroll bajo 540px. Repetición PASS. Los importes no se truncan; las preguntas largas permanecen editables y la evidencia se escapa. No hubo decisiones de diseño pendientes. RTL no se anuncia como capability del producto; no se implementó internacionalización nueva. No se probaron 1000 filas simultáneas donde la API ya pagina o el preview limita la cantidad.

## Integración autorizada

Fases 1–6: `656d3b4`, `e19e9a9`, `5498449`, `8e202bc`, `31ff3fc`, `628a659`. Fase 7: este commit. Sin STOP funcional. El gate requiere árbol limpio y comprobar otra vez origin/main antes de fast-forward; conservar los siete commits y publicar por el pipeline existente, sin cambios de infraestructura ni despliegue manual. El resultado exacto del push y la observación del pipeline se informan al finalizar, fuera del árbol ya validado.
