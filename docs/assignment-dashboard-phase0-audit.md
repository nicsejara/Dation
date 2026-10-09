# Assignment Dashboard V2 — Fase 0 · Auditoría y contrato

Fecha: 2026-10-09

Base auditada: `main@c3a82df1aaf56d63ab1a42755a8dfe828eb0edff`

Alcance de esta fase: **auditoría y contrato solamente**. No se modifica todavía el diseño del dashboard, el solver, los modelos de negocio, el intérprete IA ni el flujo de Scheduling.

## 1. Criterio de salida

**PASS.** Una corrida Esencial y una Comparativa se distinguen de forma persistida y reproducible.

Selector canónico propuesto para la siguiente fase:

```js
function getAnalysisDepth(run){
  const result=run?.result_json||{};
  return result.analysis?.depth
    || result.configuration?.options?.analysis_depth
    || run.configuration_json?.options?.analysis_depth
    || "comparative";
}
```

Las tres primeras ubicaciones son observables hoy en el contrato real. El fallback `comparative` sólo debe usarse para compatibilidad con corridas antiguas que no tengan profundidad persistida.

### Dónde se persiste `analysis_depth`

1. El frontend envía `options.analysis_depth` desde `workspace.mjs`.
2. `RunRequest` valida `options` con `AssignmentOptions`.
3. `dispatch_service.execute()` persiste `run.configuration_json.options.analysis_depth`.
4. `run_assignment_engine()` canoniza el valor en `opts["analysis_depth"]`.
5. El resultado publica:
   - `result.analysis.depth`;
   - `result.configuration.options.analysis_depth`.

Por lo tanto, la profundidad es una **propiedad de la corrida**, no un estado de UI que deba poder alternarse después de ejecutar.

## 2. Contrato observado de `assignment_v1`

### Identidad

```text
schema_version = assignment_v1
decision.id = logistics_assignment
analysis.temporal = false
handoff.schema_version = scheduling_input_v1
handoff.next_decision = logistics_scheduling
handoff.source_path = scenarios.selected.trips
```

Assignment resuelve la distribución de carga y la construcción de viajes abstractos. No resuelve fechas, SLA, tardanzas, lead time temporal, ocupación futura ni superposición de viajes.

### Resultado de alto nivel

El `result_json` observado contiene:

- `schema_version`;
- `decision`;
- `analysis`;
- `capabilities`;
- `decision_drivers`;
- `exceptions`;
- `engine`;
- `inputs`;
- `configuration`;
- `resources`;
- `kpi_directions`;
- `normalization`;
- `assumptions`;
- `scenarios`;
- `sensitivity`;
- `handoff`;
- fingerprint de resultado persistido por la corrida;
- `decision_case` agregado por el servicio cuando la ejecución pertenece a un caso.

### `scenarios.selected`

El escenario seleccionado conserva detalle operativo completo:

- `metrics`;
- `trips`;
- `order_outcomes`;
- `name`;
- `feasible`;
- `solver`;
- `plan_fingerprint`.

Cada viaje puede contener:

- `trip_id`;
- `vehicle_id`;
- `vehicle_type`;
- `ownership`;
- `provider_name`;
- `base_site`;
- `origin`;
- `destination`;
- `distance_km`;
- `capacity_kg`;
- `load_kg`;
- `utilization`;
- `estimated_cost`;
- `estimated_co2_kg`;
- `loads`.

Cada carga conserva `order_id`, `product`, `units` y `kg`.

Cada `order_outcome` conserva, entre otros, `order_id`, `product`, `units`, `kg`, `trip_ids`, `vehicle_ids`, `split`, `consolidated` y `outsourced`.

### Métricas observadas

`selected.metrics` contiene actualmente:

- `orders`;
- `units_assigned`;
- `total_weight_kg`;
- `total_trips`;
- `vehicles_used`;
- `own_trips`;
- `outsourced_trips`;
- `load_utilization`;
- `own_weight_kg`;
- `outsourced_weight_kg`;
- `own_weight_share`;
- `outsourced_weight_share`;
- `total_cost` (nullable);
- `co2_kg` (nullable).

No se debe tratar `load_utilization` o `vehicles_used` como causa de selección salvo que el producto demuestre que participaron del objetivo. Son KPIs operativos descriptivos.

## 3. Capabilities y objetivos

Objetivos válidos en `AssignmentConfig`:

- `min_trips`;
- `min_cost`;
- `max_own_fleet`;
- `min_co2`;
- `balanced`;
- `custom`.

Dimensiones válidas:

- `trips`;
- `cost`;
- `own_fleet`;
- `co2`.

Disponibilidad observada:

