# D1 Assignment · Dashboard V2

## Fase 0: auditoría previa

Base: `main@b1c2701c05f1174f8b7b42210bd00c156e656a08`. La nueva solicitud se aplica al dashboard `assignment_v1`; las rutas, la configuración, el solver y Scheduling conservan sus contratos.

| Componente | Estado encontrado | Tratamiento |
|---|---|---|
| `dashboard.mjs` / shell | Hero, evidencia completa, validación, comparativo e IA siempre desplegados | Reordenar D1 y separar la vista visual del `analysis_depth` persistido |
| Selectores | Métricas canónicas, objetivos, recursos, órdenes, advertencias y deltas | Reutilizar y extender con contexto, cuatro KPI esenciales, insights, tabla, participación, preview y corredores |
| `assignment-summary.mjs` | Título operativo, ponderaciones y costo medio por viaje como KPI | Hero ejecutivo y componentes esenciales; costo total pasa a KPI y el promedio queda en Advanced |
| `assignment-evidence.mjs` | Viajes, vehículos, órdenes y detalle contextual con Escape | Conservar dentro de Advanced, sin perder cargas, productos, unidades ni proveedores |
| Comparador / resumen comparativo | Cuatro métricas, deltas semánticos, misma distribución y no factible | Reutilizar; agregar costo total y CO₂, mantener el costo medio en detalle |
| `comparative-upgrade.mjs` | GET restaura; POST explícito encola; polling con cancelación; original reutilizable | Conservar el endpoint y la inmutabilidad de selected; publicar evidencia a los módulos de presentación |
| `assignment-validation.mjs` | Advertencias reales y un estado vacío | Mantener al final; concentración de viajes es información para D2, no una advertencia |
| `explanation.mjs` | Resumen en secciones y chat versionado | Mantener el chat; nuevo brief ejecutivo específico de D1 |
| Toolbar / acciones / export | Controlador compartido, aprobación persistida, continuidad, CSV/JSON, drawer | Reutilizar el controlador; acciones de D1 integradas en Hero y al final, conservando D2 |
| Navegación / rail | `run_id`, `case_id`, `node_id`, restauración y estado stale | Conservar; el selector visual no modifica URL, configuración ni corrida |
| Iconos / CSS | Registry SVG, tokens dark y ECharts local con lifecycle | Extender el registry y estilos limitados a D1; sin dependencias nuevas |
| Assets | Logo y dos SVG, sin fotografía de Assignment | Crear imagen original local optimizada y fallback al SVG existente |

### Contratos comprobados

- `scenarios.selected.metrics`: `orders`, `total_weight_kg`, `total_cost`, `total_trips`, `load_utilization`, `own_weight_share`, `co2_kg`. Ausencia se representa con `—`; un cero publicado sigue siendo cero.
- Los viajes contienen origen/destino, recurso, cargas, capacidad y estimaciones. `resources` publica la flota normalizada completa de la corrida, incluidas alternativas no utilizadas; su conteo en contexto se diferencia de `vehicles_used`. No certifica un subconjunto filtrado adicional del solver.
- `analysis_depth` se lee de resultado/configuración persistida. Essential/Advanced es una preferencia visual por corrida, independiente de esa propiedad.
- `/api/runs/{id}/comparative`: GET recupera estado; POST solicita explícitamente evidencia; el worker preserva íntegramente selected. La presentación no reejecuta Assignment ni muta el resultado base.
- `/explain` genera y persiste; `/interpretation` recupera explicación, historial, IDs de evidencia y `explanation_is_current`; `/chat` conserva turnos e historial. No se consume inferencia al abrir el dashboard ni al cambiar de nivel visual.
- La aprobación utiliza `caseActions.onApprove` y el endpoint persistido existente; el workspace bloquea aprobación de corridas stale/superseded. La continuidad se resuelve nuevamente después de aprobar.
- CSV/JSON reutilizan `export.mjs`. Running/error se resuelven en workspace; completed/approved/stale se conservan en la presentación.
- No reintroducir profundidad editable de ejecución, selección editable de escenarios, paneles legacy ni el chat como bloque fijo.

### Referencia y pruebas previas

350 pruebas Python y 44 Node aprobadas. Capturas y estructura del dashboard actual en escritorio y móvil guardadas en `/workspace/dation-audit/d1-dashboard-v2-2026-10-16/` antes de modificar la UI.

