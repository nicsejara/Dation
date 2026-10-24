# Unified Hero Illustrations and Icon Refinement

Estado: **Completed — U1–U11 PASS**. Baseline real: `eb395621c4c44843082e3ad4bab9c6247f10bfcb`.
Branch: `ux-ui/unified-hero-illustrations-and-icon-refinement`.

Se leyó completo el master definitivo. El entorno recuperado tenía una copia local anterior; `main` se sincronizó por fast-forward con `origin/main`, sin descartar cambios. La branch de esta saga no existía. La colección generada en el intento anterior se recuperó íntegra y se reutilizó. No se hizo una auditoría transversal ni una nueva exploración estética.

## Implementación

Home y DDA Logística usan el componente visual opt-in `d-product-hero`: misma fuente de tokens para altura, padding y radio; copy arriba a la izquierda; arte contenido en una columna independiente; panel inferior integrado. No se altera el shell ni otros heroes mediante estos estilos.

| Viewport | Ancho Home / Logística | Alto Home / Logística | Padding | Radio |
| --- | --- | --- | --- | --- |
| 1440×900 | 1144 / 1144 | 480 / 480 | 24 | 16 |
| 1280×800 | 984 / 984 | 480 / 480 | 24 | 16 |
| 1024×768 | 742 / 742 | 560 / 560 | 24 | 16 |
| 768×1024 | 660 / 660 | 560 / 560 | 24 | 16 |

El arranque del copy queda a 25 px de los bordes superior e izquierdo, incluyendo borde; antes el Home comenzaba a 53,78 px del borde superior a 1440. En teléfono el padding compartido es 20 px y la altura depende del contenido, sin recorte. El mínimo desktop permite reflow de identidades extensas, sin imponer una altura que corte texto.

Data Pack / Decision Case / Decision Run conservan su copy y semántica de lista. Usan el mismo panel que Entrada / Inteligencia / Decisión: superficie oscura, borde, radio, divisores y padding compartidos; títulos 600 y descripción debajo. A 1440 y 1280 ambos paneles miden 77 px. En mobile se apilan sus elementos.

Los dos CTA del Home siguen iguales entre sí, de 228×40 px cuando hay espacio, adaptándose al ancho disponible. La revisión visual detectó texto recortado en los CTA de Logística a 320 px: se habilita su reflow manteniendo alto, tipografía y navegación. El test comprueba los límites de la tinta del texto dentro de los botones.

## Colección final

Las cuatro escenas provienen de **una misma hoja generada simultáneamente**, con perspectiva, materiales navy/charcoal, iluminación, bordes y acentos teal/cyan comunes. Se exportaron sus cuatro cuadrantes a WebP con transparencia real, calidad 88 y dimensiones 724×543. No se mezclaron imágenes de estilos distintos.

| Asset en `backend/app/static/assets/` | Bytes | Significado |
| --- | --- | --- |
| `home-isometric.webp` | 72668 | Hub y módulos de datos, evidencia y gobernanza; abstracto, sin logística |
| `logistics-isometric.webp` | 100884 | Warehouses, carga, camión y red de orígenes/destinos |
| `assignment-isometric.webp` | 86006 | Carga → hub de asignación → recursos y capacidad |
| `scheduling-isometric.webp` | 76142 | Viajes, reloj, waypoints y ventanas temporales |

Total: **335700 bytes**. Los tres visuales operativos activos pasan de 5473219 a 263032 bytes. El Home pasa de SVG a raster para pertenecer a la colección. Los archivos anteriores se conservan para compatibilidad con pestañas existentes; las cuatro superficies actuales usan los nuevos exports.

El arte decorativo reserva su geometría y no tapa texto ni controles. Home/Overview lo ocultan hasta 700 px; los dashboards hasta 900 px, donde el contenido ocupa una columna. La geometría exterior de D1 y D2 es idéntica al baseline en los seis tamaños. No se agrega movimiento.

Los SVG `dda-logistics.svg` y `dda-production.svg` se simplifican a siluetas de trazo consistente, con fondos transparentes: camión y fábrica. Logística reutiliza exactamente el mismo asset en card y sidebar. Producción se alinea a 28 px con los demás iconos del catálogo; Logística usa 48 px en la card destacada. El feedback del sidebar pertenece a la fila y su foco visible, manteniendo el área del icono transparente en default, hover, pressed, active y focus.

## Acceptance

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| U1 — Top alignment | PASS | Copy anclado al padding superior/izquierdo; orden y saludo conservados |
| U2 — Structural parity | PASS | Geometría exterior, padding y radio iguales en los cuatro tamaños desktop/tablet |
| U3 — Bottom panel | PASS | Patrón compartido, borde/fondo/radio/divisores y contenido completo |
| U4 — Unified family | PASS | Cuatro exports de una misma creación; revisión visual conjunta |
| U5 — Logistics art | PASS | Ecosistema operacional isométrico, sin fotografía |
| U6 — Assignment art | PASS | Matching y distribución entre carga/recursos; sin secuencia temporal |
| U7 — Scheduling art | PASS | Reloj, ventanas y secuencia; sin hub de matching |
| U8 — DDA icons | PASS | Camión y fábrica minimalistas, transparentes y consistentes |
| U9 — Sidebar hover | PASS | Cinco estados × seis viewports; contenedor sin fondo/borde/sombra; esquinas raster transparentes |
| U10 — Functional preservation | PASS | Contratos, fuentes, DOM preservado y recorridos funcionales verificados |
| U11 — Responsive | PASS | Seis viewports sin overflow; CTA sin texto recortado; teclado y zoom 200% |

## QA

