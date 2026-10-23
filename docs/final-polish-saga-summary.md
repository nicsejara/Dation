# Dation — Final UX/UI Polish Saga

Estado: en implementación. Baseline real de main/origin/main: `ff8134c6a19fc98c7e6a81029d830b4ab5285560`. Rama: `ux-ui/final-polish-saga`.

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
