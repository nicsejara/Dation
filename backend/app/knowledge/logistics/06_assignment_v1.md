# Assignment V1 — frontera de decisión

## Propósito

Assignment es la primera decisión de la cadena logística de Dation.

Responde únicamente:

> ¿Cómo conviene construir los viajes y distribuir la carga entre los vehículos habilitados?

No responde cuándo debe salir cada viaje.

## Resultado

El resultado `assignment_v1` contiene una lista de viajes abstractos. Cada viaje identifica:

- `trip_id`;
- `vehicle_id`;
- tipo y propiedad del vehículo;
- site base;
- origen y destino;
- capacidad;
- órdenes, productos, unidades y kg asignados;
- utilización;
- costo estimado y CO₂ estimado cuando esos datos están disponibles.

Una misma unidad física puede recibir más de un viaje abstracto. Esto es válido en Assignment porque todavía no existe un calendario. La siguiente decisión, Scheduling, deberá ordenar esos viajes en el tiempo y evitar superposiciones imposibles.

## Restricciones de Assignment

Siempre se respetan:

- unidades enteras;
- conservación total de las unidades incluidas;
- capacidad máxima por viaje;
- compatibilidad entre origen y site del recurso;
- una ruta origen-destino por viaje;
- recursos activos según el estado informado.

No intervienen:

- fecha estimada de despacho;
- fecha de entrega;
- SLA;
- tardanzas;
- velocidad;
- horas de conducción;
- duración del viaje;
- ocupación temporal;
- disponibilidad futura o ventanas de calendario.

Esos elementos pertenecen a Scheduling.

## Objetivos

Assignment puede trabajar con:

- menor cantidad de viajes;
- costo mínimo;
- mayor uso de flota propia;
- menor CO₂;
- balanceado;
- personalizado.

Viajes y uso de flota propia están disponibles con el núcleo mínimo del Data Pack.

Costo requiere `cost_per_km` y `fixed_trip_cost` completos.

CO₂ requiere `co2_kg_per_km` completo.

No interpretar una dimensión deshabilitada como si hubiera participado en el cálculo.

## Costo y CO₂

Cuando están disponibles, costo y CO₂ se estiman para el recorrido de ida y vuelta de cada viaje.

Estas cifras dependen de los factores suministrados por el usuario. No son mediciones históricas ni certificaciones de emisiones.

## Optimalidad

El resultado puede provenir de CP-SAT o de un candidato heurístico determinístico.

Sólo llamar "óptimo" al resultado cuando la evidencia del solver indique explícitamente `optimal`.

En cualquier otro caso hablar de asignación recomendada o mejor solución encontrada bajo el presupuesto de cálculo.

## Handoff a Scheduling

`handoff.schema_version = scheduling_input_v1`.

La fuente es `scenarios.selected.trips`.

Scheduling tomará esa asignación aprobada y resolverá el calendario. No debe reinterpretar Assignment como si ya hubiera decidido fechas.
