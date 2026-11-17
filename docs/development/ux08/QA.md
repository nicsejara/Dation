# UX08 — Evidencia y aceptación

Base: `d813c4841a87a30634aeaa9127ae4aea5aeb1933`. El SHA candidato, PR y resultado terminal de CI se registran en la descripción y checks del PR. Se conserva ese registro externo para no provocar otra ejecución sólo por copiar su contador a un commit nuevo.

La [matriz CSV](ACCEPTANCE_MATRIX.csv) contiene los 41 criterios y evidencia por ID. Es el snapshot local previo al push: 40 PASS y T04 pendiente únicamente del gate remoto. La matriz final del PR completa T04 con los checks reales del SHA. No se declara `CI_GREEN` antes de su resultado terminal.

## Mediciones y capturas reales

Capturas sin retoques del renderer real del repositorio, con API/PostgreSQL/Storage aislados del entorno de pruebas existente; no son mockups ni capturas de producción. La identidad `Synthetic`/`Miembro del equipo`, modelos, Cases, CSV y estados provienen de esos fixtures. Los documentos adjuntos del propietario son referencia de diseño; no se copian sus datos de ejemplo.

| Superficie | Escritorio | Móvil | Comprobación |
|---|---|---|---|
| Home | [1536](evidence/home-1536.png) | [390](evidence/home-390.png) | Saludo dinámico, claim activo, CTA y tres conceptos |
| DDA Logística | [1536](evidence/landing-1536.png) | [390](evidence/landing-390.png) | Misma escala y baseline de contenido |
| Core01 / footer | [1536](evidence/core1-1536.png) | [390](evidence/core1-390.png) | Estado, separación de costos, Previous/anillo intactos |
| Core02 / Data Owner / footer | [1536](evidence/core2-1536.png) | [390](evidence/core2-390.png) | Tarjeta Owner, dos CTA horizontales desktop, conteo real |
| Campos y reglas | [1536](evidence/contract-fields-1536.png) | [390](evidence/contract-fields-390.png) | Tres columnas, condiciones completas, sin JSON técnico |
| Core03 / Decision Owner / footer | [1536](evidence/core3-1536.png) | [390](evidence/core3-390.png) | Misma tarjeta, progreso único, resumen funcional conservado |
| Case / Graph cerrado | [1536](evidence/graph-closed-1536.png) | [390](evidence/graph-closed-390.png) | Cuatro hechos, cinco acciones, cierre segregado |
| Panel D1 | [1536](evidence/graph-d1-1536.png) | [390](evidence/graph-d1-390.png) | Jerarquía, estado + detalle, Owner y acción real |
| Panel D2 | [1536](evidence/graph-open-1536.png) | [390](evidence/graph-open-390.png) | Bloqueo auténtico, sin acciones inventadas ni checks falsos |

Antes: [Home](evidence/before-home-1536.png), [Landing](evidence/before-landing-1536.png), [medidas baseline](evidence/hero-baseline.json). Los screenshots de UX07 integrados en `main` permiten comparar además Core/Graph.

- [Heroes después](evidence/hero-metrics.json): exteriores 480 px en 1536/1280 y 560 px en 1024/768, iguales al baseline; misma caja de ilustración y mismas franjas inferiores desktop/tablet. CTA de 44 px en 1536/1280/1024 y reflow equivalente cuando el texto requiere más altura. A 390/320, el apilado de iconos/copy conserva texto completo y adapta la altura natural, conforme E.1.7. La franja Home móvil gana 39 px frente al baseline por ese reflow; no se fuerza altura fija ni se reduce tipografía para esconder contenido. El claim preservado es el activo en `platform/home.mjs`, no el texto inactivo de la plantilla inicial.
- [Core](evidence/core-metrics.json): tres headers de 176 px y tres footers de 128 px en 1536 y 1280; Previous y anillos de 44 × 44 px. Badges normales de 180 × 36 px; a 320 se contiene el ancho disponible. Se prueban labels/estados con geometría del header estable; el texto de errores largos puede crecer naturalmente.
- [Owners](evidence/owner-metrics.json): Data/Decision Owner de 176 px, mismo ancho/rail, selectores de 40 px y misma tipografía en desktop. Edición existente mantiene dos responsables y permisos propios.
- [Tabla](evidence/table-metrics.json): filas desktop de 119 px en el contrato real de la fixture, iguales al contenido máximo; alturas naturales de 43–119 px en móvil, con scroll del contenedor y encabezado accesible. Sin elipsis o recorte de campos.
- [Graph](evidence/graph-metrics.json): círculos iguales, distancias simétricas, conectores sin glifos; código del grafo, lifecycle/toggle, acciones y CSS de su geometría idénticos al baseline.
- [Accesibilidad/reflow](evidence/geometry.json): viewports 1536×900, 1280×800, 1024×768, 768×900, 390×844 y 320×740, teclado, foco y zoom 200 %. Sin overflow de página ni fallos del auditor de contraste en las escenas verificadas. Las tablas pueden desplazar su contenedor local.