- `trips`: siempre disponible;
- `own_fleet`: siempre disponible;
- `cost`: requiere `cost_per_km` y `fixed_trip_cost` completos;
- `co2`: requiere `co2_kg_per_km` completo.

`AssignmentOptions` acepta `essential`, `comparative` y `deep`, pero **el configurador actual sólo permite Esencial o Comparativo** y normaliza cualquier otro valor visible a Comparativo. `deep` debe considerarse capacidad backend/compatibilidad, no una opción de producto actual.

## 4. Matriz real de escenarios

Definición: un “extremo activo” es el escenario correspondiente a cada dimensión activa:

| Dimensión | Escenario |
|---|---|
| `trips` | `min_trips` |
| `cost` | `min_cost` |
| `own_fleet` | `max_own_fleet` |
| `co2` | `min_co2` |

### 4.1 Esencial + objetivo simple

Para `min_trips`, `min_cost`, `max_own_fleet` o `min_co2`:

- se ejecuta/persiste el escenario del objetivo solicitado;
- se persiste `selected`;
- no se agrega `balanced`;
- `sensitivity.frontier = []`;
- `analysis.scenario_count = 1`.

Ejemplo `min_trips`:

```text
scenarios = min_trips + selected
```

### 4.2 Esencial + balanceado

- se construyen todos los extremos de las dimensiones activas;
- se construye `balanced`;
- `selected` es copia de la alternativa balanceada elegida;
- `sensitivity.frontier = []`;
- `scenario_count = extremos activos + 1`.

### 4.3 Esencial + custom

- se construyen todos los extremos de las dimensiones activas;
- se construye un `selected` con los pesos custom;
- no se agrega `balanced` por el solo hecho de ser Esencial;
- `sensitivity.frontier = []`;
- `scenario_count = extremos activos`.

### 4.4 Comparativo + objetivo simple

- se construyen todos los extremos activos;
- se agrega `balanced`;
- se persiste `selected` como la alternativa seleccionada bajo el objetivo ejecutado;
- `sensitivity.frontier` contiene todos los escenarios no `selected`;
- `scenario_count = extremos activos + 1`.

### 4.5 Comparativo + balanceado

- extremos activos;
- `balanced`;
- `selected` equivalente al plan balanceado seleccionado;
- frontier con todos los no seleccionados.

### 4.6 Comparativo + custom

- extremos activos;
- `balanced`;
- `selected` calculado con pesos custom;
- frontier con todos los no seleccionados.

### 4.7 Detalle que NO se persiste en alternativas

Antes de publicar el resultado, el engine elimina de todo escenario distinto de `selected`:

- `trips`;
- `order_outcomes`.

Las alternativas conservan métricas, nombre, factibilidad, solver y `plan_fingerprint`. Por lo tanto el dashboard Comparativo V2 puede comparar alternativas **a nivel de métricas**, pero no debe prometer detalle vehículo/viaje/orden de una alternativa no seleccionada.

También es válido que `selected.plan_fingerprint` coincida con el fingerprint de un escenario nombrado. Ese caso significa “misma distribución” y debe tratarse explícitamente en la UI comparativa.

## 5. Optimalidad

El contrato expone `engine.solver.status`.

Regla de producto confirmada: sólo se puede utilizar “óptimo” cuando el estado sea exactamente `optimal`. `feasible`, `heuristic` o `best_candidate` deben presentarse como asignación recomendada / mejor solución encontrada bajo la configuración y presupuesto ejecutados.

## 6. Handlers actuales del dashboard

El dashboard recibe los siguientes handlers desde `workspace.mjs`:

### `onApprove`

- llama `POST /api/runs/{run_id}/approve`;
- persiste aprobación del run y del Decision Case;
- cambia el nodo actual a `approved`;
- desbloquea el siguiente nodo cuando corresponde;
- persiste el estado local.

### `onApprovalComplete`

Comportamiento actual:

```text
unlockNextNode(nodeId)
persist()
```

**No navega automáticamente al mapa.** Esta es una diferencia importante respecto de algunas iteraciones UX anteriores. Si Fase 1 necesita un siguiente paso visible, debe usar el comportamiento real disponible y no asumir navegación automática.

### `onFlow`

Navega a:

```text
logistics-map
```

Es el handler vigente para “Mapa de decisiones” / “Explorar mapa”.

### `onOpenNode`

Apunta a `openCaseResult(nodeId)`.

Sólo puede abrir nodos con un `run_id` accesible desde el rail. El rail actual habilita resultados en estado `review`, `approved` o `running`.

### `onRerun`

Se pasa como argumento posicional a `dashboard.render()`.

Para Assignment:

- reconstruye dimensiones, objetivo, pesos, filtros, profundidad, modo de flota y anomalías desde la corrida;
- recupera los datasets originales;
- vuelve a `logistics-config`;
- **no ejecuta automáticamente** una nueva corrida.

Esto cumple el principio de “Reconfigurar y ejecutar nuevamente” sin disparar un run por sí solo.

## 7. Comportamiento post-aprobación observado

Hoy la secuencia es:

```text
Aprobar
→ POST /approve
→ nodo Assignment = approved
→ desbloquear siguiente nodo
→ actualizar estado local
→ permanecer en el dashboard
```

El regreso al mapa es una acción separada mediante `onFlow`.

Riesgo UX para Fase 1: el botón superior de aprobación queda en la command bar y compite con el recorrido de evidencia. El rediseño debe mover la aprobación primaria hacia Validación, pero **sin alterar todavía el contrato backend de aprobación**.

## 8. Export actual

`exportDecision(result)` ya soporta `assignment_v1` y genera:

```text
assignment-recomendada.csv
```

Exporta la recomendación seleccionada a nivel viaje × carga con columnas de viaje, vehículo, propiedad, proveedor, site, ruta, orden, producto, unidades, kg, capacidad, utilización, costo y CO₂ cuando existen.

`exportDecisionJson(result, runId)` también existe y genera JSON técnico.

Diferencia actual: `dashboard.mjs` no usa ese helper para JSON; descarga directamente `decision-{run_id}.json`.

No existe todavía:

- CSV comparativo;
- PDF;
- export detallado de viajes de alternativas no seleccionadas.

Fase 1 debe reutilizar el CSV actual y puede unificar el JSON técnico sin inventar formatos nuevos. El CSV comparativo pertenece a una fase posterior si se implementa su contrato real.

## 9. Intérprete Dation IA y persistencia

Para `assignment_v1`, `build_decision_context()` delega a `build_assignment_context()`.

El contexto IA actual incluye:

- `configuration` completa, por lo tanto también profundidad;
- capabilities;
- decision drivers;
- key events;
- selected metrics;
- agregado por vehículo;
- ejemplos de órdenes;
- alternativas tomadas de `sensitivity.frontier`;
- handoff;
- anomalías;
- supuestos;
- boundary explícito no temporal.

Consecuencia:

- Esencial entrega `alternatives = []` porque no publica frontier;
- Comparativo entrega las alternativas métricas publicadas por frontier.

La explicación generada se persiste en `decision_explanations` con:

- `run_id`;
- provider;
- model;
- knowledge version;
- prompt version;
- `response_json`;
- usage.

El chat se persiste en `decision_messages` con rol, contenido, provider/model y knowledge version.

El endpoint `GET /api/runs/{run_id}/interpretation` devuelve la explicación más reciente y el historial de mensajes.

### Deuda confirmada para Fase 4

El schema actual del intérprete todavía exige `business_impact.cost`, `business_impact.trips` y `business_impact.distance`. Además, el prompt Assignment no cambia explícitamente su estructura de salida según `analysis_depth`.

Esto confirma que el rediseño de IA debe esperar a su fase propia y mantener backward compatibility.

## 10. Diferencias entre el documento de diseño y `main`

1. **`analysis_depth` sí está completamente persistido** y puede distinguir las dos experiencias sin agregar backend nuevo.
2. `compare.mjs` existe pero **no se monta** en Assignment y contiene métricas de otros schemas (`avg_lead_time_days`, SLA, etc.). No debe reutilizarse sin adaptación.
3. La evidencia actual es vehicle-centric y mantiene un gran ECharts por vehículo; no es trip-centric todavía.
4. `onApprovalComplete` no navega al mapa; únicamente desbloquea/persiste. `onFlow` es la navegación real al mapa.
5. El backend acepta `deep`, pero el configurador de producto sólo expone Esencial/Comparativo.
6. El helper de export JSON existe, pero el dashboard usa una descarga JSON paralela.
7. No existe `validation_summary` explícito en `assignment_v1`; Fase 2 no debe simular una checklist de controles de motor que no esté respaldada por evidencia persistida.
8. Las alternativas no seleccionadas no tienen `trips` ni `order_outcomes`, tal como anticipaba el documento.

## 11. Riesgos a proteger

- No alterar `assignment_v1` sólo para resolver composición visual.
- No introducir fechas/SLA en Assignment.
- No recalcular métricas en el frontend.
- No asumir que un KPI descriptivo fue parte del objetivo.
- No llamar “óptimo” a `feasible`.
- No mostrar cero cuando costo/CO₂ son `null`.
- No prometer detalle alternativo inexistente.
- No romper el dashboard Scheduling mientras se refactoriza el orquestador compartido.
- No romper persistencia/aprobación del Decision Case.
- No disparar una nueva corrida al reconfigurar.
- No hacer depender aprobación de Dation IA.