No se encontraron CSV denominados Golden Pallets v2 en el repositorio ni en el adjunto. Se validarán todos los objetivos sobre datos V3 disponibles y casos sintéticos reproducibles, identificando el conjunto utilizado sin presentarlo como el Golden ausente. `quantity_units` conserva la etiqueta unidades si no hay metadata explícita.

## Implementación final

Las fases 0–9 del documento quedan integradas en D1. El nivel visual se conserva por corrida en `sessionStorage`; abrir Essential/Advanced no cambia `analysis_depth`, la URL, la configuración ni el resultado. El escenario seleccionado se identifica mediante objetivo y fingerprint reales, incluidos objetivos no balanceados, planes iguales y alternativas no factibles.

Essential incluye Hero, contexto, cuatro KPI (costo total, viajes, utilización y participación propia), hasta tres insights deterministas, tabla compacta, participación de recursos, preview de cinco viajes, brief IA colapsado, validación humana y acciones. Advanced conserva toda la evidencia anterior y agrega seis métricas comparables, frontera costo/CO₂ con tamaño por viajes, ganancias/concesiones, utilización ordenable y corredores. Los valores ausentes siguen siendo `—`.

### Archivos modificados

- `backend/app/static/js/dispatch/assignment-comparative-summary.mjs`
- `backend/app/static/js/dispatch/assignment-comparison.mjs`
- `backend/app/static/js/dispatch/assignment-dashboard-selectors.mjs`
- `backend/app/static/js/dispatch/assignment-dashboard-shell.mjs`
- `backend/app/static/js/dispatch/assignment-evidence.mjs`
- `backend/app/static/js/dispatch/assignment-summary.mjs`
- `backend/app/static/js/dispatch/assignment-validation.mjs`
- `backend/app/static/js/dispatch/comparative-upgrade.mjs`
- `backend/app/static/js/dispatch/dashboard-actions.mjs`
- `backend/app/static/js/dispatch/dashboard-toolbar.mjs`
- `backend/app/static/js/dispatch/dashboard.mjs`
- `backend/app/static/js/dispatch/decision-ui.mjs`
- `backend/tests/browser/test_navigation.py`
- `backend/tests/e2e/browser_journey.py`
- `backend/tests/e2e/fixtures.py`
- `backend/tests/e2e/test_workflow.py`
- `backend/tests/e2e/workflow_ui_audit.py`
- `backend/tests/test_assignment_dashboard_phase1.py`
- `backend/tests/test_assignment_dashboard_phase2.py`
- `backend/tests/test_assignment_dashboard_phase3.py`
- `backend/tests/test_assignment_executive_kpis.mjs`

### Archivos creados

- `backend/app/static/assets/assignment-hero-truck.webp`
- `backend/app/static/css/assignment-dashboard-decision.css`
- `backend/app/static/js/dispatch/assignment-advanced.mjs`
- `backend/app/static/js/dispatch/assignment-ai-summary.mjs`
- `backend/app/static/js/dispatch/assignment-essential.mjs`
- `backend/tests/e2e/assignment_matrix_journey.py`
- `backend/tests/test_assignment_ai_summary.mjs`
- `backend/tests/test_assignment_dashboard_v2_selectors.mjs`
- `docs/d1-assignment-dashboard-v2-2026-10-16.md`

### Arquitectura y contratos

- Se reutilizan shell de navegación, registry SVG, lifecycle/scope, toolbar, aprobación, continuidad, exportación, evidencia por viajes/vehículos/órdenes, validación humana y ECharts local. Los nuevos módulos de Essential, Advanced y brief IA usan selectores puros; no se agregan librerías.
- El comparativo existente mantiene GET de restauración y POST explícito. La evidencia adicional actualiza la presentación y el estado del brief, sin reemplazar `scenarios.selected` de la corrida original. Los gráficos se crean al abrir Advanced y se disponen al cambiar la evidencia o desmontar la pantalla.
- Los dos botones de aprobación comparten controlador y bloqueo de concurrencia. La aprobación se persiste por el callback existente, sincroniza ambos botones y permite continuar a Planificación. D2 conserva sus controles y comportamiento.
- No hay cambios de solver, fórmulas, endpoints backend, migraciones ni esquema de Supabase. Se preservan las rutas y los nombres de parámetros actuales.

### Hero y asset

