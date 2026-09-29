# Logistics DDA — Métricas y fórmulas

Este documento describe las métricas generadas por el engine. El intérprete debe usar los valores calculados que recibe; estas fórmulas sirven para entender su significado, no para volver a calcular la corrida.

## Peso total del despacho

`total_weight_kg`

Peso total transportado por un shipment.

Conceptualmente:

`quantity_units × unit_weight_kg`

## Viajes requeridos

`required_trips`

Cantidad mínima de viajes completos necesarios para transportar el peso del despacho con el tipo de vehículo evaluado.

Conceptualmente:

`ceil(total_weight_kg / vehicle_capacity_kg)`

Un vehículo de mayor capacidad puede reducir viajes, pero no necesariamente costo total si su costo por km o costo fijo es mayor.

## Distancia total

`total_distance_km`

En v0.1 cada viaje contempla ida y vuelta.

Conceptualmente:

`required_trips × distance_km × 2`

Por esta razón, con una distancia origen-destino fija, minimizar viajes también tiende a minimizar kilómetros.

## Costo variable

`variable_cost`

Costo asociado a los kilómetros recorridos.

Conceptualmente:

`total_distance_km × cost_per_km`

## Costo fijo

`fixed_cost`

Costo fijo acumulado de los viajes necesarios.

Conceptualmente:

`required_trips × fixed_trip_cost`

## Costo total

`total_cost`

Suma del costo variable y el costo fijo estimado.

Conceptualmente:

`variable_cost + fixed_cost`

La demo actual presenta monetariamente estos valores como ARS en la interfaz. La validez de la moneda depende de que las variables de costo del dataset estén expresadas consistentemente en esa moneda.

## Métricas agregadas de escenario

Cada escenario contiene:

- `shipments`: cantidad de despachos evaluados.
- `total_units`: unidades transportadas.
- `total_weight_kg`: peso agregado.
- `total_trips`: viajes agregados.
- `total_distance_km`: kilómetros agregados.
- `total_cost`: costo agregado estimado.

## Delta versus baseline

Los escenarios optimizados contienen variaciones porcentuales contra baseline.

- valor negativo en costo: reducción estimada de costo.
- valor positivo en costo: incremento estimado de costo.
- valor negativo en viajes: reducción de viajes.
- valor negativo en distancia: reducción de kilómetros.

No describas un delta como ahorro real ya capturado. Es una diferencia estimada por el modelo entre escenarios.