## 12. Fixtures creados por esta fase

Los fixtures bajo `backend/tests/fixtures/assignment_dashboard/` son **fixtures contractuales sintéticos**. No representan datos de producción ni una captura de Supabase; modelan exactamente las invariantes observadas del engine para permitir tests determinísticos del nuevo dashboard.

Se incluyen:

- `assignment_essential_run.json`: Esencial + `min_trips`;
- `assignment_comparative_run.json`: Comparativo + `min_trips`, con cinco referencias métricas y un caso de misma distribución por fingerprint.

## 13. Plan técnico concreto de Fase 1

Fase 1 debe ser de **shell, navegación y herramientas**, sin tocar evidencia, engine ni IA.

### Crear

- `backend/app/static/css/assignment-dashboard-v2.css`
  - scope `.assignment-dashboard-v2`;
  - toolbar compacta;
  - rail compacto;
  - dropdowns Exportar / Más;
  - drawer de detalles;
  - responsive desktop/tablet;
  - focus visible y estados accesibles.

- `backend/app/static/js/dispatch/assignment-dashboard-selectors.mjs`
  - empezar con `getAnalysisDepth(run)` como selector puro;
  - helpers de labels técnicos necesarios por el shell, sin derivar evidencia operativa todavía.

- `backend/app/static/js/dispatch/assignment-dashboard-shell.mjs`
  - shell exclusivo de `assignment_v1`;
  - toolbar;
  - badge de profundidad persistida;
  - badge de estado;
  - compact case rail reutilizando el contrato de Decision Case;
  - Exportar / Más;
  - drawer Detalles de ejecución.

### Adaptar

- `backend/app/static/js/dispatch/dashboard.mjs`
  - mantenerlo como orquestador;
  - delegar shell Assignment V2 sólo cuando `schema_version === "assignment_v1"`;
  - Scheduling debe seguir usando su renderer actual;
  - conservar contenido existente `hero/assignment/review/explanation` durante Fase 1.

- `backend/app/static/js/dispatch/export.mjs`
  - sólo si hace falta exponer/reutilizar `exportDecisionJson` desde el shell;
  - no agregar CSV comparativo en Fase 1.

- `backend/app/templates/app.html`
  - cargar CSS scoped después de `dispatch.css` o usar import dinámico versionado consistente.

### Tests de Fase 1

Agregar contratos específicos para:

- selector de profundidad;
- shell Esencial vs Comparativo sin switch editable;
- volver al mapa;
- CSV actual;
- JSON técnico;
- rerun a configuración;
- drawer abrir/cerrar/Escape/click fuera;
- estado review/approved;
- nodos bloqueados sin navegación;
- Scheduling no modificado.

## 14. Archivos que Fase 1 puede tocar

Principalmente:

```text
backend/app/static/js/dispatch/dashboard.mjs
backend/app/static/js/dispatch/decision-nav.mjs       # sólo si se extrae una variante compacta reutilizable
backend/app/static/js/dispatch/export.mjs             # sólo integración JSON
backend/app/templates/app.html                         # carga CSS/module si corresponde
backend/app/static/css/assignment-dashboard-v2.css    # nuevo
backend/app/static/js/dispatch/assignment-dashboard-selectors.mjs # nuevo
backend/app/static/js/dispatch/assignment-dashboard-shell.mjs     # nuevo
backend/tests/...                                      # contratos de Fase 1
```

## 15. Archivos que Fase 1 NO debe tocar

```text
backend/app/engines/assignment/engine.py
backend/app/engines/assignment/plans.py
backend/app/engines/assignment/model.py
backend/app/models/assignment_config.py
backend/app/services/decision_interpreter_service.py
backend/app/services/dispatch_context.py
backend/app/knowledge/logistics/06_assignment_v1.md
backend/app/static/js/dispatch/scheduling-dashboard.mjs
backend/app/engines/scheduling/**
```

Tampoco debe cambiar el schema de Supabase, el contrato de aprobación ni el payload `assignment_v1`.

---

## Conclusión

La Fase 0 demuestra que el rediseño puede implementarse sin alterar el motor: la profundidad está persistida, el payload seleccionado contiene suficiente evidencia trip-centric y el modo Comparativo ya publica alternativas métricas y fingerprints. El principal trabajo de Fase 1 es reorganizar la carcasa y las herramientas respetando estos contratos, no crear nueva lógica de decisión.
