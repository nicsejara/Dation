# Scheduling V1 — planificación temporal sobre Assignment aprobada

## Propósito

Scheduling es la segunda decisión de la cadena logística de Dation.

Responde:

> ¿Cuándo conviene ejecutar los viajes ya definidos por Assignment?

Scheduling no puede cambiar qué vehículo lleva qué carga.

## Input

Scheduling consume únicamente un handoff `scheduling_input_v1` proveniente de una corrida `assignment_v1` aprobada dentro del mismo Decision Case.

El input temporal se completa con Orders V3 y Fleet V3 del mismo caso.

## Invariantes upstream

Scheduling conserva exactamente:

- `trip_id`;
- `vehicle_id`;
- origen y destino;
- órdenes;
- productos;
- unidades;
- kg;
- capacidad y demás atributos de cada viaje.

Si cualquiera de esos elementos cambia, deja de ser Scheduling y debe volver a ejecutarse Assignment.

## Variables temporales

Para cada viaje Scheduling agrega:

- `ready_date`: fecha mínima derivada de las órdenes que contiene;
- `dispatch_date`: fecha elegida de salida;
- `arrival_date`: fecha estimada de entrega;
- `transit_days`: días de viaje de ida;
- `cycle_days`: días de ocupación ida + retorno;
- `resource_available_again`: primera fecha en que el vehículo puede reutilizarse;
- `wait_days`: espera desde ready date hasta salida.

## Disponibilidad

La salida nunca puede ser anterior a:

- la fecha más tardía `estimated_dispatch_date` de las órdenes del viaje;
- `available_from` del vehículo.

Viajes del mismo `vehicle_id` no pueden superponerse. El vehículo queda ocupado hasta `resource_available_again`.

Si `available_until` está informado, todo el ciclo debe quedar dentro de esa ventana.

## Duraciones

La distancia diaria estimada es:

`avg_speed_kmh × driving_hours_per_day`

La llegada usa:

`ceil(distance_km / distancia_diaria)`

El ciclo completo usa:

`max(1, ceil(2 × distance_km / distancia_diaria))`

El modelo trabaja a nivel día. No representa horas intradía.

## SLA y objetivo

`delivery_due_date` participa sólo cuando está completo en Orders y la configuración lo habilita.

Con SLA activo, la jerarquía del objetivo es:

1. minimizar cantidad de órdenes tardías;
2. minimizar días totales de tardanza;
3. minimizar espera desde ready date;
4. minimizar makespan.

Sin SLA activo:

1. minimizar espera;
2. minimizar makespan.

La prioridad operativa cargada en Orders todavía no modifica esta jerarquía en Scheduling V1.

## Solver

Scheduling usa OR-Tools CP-SAT con intervalos por viaje y `NoOverlap` por `vehicle_id`.

Si el solver no produce una solución utilizable dentro del presupuesto y existe una secuencia heurística factible, puede publicarse esa secuencia como `feasible`, nunca como `optimal`.

## Excepciones

Una orden puede quedar fuera de `delivery_due_date` aun cuando el calendario sea físicamente factible. En ese caso el resultado es `recommended_with_exceptions` y la tardanza debe presentarse explícitamente para revisión humana.

## Handoff

Una planificación aprobada expone `final_assignment_input_v1` para la siguiente decisión.

Scheduling no realiza la decisión 03.
