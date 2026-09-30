# Logistics DDA — Métricas y fórmulas

Este documento describe las métricas generadas por el engine. El intérprete debe usar los valores calculados que recibe; las fórmulas sirven para entender su significado, no para recalcular la corrida.

## Peso total del despacho

`total_weight_kg = quantity_units × unit_weight_kg`

## Viajes requeridos

`required_trips = ceil(total_weight_kg / vehicle_capacity_kg)`

Un vehículo de mayor capacidad puede reducir viajes, pero no necesariamente costo total si su costo por km o costo fijo es mayor.

## Distancia total

En v0.2 cada viaje contempla ida y regreso:

`total_distance_km = required_trips × distance_km × 2`

Por esta razón, con distancia origen-destino fija, minimizar viajes también minimiza kilómetros para ese despacho.

## Costo variable

`variable_cost = total_distance_km × cost_per_km`

## Costo fijo

`fixed_cost = required_trips × fixed_trip_cost`

## Costo total

`total_cost = variable_cost + fixed_cost`

La interfaz presenta estos valores como ARS. Esa interpretación sólo es válida si las variables de costo del dataset están expresadas consistentemente en esa moneda.

## Normalización para modo personalizado

Costo y viajes no se suman directamente porque utilizan unidades y escalas diferentes.

Para las alternativas disponibles de cada despacho se calcula Min-Max:

`normalized_cost = (cost - min_cost) / (max_cost - min_cost)`

`normalized_trips = (trips - min_trips) / (max_trips - min_trips)`

Si máximo y mínimo son iguales, la dimensión normalizada vale 0.

## Score de decisión

`decision_score = cost_weight × normalized_cost + trips_weight × normalized_trips`

La alternativa con menor score es seleccionada.

Un score menor significa mejor ajuste a las prioridades declaradas dentro del conjunto de alternativas evaluadas para ese despacho. No es una métrica operacional universal.

## Extremos

- 100% costo / 0% viajes reproduce exactamente la lógica de `min_cost`.
- 0% costo / 100% viajes reproduce exactamente la lógica de `min_trips`.

## Métricas agregadas de escenario

Cada escenario contiene:

- `shipments`: cantidad de despachos evaluados.
- `total_units`: unidades transportadas.
- `total_weight_kg`: peso agregado.
- `total_trips`: viajes agregados.
- `total_distance_km`: kilómetros agregados.
- `total_cost`: costo agregado estimado.

## Delta versus baseline

- costo negativo: reducción estimada frente a la asignación actual;
- viajes negativo: reducción de viajes;
- distancia negativa: reducción de kilómetros.

No describas un delta como ahorro real ya capturado. Es una diferencia estimada entre escenarios del modelo.
