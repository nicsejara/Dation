# Contrato dispatch_v2 — SLA primero, negocio después

Estas reglas corresponden a logistics-dispatch-engine 2.1.0 y al envelope `dispatch_v2`.

## Orden de decisión

El motor resuelve la decisión en dos niveles:

1. **Nivel de servicio (SLA)**: minimiza primero la cantidad de órdenes tardías. Como segundo criterio de servicio minimiza días de tardanza ponderados por prioridad.
2. **Objetivo de negocio**: sólo entre distribuciones que conservan el mejor SLA encontrado, optimiza costo, tiempo, uso de flota propia, CO₂ o una ponderación personalizada.

Nunca explicar una tardanza como consecuencia aceptada para ahorrar costo o CO₂ cuando el resultado indica que existe una solución con mejor SLA. Si `sla_optimal_certified=false`, hablar de **mejor SLA encontrado**, no de SLA óptimo.

## Objetivos

- `min_cost`: minimizar costo total.
- `min_time`: minimizar tiempo medio de entrega ponderado por unidades.
- `max_utilization`: maximizar participación de flota propia minimizando el peso tercerizado. `own_load_utilization` es un KPI complementario y no debe confundirse con el objetivo.
- `min_co2`: minimizar CO₂ estimado del ciclo ida y vuelta.
- `balanced`: ponderación equivalente entre las dimensiones activas.
- `custom`: ponderación explícita del usuario entre las cuatro dimensiones.

Viajes sigue siendo KPI y desempate, no una prioridad configurable.

## Evidencia determinística

`decision_drivers` contiene hechos calculados por el motor, como órdenes consolidadas, divididas, tercerizadas o postergadas. No inferir una causa más específica si no está presente.

`exceptions` contiene las órdenes que quedan fuera de SLA con prioridad, días de tardanza, deadline, llegada y viajes asociados.

`feasibility.physical_sla_violations` indica tardanzas inevitables aun con salida inmediata por distancia/plazo.

`feasibility.capacity_or_policy_sla_violations` indica excepciones adicionales asociadas al conjunto de restricciones y políticas vigentes. No atribuirlas exclusivamente a falta de flota, tercerización deshabilitada u otra causa específica salvo evidencia adicional.

## Recursos

Cada viaje conserva `fleet_pool_id`, `base_location`, `dispatch_date`, `arrival_date`, `cycle_days` y `resource_available_again`.

Un pool finito queda ocupado desde la salida hasta completar ida, entrega y retorno. Un pool propio sólo atiende su base. Un tercerizado con base `*` puede operar desde cualquier origen.

## Métricas

Costo y emisiones usan distancia ida y vuelta. El costo por km ya incluye combustible. CO₂ y combustible son estimaciones basadas en factores informados por el usuario.

`own_weight_share` = kg transportados por flota propia / kg totales.

`outsourced_weight_share` = kg tercerizados / kg totales.

`on_time_rate` = órdenes dentro de SLA / órdenes incluidas.

La llegada de una orden es la última llegada de cualquiera de sus fracciones.

## Lenguaje

La salida principal se llama **Decisión recomendada**. La ejecución detallada se llama **Distribución recomendada**.

Nunca presentar la recomendación como “la mejor opción absoluta”: es la recomendación bajo datos, restricciones, disponibilidad y objetivo configurado.

Nunca llamar “óptimo” a un resultado cuando el solver no lo certificó.
