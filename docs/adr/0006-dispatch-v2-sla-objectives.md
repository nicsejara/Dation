# ADR 0006 — Dispatch v2: SLA jerárquico y objetivos de negocio

Estado: implementado en Fase 4.

## Contexto

Dispatch 1.2.0 ya representaba demanda, ubicación de flota y ocupación temporal multiday, pero trataba costo, viajes y tiempo como objetivos ponderables del mismo nivel. Ese esquema permitía conceptualmente que una mejora económica compensara una peor entrega, y no representaba de forma explícita utilización de flota propia ni CO₂ como prioridades de negocio.

## Decisión

El motor adopta `schema_version=dispatch_v2` y `engine_version=2.2.0`.

La optimización se resuelve lexicográficamente:

1. minimizar cantidad de órdenes fuera de SLA;
2. minimizar días de tardanza ponderados por prioridad;
3. manteniendo el mejor nivel de servicio encontrado, optimizar el objetivo de negocio configurado.

Los pesos de prioridad de tardanza son:

- High: 9
- Normal: 3
- Low: 1

Los objetivos configurables son:

- `min_cost`: costo total;
- `min_time`: tiempo medio ponderado por unidades;
- `max_utilization`: minimizar participación de kg tercerizados, equivalente operacional a maximizar participación de flota propia;
- `min_co2`: emisiones estimadas ida + vuelta;
- `balanced`: reparto uniforme entre las dimensiones activas;
- `custom`: pesos explícitos entre costo, tiempo, uso propio y CO₂.

`total_trips` permanece como KPI y desempate determinístico, no como objetivo configurable.

## Recuperación de SLA

El modelo puede explorar salidas posteriores al plazo on-time dentro de un horizonte limitado por `max_late_days`, 30 días por defecto.

Esto permite diferenciar:

- una distribución completa con excepciones de SLA;
- una ausencia real de distribución completa dentro del horizonte operativo.

Una corrida con excepciones devuelve `decision.status=recommended_with_exceptions`; no se presenta como error técnico.

## Contrato de salida

Dispatch v2 agrega:

- `decision`
- `feasibility`
- `decision_drivers`
- `exceptions`
- escenarios `min_cost`, `min_time`, `max_utilization`, `min_co2`, `balanced` y `selected`.

`decision_drivers` contiene hechos determinísticos para explicación: consolidación, división, tercerización, postergación, excepciones SLA y participación propia.

`exceptions` lista las órdenes fuera de SLA con prioridad, deadline, llegada, días de tardanza y viajes relacionados.

## Certificación del solver

El estado del objetivo de negocio y la certificación de SLA son independientes.

- `sla_certified=true` significa que CP-SAT certificó el óptimo del primer nivel.
- `solver.status=optimal` significa que el objetivo de negocio fue certificado bajo la restricción SLA vigente.
- Si SLA sólo tiene un incumbent factible, la interfaz debe decir “Mejor SLA encontrado”.
- Nunca se declara óptimo un resultado heurístico o feasible.

## Utilización propia

El objetivo `max_utilization` minimiza `outsourced_weight_share`. Se elige esta definición porque evita maximizar artificialmente un cociente de ocupación cargando pocos viajes propios.

`own_load_utilization` sigue siendo un KPI para evaluar qué tan llenos viajan los recursos propios efectivamente usados.

## Persistencia y compatibilidad

Las corridas nuevas se guardan como `dispatch_v2`. Las corridas `dispatch_v1` no se reescriben y continúan abriendo con su semántica histórica.

La migración `20261002184751_dispatch_v2_integrity.sql` amplía el trigger existente para aceptar V1/V2 y comprueba que una corrida completada tenga la misma versión en la fila y en `result_json`.

## Limitaciones

El horizonte de recuperación no convierte una tardanza en una solución deseable: únicamente permite encontrar la distribución completa de menor daño de servicio.

La clasificación `capacity_or_policy_sla_violations` no atribuye causalidad específica. Para afirmar que una tardanza fue causada por capacidad, tercerización deshabilitada u otra política se requiere evidencia determinística adicional.

## Decision Composer 2.1

La configuración distingue entre restricciones físicas obligatorias y dimensiones de negocio opcionales. `dimensions` controla qué ejes participan del balance, comparaciones y sensibilidad. `analysis_depth` puede ser `essential`, `comparative` o `deep`; este valor controla cuántos escenarios ejecuta el motor y no es sólo una preferencia visual.

## Dashboard 2.2

Las diferencias contra `baseline_direct` no se presentan como ahorro real. La referencia es una política sintética de despacho individual, no una observación histórica. El dashboard prioriza la distribución ejecutable y la asignación por pool; comparaciones y sensibilidad quedan como evidencia secundaria disponible para auditoría e interpretación IA.