## Pruebas focales

[Resultados, intentos y pruebas únicas](evidence/focal-results.json).

- 70 casos únicos de navegador: UX08, HomeHero, DataContractWizard, Graph UX05, Journey UX06, Unified Journey UX04, regresión visual UX07, cuatro contratos de permisos/elegibilidad/edición de Decision Owner y los seis recorridos seleccionados por FAST.
- Node: 15 contratos de estado/acciones del Graph, 19 de identidad/navegación UX06 y 5 del catálogo. En este entorno se ejecutan directamente los archivos con `node`, que registra sus subtests.
- Clasificador: 7 pruebas PASS. Diff clasificado **R2**, `requires_full=false`; no se modifica el clasificador, mapa o workflows.
- Static check del repositorio sobre archivos modificados y `git diff --check`.
- Dos E2E focales con backend, persistencia y ejecución/aprobación local reales: `test_browser_creation_execution_approval_navigation_and_mobile_history` y `test_browser_complete_workflow_at_mobile_width`. No se usan recursos productivos.

Comando de navegador (desde `backend/tests/browser`, usando Python/Chromium de las dependencias existentes):

```sh
python -m unittest -v test_premium_refinement_ux08 test_home_hero test_data_contract_wizard test_decision_graph_ux05 test_journey_navigation_ux06 test_unified_decision_journey test_visual_refinement_ux07
```

Los cuatro permisos de `test_decision_case_wizard` T05–T08 y los seis smokes de `scripts/ci/impact.py` se ejecutaron además focalmente. El E2E se ejecutó mediante `tests/e2e/run_suite.py --module ...`, sin repetir la suite general.

## Hallazgos corregidos y límites de evidencia

- Se corrigió el conflicto de especificidad del header Core que comprimía el título al introducir el badge ancho en móvil.
- Se verificó que reducir los footers a 108 px hacía que Core02 creciera hasta 124 px en 1280. Se dejó una base compartida de 128 px, menor a los 164 px anteriores, sin comprimir contenido ni ocultar notas.
- El nuevo panel había omitido `state.detail` cuando existía una acción primaria. La regresión real de presentación se corrigió: estado y detalle se muestran una sola vez en la meta; se conserva `Resultado desactualizado`, fallos técnicos, aprobación y bloqueos auténticos. Graph T08 volvió a PASS sin relajar su assertion.
- La primera tanda concurrente registró timeouts previos al montaje de Core y al acceso frío al dashboard móvil. Los casos aislados pasaron sin cambios de producto, waits ni assertions: contrato/descarga y E2E móvil (54,078 s). No hay causa raíz demostrada para esos timeouts; se conservan los intentos fallidos en el registro, en lugar de atribuirlos a una causa no verificada. El E2E desktop pasó en su primera ejecución.
- Las anteriores lecturas del JSON en pantalla se reemplazaron por pruebas del callback real del renderer con el contrato congelado, incluida metadata desconocida. Persisten los checks de bytes CSV, headers, hashes/versiones, stale requests, XSS literal y contratos parciales/error.

## Gates y cierre

CI requerida: `impact` + FAST (clasificador, static y seis smokes R2) + `required-gate`. FULL sólo si lo determina el clasificador; este diff no lo exige. El resultado terminal y el SHA validado deben consultarse en los checks y la matriz final del único PR.

No hay cambios de backend, SQL, Supabase, motores, permisos, persistencia, navegación, dependencias, workflows o infraestructura. Sin merge, publicación de imagen, despliegue ni cambio de tráfico. [Activación posterior y rollback](IMPLEMENTATION.md#activación-posterior-y-rollback).
