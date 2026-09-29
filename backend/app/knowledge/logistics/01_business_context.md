# Logistics DDA — Contexto de negocio

## Propósito

El Logistics Decision Asset v0.1 compara alternativas de asignación de tipo de vehículo para un conjunto de despachos y permite observar su impacto estimado en:

- costo total,
- cantidad total de viajes,
- distancia total recorrida.

El objetivo del DDA no es automatizar ciegamente una decisión. Presenta escenarios comparables para que el decisor entienda el impacto de distintas prioridades.

## Unidad de análisis

Cada fila del dataset representa un despacho independiente identificado por `shipment_id`.

El despacho contiene, entre otros datos:

- producto,
- cantidad de unidades,
- peso unitario,
- origen,
- destino,
- distancia,
- vehículo actualmente asignado,
- capacidad del vehículo,
- costo por kilómetro,
- costo fijo por viaje.

## Catálogo de vehículos

El engine construye un catálogo a partir de los tipos de vehículo observados en el dataset. Para cada tipo utiliza:

- capacidad en kg,
- costo por km,
- costo fijo por viaje.

En v0.1 se supone que todos los tipos detectados pueden evaluarse para todos los despachos.

## Decisión representada

El motor compara tres vistas:

### Baseline

Representa la asignación de vehículo que llega en el CSV. Es el punto de referencia operativo.

### Minimum total cost

Para cada despacho selecciona la alternativa que minimiza el costo total estimado, utilizando viajes, kilómetros, costo por km y costo fijo.

### Minimum trips

Para cada despacho selecciona la alternativa que minimiza la cantidad de viajes. Si hay empate, utiliza distancia y costo como criterios secundarios.

## Interpretación correcta de "recomendado"

El campo `recommended_scenario` significa:

> escenario recomendado por el motor para el objetivo explícitamente seleccionado en esa corrida.

No significa que sea universalmente superior en servicio, capacidad real de flota, riesgo, plazo o cualquier dimensión que el modelo todavía no contemple.

## Preguntas de negocio que v0.1 sí puede responder

- ¿Cuál es el costo estimado del escenario actual?
- ¿Cuánto cambia el costo si priorizo minimizar costo?
- ¿Cuántos viajes se reducen si priorizo viajes?
- ¿Qué diferencia de kilómetros existe contra baseline?
- ¿Cuántos despachos cambian de tipo de vehículo?
- ¿Qué despachos explican los mayores cambios estimados?
- ¿Qué trade-off existe entre costo y cantidad de viajes?

## Preguntas que requieren una versión posterior

- ¿Tengo suficientes camiones disponibles?
- ¿Se cumplen ventanas horarias reales?
- ¿Cómo consolido varios despachos en un mismo viaje?
- ¿Cuál es la mejor secuencia de paradas?
- ¿Qué efecto tiene el clima o el tránsito?
- ¿Qué impacto tiene CO2?
- ¿Qué alternativa maximiza nivel de servicio?
