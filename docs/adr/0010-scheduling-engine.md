# ADR 0010 — Scheduling como segunda decisión temporal

Estado: implementado en Fase 4.

## Contexto

Assignment 1.0 separó la construcción de viajes de su ejecución temporal. Quedaba pendiente decidir cuándo puede ejecutarse cada viaje aprobado sin reabrir la distribución de carga.

## Decisión

Dation incorpora un motor independiente de Scheduling:

- engine: `logistics-scheduling-engine`;
- version: `1.0.0`;
- result schema: `scheduling_v1`;
- input handoff: `scheduling_input_v1`;
- output handoff: `final_assignment_input_v1`.

Scheduling sólo puede ejecutarse sobre una corrida `assignment_v1` completada y aprobada, del mismo Decision Case y del mismo par Orders/Fleet.

## Inmutabilidad upstream

Scheduling conserva exactamente:

- trip_id;
- vehicle_id;
- origen y destino;
- órdenes, productos, unidades y kg;
- la composición de cada viaje.

Cambiar cualquiera de esos elementos requiere volver a Assignment.

## Modelo temporal

Para cada viaje:

- ready date = máximo `estimated_dispatch_date` de sus órdenes;
- earliest dispatch = máximo entre ready date y `available_from` del vehículo;
- transit days = `max(1, ceil(distance / (speed × driving_hours_per_day)))`;
- cycle days = `max(1, ceil(2 × distance / (speed × driving_hours_per_day)))`;
- resource available again = dispatch + cycle days.

Los intervalos de viajes del mismo `vehicle_id` usan `NoOverlap` en CP-SAT.

Si `available_until` está informado, todo el ciclo ocupado debe finalizar dentro de esa ventana inclusiva.

## Objetivo

Cuando `delivery_due_date` está completo y habilitado:

1. minimizar órdenes tardías;
2. minimizar días totales de tardanza;
3. minimizar espera desde ready date;
4. minimizar makespan.

Sin SLA:

1. minimizar espera;
2. minimizar makespan.

La dominancia se implementa con coeficientes enteros acotados, de modo que un nivel superior no pueda ser compensado por mejoras en niveles inferiores.

## Fallback

El motor genera una secuencia heurística determinística como hint y respaldo. Si CP-SAT no entrega una solución utilizable por presupuesto de cálculo pero la heurística es factible, puede publicarse como `feasible`. Nunca se etiqueta `optimal` sin certificación del solver.

## Aprobación humana durable

La aprobación de Assignment y Scheduling se persiste en la metadata `decision_case` de `configuration_json` y `result_json` del run mediante `POST /api/runs/{run_id}/approve`.

La aprobación no cambia el fingerprint matemático del resultado.

Scheduling verifica la aprobación persistida de Assignment antes de comenzar. Esto evita depender de `sessionStorage` para una precondición de negocio.

## Resultado

`scheduling_v1` agrega fechas y métricas temporales sobre los viajes fijos, además de excepciones de fecha objetivo cuando corresponda.

Una Scheduling aprobada publica `final_assignment_input_v1` para Decision 03.

## Persistencia

No se agregan tablas ni columnas. `decision_runs.schema_version` admite el nuevo valor y los contratos viven en JSONB.

El trigger histórico `validate_dispatch_run` continúa validando específicamente `dispatch_v1/dispatch_v2`; las precondiciones de `assignment_v1` y `scheduling_v1` se validan en API/servicio.

## Limitaciones

Scheduling V1 trabaja a nivel día y no representa:

- horas intradía;
- descansos regulatorios detallados;
- tráfico o clima;
- tiempos de carga/descarga;
- reposicionamiento entre bases;
- multiparada;
- cambios de vehículo posteriores a Assignment.
