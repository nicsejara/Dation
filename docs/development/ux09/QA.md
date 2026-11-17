# UX09 — Validación y evidencia

Baseline: `d2abe7f69e411fece0f44207fb720c2c682666da`, UX08 preservada. [Implementación y rollback](IMPLEMENTATION.md). [59 criterios](ACCEPTANCE_MATRIX.csv).

Este primer snapshot registra PASS locales; GATE06 (CI remota) y GATE08 (PR) se completan después de comprobar GitHub. No se declara CI_GREEN anticipadamente. El SHA validado y el run final se publican también en el único PR, para no hacer un commit autorreferencial con su propio hash.

## Evidencias reales

Chromium headless 153, renderer del repositorio, API/PostgreSQL/Storage y trabajadores locales de los fixtures existentes. Capturas originales sin retoques, con identidades y datos sintéticos. No se consultó ni modificó producción. [Índice y SHA-256](evidence/screenshots.json).

| Superficie | Escritorio 1536 | Móvil 390 |
|---|---|---|
| Core01 / footer | [Completo](evidence/core01-ready-1536.png) | [Completo](evidence/core01-ready-390.png) |
| Core02 / Owner + Sessions / footer | [Con datos](evidence/core02-validated-1536.png) | [Con datos](evidence/core02-validated-390.png) |
| Core03 / Owner / footer | [Completo](evidence/core03-ready-1536.png) | [Completo](evidence/core03-ready-390.png) |
| Sesiones vacías | [Cero real](evidence/data-sessions-empty-1536.png) | [Cero real](evidence/data-sessions-empty-390.png) |
| Sesiones compatibles | [Lista](evidence/data-sessions-available-1536.png) | [Lista](evidence/data-sessions-available-390.png) |
| FINALIZING vencida recuperable | [Intento real](evidence/data-sessions-frozen-recovery-1536.png) | [Intento real](evidence/data-sessions-frozen-recovery-390.png) |
| Estado del Case | [Cuatro hechos](evidence/case-header-1536.png) | [Cuatro hechos](evidence/case-header-390.png) |
| D1 | [Panel](evidence/graph-d1-1536.png) | [Panel](evidence/graph-d1-390.png) |
| D2 | [Panel bloqueado](evidence/graph-d2-1536.png) | [Panel bloqueado](evidence/graph-d2-390.png) |
| Conflicto 409 | [Sin truncar](evidence/footer-error-409-1536.png) | [Sin truncar](evidence/footer-error-409-390.png) |

Estados adicionales: [Core01 0/3](evidence/core01-zero-1536.png), [1/3](evidence/core01-partial-1536.png), [Core02 un candidato](evidence/core02-one-candidate-1536.png), [Case parcial](evidence/core03-partial-1536.png), [guardando](evidence/footer-saving-1536.png), [fallo 503](evidence/footer-error-503-390.png), [sesiones 403](evidence/data-sessions-error-403-390.png), [sesiones 503](evidence/data-sessions-error-503-1536.png), zoom 200% [footer](evidence/footer-zoom200.png) / [Graph](evidence/graph-zoom200.png). Los textos excepcionalmente largos del [stress fixture](evidence/graph-long-label-390.png) se etiquetan como tales; no son un estado inventado en el producto.

Antes, en main UX08: [Core01](evidence/before-core1-1536.png), [Core02](evidence/before-core2-1536.png), [Core03](evidence/before-core3-1536.png), [D1](evidence/before-graph-d1-1536.png), [D2](evidence/before-graph-open-1536.png).

## Geometría comprobada

[Baseline](evidence/geometry-baseline.json), [71 escenas después](evidence/geometry-after.json), [comparación extraída](evidence/comparison.json). Rectángulos en píxeles CSS del viewport; la coordenada Y puede variar por scroll. Capturas full-page y rectángulos se toman en la misma escena, sin recortes artificiales.

- Los tres footers normales pasan de 128 a **96 px** en 1536/1280, con una fila; Previous/anillo 44×44 y CTA >=44 px. Core02 mantiene ambos CTA en la misma fila desktop. Los errores largos crecen sin truncar.
- En 1536 Owner/Sessions miden 633,328 / 316,656 px y ambos 217,766 px de alto. En 1280, 462,656 / 231,328 px y ambos 277,766 px de alto. El cambio de altura es reflow real del contenido, no una altura rígida por viewport.
- Padding 18 px, radio 11 px, títulos 16 px, texto 12 px, iconos 48×48; selector Owner 40 px. Gap al footer **22 px**, también con lista expandida y errores.
- En 1536 los tracks Estado/Salida/cierre comienzan en X=1005/1221/1437 tanto D1 como D2; en 1280, X=749/965/1181. Tracks de datos 200 px, cajas útiles 183×40 y cierre 44×44. Los detalles largos pueden crecer verticalmente sin desplazar esos tracks.
- Estado del Case ocupa el 100% de su columna. Normal desktop 36 px; a 320/390 una etiqueta larga puede envolver y crecer a 48 px, preservando texto completo y ancho estable.
- Viewports **1536, 1280, 1024, 768, 390, 320**, zoom 200%; cero overflow horizontal en las escenas comprobadas. Auditoría de contraste del repositorio y nombres accesibles, teclado y foco conservados.