- **15 browser PASS**, ejecución final conjunta: seis Home; tres de esta saga; dos Final Polish afectados; tres de catálogo; uno de controles actuales de dashboards. Incluye saludo por timezone/identidad, teclado/historia, navegación, fallo/carga lenta de imagen, zoom 200%, igualdad geométrica, panel, sidebar y catálogo/fallback.
- El test vigente de dashboards verifica exportaciones CSV/JSON, detalles/Escape/restauración del foco, nueva corrida, aprobación D1/D2 y conservación exacta del escenario seleccionado. El CTA de Overview sigue abriendo Decision Center filtrado por Logística; iniciar un Case prepara Datos sin ejecutar un Run.
- **34 Python PASS**: 29 contratos frontend y cinco Home V2. **Suite Node de catálogo PASS**. Sintaxis de ambos módulos JS modificados y de los tests Python: PASS. `git diff --check`: PASS.
- **24 observaciones visuales finales**: Home, Overview, D1 y D2 en 1440×900, 1280×800, 1024×768, 768×1024, 375×812 y 320×640. Cero overflow de página y cero fallos de contraste muestreado. Revisión de capturas de heroes y estados de iconos.
- **Taste CSS añadido: 0 FAIL / 0 WARN**. Probe y `judgeApp` de la Skill ejecutados dentro del harness autenticado de fixtures: 24 observaciones, **0 FAIL**. Se conservan datos crudos. El adaptador mide el h1 visible, excluye texto sin caja visible y colores de rectángulos de área cero o `fill-opacity=0`; no cambia reglas, Skills ni producto para corregir falsos positivos de medición.
- Advertencias revisadas: bordes/metadata/radios pertenecen a tokens y roles existentes; el tamaño de títulos y el contenido bajo el fold conservan la dirección aprobada y el alto compartido pedido. Los huecos y escalas de secciones ajenas al hero no se rediseñan para satisfacer heurísticas. No se añade blur, sombra decorativa ni nuevos colores de gráficos.

Cuatro tests históricos de `NavigationTests` fallan **idénticamente en el baseline `eb39562` y en la saga**: `test_overview_single_case_map_opens_directly_and_new_decision_clears_active_context`, `test_scheduling_uses_shared_menus_drawer_and_exports_without_format_changes`, `test_d1_v2_final_approval_updates_hero_and_continues_to_scheduling` y `test_d2_v21_ai_retry_approval_and_approved_state`. Esperan el selector anterior de Case, tres acciones antiguas del menú, `data-approve-final` o la explicación inicialmente abierta. Se ejecutaron en un worktree separado del baseline; no se debilitan esos tests ni se cambia funcionalidad para satisfacerlos. Los recorridos vigentes están cubiertos por la tanda final verde. No se declara verde la suite histórica monolítica.

## Integridad y revisión visual

Los hashes del baseline confirman que no cambian backend, worker, motores, API, SQL, persistencia, tenancy, permisos, routing ni infraestructura. Todos los módulos JS salvo Home y Assignment permanecen idénticos; Assignment cambia únicamente URL/dimensiones del asset. El saludo y todos los handlers de Home son idénticos. El texto de los cuatro heroes y el DOM de Quick Access, catálogo y sidebar coinciden con el baseline en los seis tamaños. Los datos usados en las capturas son fixtures sintéticas, sin escrituras productivas.

Se aplicaron `design-taste-frontend`, `ui-ux-pro-max` y `emil-design-eng`. Se mantuvo Dation Precision / `data-terminal` y su dirección previa (seed 2039572090); no hubo nuevo draw, según la excepción de componente con dirección existente. Firma: la red abstracta del producto se concreta progresivamente en red logística, asignación y secuencia.

Crítica acotada de app: el headline del Home explica el producto; Logística presenta sus despachos; D1 prioriza el resultado de distribución y D2 las fechas/SLA. Los heroes comparten bordes; el arte ocupa su propia zona. La paleta de marca y los estados existentes se conservan. Cifras, faltantes, totales y leyendas no se reinterpretan; las exportaciones conservan evidencia. El rail móvil existente permanece y el contenido refluye sin recorte. La ilustración abstracta del Home sigue siendo la dirección definitiva. Validación de render en Chromium; no equivale a QA de todos los navegadores ni a medir LCP productivo.

Artefactos locales, fuera del repositorio: `/workspace/work/unified-hero/`. Incluyen baseline y hashes, master PNG recuperado, metadatos de exports, before/final, capturas de estados, probes/findings, logs de tests y comparación de fallos históricos.

## Archivos y commits

Archivos de aplicación: los seis assets indicados; `tokens.css`, `platform-components.css`, `platform-home.css`, `home-dda.css`, `platform-shell.css`, `assignment-dashboard-decision.css`, `scheduling-dashboard-v21.css`; `platform/home.mjs`, `assignment/assignment-summary.mjs`; `templates/app.html`. Tests: `test_home_hero.py`, `test_final_polish.py`, `test_unified_heroes.py`. Este documento cierra la saga.

| Fase | Commit | Contenido |
| --- | --- | --- |
| Estructura | `47584ee` | Refine home hero structure and bottom panel |
| Colección | `df4b7a2` | Introduce unified isometric hero illustration family |
| Iconos y cierre | Este commit | Simplify DDA icons and fix sidebar logo hover; responsive y QA |

La publicación autorizada exige árbol limpio, U1–U11 PASS, ausencia de regresiones nuevas/STOP y fast-forward seguro después del fetch final. No se hace squash, force, rebase ni despliegue manual. La integración y el push se verifican con Git; la observación del pipeline se informa separadamente y no implica verificar el despliegue.
