# Logistics DDA — Contexto de negocio

## Propósito

El DDA Logística v0.2 compara alternativas de asignación de tipo de vehículo para un conjunto de despachos y cuantifica su impacto estimado en:

- costo total,
- cantidad total de viajes,
- distancia total recorrida.

El DDA no automatiza ciegamente una decisión. Presenta escenarios comparables y trazables para que el decisor pueda elegir prioridades y entender sus consecuencias.

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

El engine construye un catálogo a partir de los tipos de vehículo observados en el dataset. Para cada tipo utiliza capacidad, costo por kilómetro y costo fijo por viaje.

En v0.2 se supone que todos los tipos detectados pueden evaluarse para todos los despachos.

## Escenarios

### Situación actual

Representa la asignación que llega en el CSV. Es baseline y sirve para medir el impacto potencial de adoptar una recomendación.

### Costo mínimo

Prioriza la alternativa de menor costo total estimado por despacho.

### Viajes mínimos

Prioriza la alternativa con menor cantidad de viajes requeridos por despacho.

### Configuración personalizada

Cuando el usuario selecciona pesos intermedios, el motor normaliza costo y viajes dentro del conjunto de alternativas de cada despacho y aplica un score ponderado.

Este escenario representa la preferencia declarada por el decisor, no una mezcla de unidades monetarias con cantidad de viajes.

## Sensibilidad

Los extremos 100% costo y 100% viajes enmarcan la configuración seleccionada. Permiten responder si una ponderación intermedia modifica realmente la asignación o si la solución permanece igual que uno de los extremos.

Baseline y extremos cumplen funciones diferentes:

- baseline: mide cambio frente a la operación actual;
- extremos: muestran sensibilidad frente a las preferencias.

## Interpretación correcta de "recomendado"

`recommended_scenario` significa:

> escenario recomendado por el motor para la configuración explícitamente seleccionada en esa corrida.

No significa que sea universalmente superior en servicio, capacidad real de flota, riesgo, plazo o cualquier dimensión que el modelo todavía no contemple.

## Preguntas que v0.2 sí puede responder

- ¿Cuál es el costo estimado de la situación actual?
- ¿Cuánto cambia el costo frente a baseline?
- ¿Cuántos viajes cambian?
- ¿Qué diferencia de kilómetros existe?
- ¿Qué despachos cambian de vehículo?
- ¿Qué despachos explican los mayores cambios?
- ¿Qué trade-off existe entre costo y viajes?
- ¿La configuración personalizada cambia la solución frente al extremo de costo?
- ¿Qué ocurre en el extremo de viajes?

## Preguntas que requieren una versión posterior

- ¿Tengo suficientes camiones disponibles?
- ¿Se cumplen ventanas horarias reales?
- ¿Cómo consolido varios despachos en un mismo viaje?
- ¿Cuál es la mejor secuencia de paradas?
- ¿Qué efecto tiene el clima o el tránsito?
- ¿Cuál es el tiempo real de transporte?
- ¿Qué impacto tiene CO2?
- ¿Qué alternativa maximiza nivel de servicio?