Fotografía original generada para esta entrega, servida desde `backend/app/static/assets/assignment-hero-truck.webp`: 1659 × 948 px, 97.214 bytes, WebP calidad 82. Gradiente oscuro con fotografía integrada a la derecha; texto y acciones conservan legibilidad en móvil. Fallback local: `/static/assets/dda-logistics.svg`, visible si la fotografía no carga. Sin hotlinks.

### IA y vigencia

El chat flotante existente conserva historial, starter questions, seguimiento, contexto y cierre. El nuevo brief es un bloque narrativo independiente y colapsado inicialmente. Abrir el dashboard o cambiar el nivel visual no solicita inferencia.

- GET `/api/runs/{id}/interpretation`: recupera explicación persistida y vigencia.
- POST `/api/runs/{id}/explain`: genera únicamente por acción explícita; permite regenerar y reintentar.
- POST `/api/runs/{id}/chat`: continúa bajo el controlador del chat; «Preguntar sobre este análisis» abre el chat sin enviar una pregunta automáticamente.

Se reutiliza una explicación vigente; nueva evidencia comparativa marca el resumen como desactualizado y ofrece actualización explícita. Hay estados de carga, error y reintento, copia de texto y cancelación al navegar. El modelo no modifica el plan. Las pruebas IA usan respuestas sintéticas y no consumen inferencia de producción.

## Verificación

Desde `backend/`, con Python 3.13, Node 22 y Chromium:

```sh
python -m unittest discover -s tests -v
node --test tests/test_*.js tests/test_*.mjs
.browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_*.py' -v
python tests/e2e/run_suite.py
```

Resultados locales: **350 pruebas Python, 60 Node y 9 E2E aprobadas**, sin omisiones. Compilación Python y sintaxis de todos los módulos JavaScript comprobadas. Auditoría visual aprobada en 12 estados (seis anchos × dos niveles), con contraste y ausencia de overflow.

La suite completa de Chromium incluye 135 pruebas, entre ellas diez nuevas para D1 V2; PostgreSQL 17 añade 46 pruebas de esquema, historial, aprobación y jobs. Ambas son puertas obligatorias de CI, junto con las suites anteriores y auditoría de dependencias. La publicación exige CI verde del commit exacto y su merge, y registra los resultados en los informes de entrega. La comprobación de producción abre D1 y D2, verifica assets idénticos al código, contraste, teclado, exportación y ausencia de escrituras.

### E2E de los cinco objetivos

Nuevo conjunto V3 reproducible de QA: cuatro órdenes (12.000 kg en total) y tres recursos con costos, capacidades, emisiones y titularidades diferentes. Se carga por HTTP en PostgreSQL/PostgREST aislados; el worker real ejecuta `min_trips`, `min_cost`, `max_own_fleet`, `balanced` y `min_co2`; Chromium abre cada resultado sin interceptar la API.

Las cinco ejecuciones aprobaron la verificación del escenario seleccionado, fingerprint, métricas, contexto visual, preview, seis comparaciones y gráfico. `min_trips` seleccionó 0 % de participación propia y los otros objetivos 100 %, verificando que la UI no presupone flota propia ni objetivo balanceado. El navegador no hizo escrituras y las corridas conservaron sus fingerprints. Se conservan además los recorridos reales de aprobación de Assignment, continuidad a Scheduling, exportación e historial.

**Golden Pallets v2 no se recibió en el adjunto ni está en el repositorio.** Esta validación utiliza el conjunto QA descrito y los casos sintéticos existentes; no se presenta como una ejecución del Golden original. Repetir esa prueba exacta requiere sus CSV.

### Evidencia y publicación

Capturas antes/después, controles de contraste y overflow, navegación con teclado, resultados de suites y pruebas de producción en `/workspace/dation-audit/d1-dashboard-v2-2026-10-16/`. La publicación se valida contra el commit exacto, CI de rama/main, Cloud Build, hashes de assets y pruebas del navegador de solo lectura, conservando fingerprints de casos y corridas existentes.

### Ajuste detectado en producción

La comprobación de teclado sobre una corrida real detectó que el scroll nativo podía dejar parcialmente recortado el botón de detalle de un viaje. `assignment-evidence.mjs` ajusta únicamente el desplazamiento horizontal del contenedor al recibir foco, con margen para el anillo visible. Conserva la posición vertical, el estado de la corrida y el ciclo de vida de los listeners. Se agrega una regresión de Chromium que reproduce el recorte parcial en distintos tamaños y verifica que el control y su foco quedan dentro del contenedor.
