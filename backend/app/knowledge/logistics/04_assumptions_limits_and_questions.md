# Logistics DDA — Supuestos, límites y preguntas

## Supuestos activos en engine v0.2

- Cada fila se procesa como un despacho independiente.
- No existe consolidación entre despachos.
- Todo viaje se modela como ida y regreso.
- La distancia origen-destino provista es fija.
- Los tipos de vehículo observados en el dataset se consideran disponibles para cualquier despacho.
- No existe límite de cantidad de vehículos simultáneos.
- La capacidad se modela únicamente por peso.
- No se modelan volumen, dimensiones físicas ni compatibilidad de carga.
- No se modelan paradas múltiples.
- No se modelan rutas alternativas.
- No se modelan peajes como variable separada.
- No se modelan tiempos de conducción ni descansos.
- No se modelan ventanas horarias.
- No se modela clima.
- No se modela CO2.
- No se modela desgaste como objetivo independiente.

## Variables presentes pero todavía no optimizables

`priority`, `max_delivery_days` y `dispatch_date` pueden existir en el dataset y utilizarse para describir contexto, pero no alteran la selección de vehículo en v0.2.

`max_delivery_days` no representa tiempo real de transporte.

No expliques una recomendación diciendo que fue causada por prioridad, fecha o plazo de entrega.

## Variables optimizables actuales

Sólo:

- costo,
- viajes.

No hables de tiempo, CO2, riesgo, servicio, utilización o desgaste como componentes del score actual.

## Límite conceptual

Este engine todavía no es un Vehicle Routing Problem completo.

No determina:

- secuencia óptima de destinos,
- consolidación de cargas,
- rutas geográficas,
- disponibilidad temporal de flota.

Es un motor de comparación de asignaciones de vehículo por despacho.

## Cuándo advertir al usuario

"¿Puedo ejecutar realmente esta alternativa mañana?"
→ No puede asegurarse sin disponibilidad de flota y restricciones operativas.

"¿Llegará a tiempo?"
→ v0.2 no calcula tiempos de viaje ni ventanas reales.

"¿Por qué eligió ese camión por prioridad?"
→ prioridad no participa de la función objetivo.

"¿Qué pasaría si priorizo CO2?"
→ esa dimensión todavía no tiene definición matemática ni fuente de datos en el engine.

## Preguntas sugeridas

- ¿Qué cambia frente a la situación actual?
- ¿Cuánto costo estimado se reduce y qué lo explica?
- ¿Qué trade-off existe entre costo y viajes?
- ¿Qué despachos generan la mayor diferencia?
- ¿La ponderación seleccionada cambia la solución frente a 100% costo?
- ¿Qué cambia frente a 100% viajes?
- ¿Qué supuesto podría cambiar la recomendación?
- ¿Qué información faltaría para llevar esta recomendación a operación real?
