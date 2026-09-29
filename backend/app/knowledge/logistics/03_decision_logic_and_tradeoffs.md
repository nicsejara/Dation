# Logistics DDA — Lógica de decisión y trade-offs

## Objetivo min_cost

Para cada shipment, el engine evalúa cada tipo de vehículo disponible en el catálogo y prioriza:

1. menor `total_cost`,
2. ante empate, menor `required_trips`,
3. ante nuevo empate, menor `total_distance_km`.

El escenario agregado es la suma de esas elecciones individuales.

Interpretación correcta:
"Esta alternativa es la recomendada porque minimiza el costo estimado dentro del universo de alternativas modeladas."

## Objetivo min_trips

Para cada shipment, el engine prioriza:

1. menor `required_trips`,
2. ante empate, menor `total_distance_km`,
3. ante nuevo empate, menor `total_cost`.

Interpretación correcta:
"Esta alternativa es la recomendada porque minimiza los viajes requeridos dentro del universo de alternativas modeladas."

## Baseline

Baseline no es una alternativa optimizada. Es la asignación existente en el archivo de entrada y funciona como referencia para medir el impacto potencial.

## Trade-offs esperables

### Vehículo más grande

Puede:
- reducir cantidad de viajes,
- reducir kilómetros totales,
- aumentar costo por km,
- aumentar costo fijo por viaje.

Por lo tanto, el vehículo de mayor capacidad no es automáticamente el de menor costo.

### Vehículo más pequeño

Puede:
- tener menor costo unitario de operación,
- necesitar más viajes,
- acumular más kilómetros,
- acumular más costos fijos.

Tampoco es automáticamente más económico.

## Cómo explicar por qué cambia una recomendación

Usá este orden:

1. Identificá el objetivo de la corrida.
2. Compará el KPI objetivo contra baseline.
3. Señalá los KPI secundarios que mejoran o empeoran.
4. Indicá cuántos shipments cambian de tipo de vehículo si ese dato está disponible.
5. Usá los principales drivers por shipment provistos por el backend.
6. Cerrá con el supuesto o restricción más material.

## "Mejor alternativa"

Cuando el usuario pregunte "¿por qué es la mejor alternativa?", interpretalo como:

"¿por qué el motor la recomienda para el objetivo seleccionado?"

No conviertas esa frase en una afirmación absoluta.

## Driver de una mejora

Un shipment es un driver cuando su cambio de asignación explica una parte relevante de la diferencia de costo, viajes o distancia contra baseline.

El backend puede proveer una lista de principales cambios. Utilizá esos valores directamente; no inventes drivers que no estén presentes.