## Pruebas y reproducibilidad

[Resultados por test e intentos](evidence/focal-results.json): **71 pruebas únicas de navegador, último resultado PASS**. Incluye siete UX09, regresión UX08/UX07, Data Contract, Graph UX05, navegación UX06, Unified Journey, permisos del Case y seis smokes FAST. No se presenta la primera tanda integrada como verde: dio 69 PASS y un fallo de medición tras resize; se corrigió la barrera de render y se revalidó focalmente.

[Dos E2E reales](evidence/e2e-results.json): ambos PASS en primera ejecución, **85,651 s**, con creación, ejecución/aprobación local y navegación desktop/móvil. No habilitan motores productivos. Además, **34 subtests Node** (15 Graph + 19 navegación) y siete pruebas del clasificador PASS. Sintaxis JS/Python/CSS/JSON y `git diff --check` forman parte del gate final.

Desde `backend/tests/browser`, con las dependencias de navegador ya instaladas:

```sh
python -m unittest -v test_visual_precision_ux09 test_premium_refinement_ux08 test_data_contract_wizard test_decision_graph_ux05 test_journey_navigation_ux06 test_unified_decision_journey test_visual_refinement_ux07
```

Las pruebas de permisos `test_decision_case_wizard` T05–T08 y los seis smokes seleccionados por `scripts/ci/impact.py` se incluyen en el registro de tests. Comandos adicionales desde la raíz:

```sh
node backend/tests/test_graph_ux05.mjs
node backend/tests/test_journey_navigation_ux06.mjs
python -m unittest discover -s tests/operations -p test_rapid_impact.py -v
python backend/tests/e2e/run_suite.py --module test_workflow.WorkflowTests.test_browser_complete_workflow_at_mobile_width --module test_workflow.WorkflowTests.test_browser_creation_execution_approval_navigation_and_mobile_history
```

El runner E2E se ejecutó realmente desde `backend` (`python tests/e2e/run_suite.py ...`); el comando anterior es equivalente con la ruta absoluta del script. Los recursos de prueba son locales y se limpian mediante los fixtures existentes.

UX09 T01 comprueba geometría/creación/Graph; T02 disponibilidad, selección, permisos/error y CSV pendiente; T03 respuestas fuera de orden y desmontaje; T04 dirty/saving/error/conflicto/recarga; T05 labels largos/toggle/frozen guard; T06 recuperación duradera del mismo Case; T07 readiness compartida, fallo de GET/restauración y reintento sin finalizar el recurso anterior.

## Hallazgos corregidos y límites

- El primer ensayo reveló un selector CSS compartido mal delimitado y una fila heredada en Sessions. Se restauraron las reglas de Owner originales y se fijó el layout de la nueva tarjeta; T01 y regresión Owner pasaron.
- Se coordinó la selección asíncrona con la promesa de readiness existente. El test mantiene la lectura pendiente y navega a Core03: no hay finalize prematuro. Fallos de lectura y restauración producen cero Cases; el reintento correcto finaliza una sola vez contra la sesión seleccionada.
- El test de guardado debe respetar que guardar un Case existente vuelve al Graph. Reabre después el Case para comprobar el estado limpio, manteniendo las aserciones de guardado.
- La medición inicial después de resize podía leer el track anterior. Se espera `document.fonts.ready` y dos animation frames, sin sleeps, retries ni relajación de igualdad de anchos.
- FINALIZING vencida es recuperable por contrato, no una sesión expirada ordinaria; se confirmó contra el servicio y la recuperación real aislada. No se alteró SQL.
- La disponibilidad no incluye conteo de archivos ni garantía transaccional de permanencia. Un recurso elegido se vuelve a leer y el servidor revalida al restaurarlo. [Invariantes de código](evidence/source-invariants.json): proyección de estados, toolbar, command center, nodos y estilos de círculos/conectores sin cambios.

## CI e integración

El clasificador vigente determina **R2**, `requires_full=false`: se exige impact + FAST + required-gate. No se alteró el clasificador ni los workflows y no se ejecuta FULL adicional sin exigencia. El registro remoto terminal se añadirá tras la primera ejecución real del PR. No merge, publicación de imagen, despliegue ni promoción.
