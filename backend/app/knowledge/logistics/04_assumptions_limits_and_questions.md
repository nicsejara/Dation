# Logistics DDA — Supuestos, límites y preguntas

## Supuestos activos en engine v0.1

- Cada fila se procesa como un despacho independiente.
- No existe consolidación entre shipments.
- Todo viaje se modela como ida y vuelta.
- La distancia origen-destino provista es fija.
- Los tipos de vehículo observados en el dataset se consideran disponibles para cualquier despacho.
- No existe límite de cantidad de vehículos simultáneos.
- La capacidad se modela únicamente por peso.
- No se modelan volumen, dimensiones físicas ni compatibilidad de carga.
- No se modelan paradas múltiples.
- No se modelan rutas alternativas.
- No se modelan peajes por ruta como variable separada.
- No se modelan tiempos de conducción ni descansos.
- No se modelan ventanas horarias.
- No se modela clima.
- No se modela CO2.
- No se modela desgaste como objetivo independiente.

## Columnas presentes pero aún no utilizadas para optimizar

En v0.1, variables como `priority`, `max_delivery_days` y `dispatch_date` pueden existir en el dataset, pero no alteran la selección de vehículo.

No expliques una recomendación diciendo que fue causada por prioridad, fecha o plazo de entrega.

## Límite conceptual

Este engine todavía no es un Vehicle Routing Problem completo.

No determina:
- secuencia óptima de destinos,
- consolidación de cargas,
- rutas geográficas,
- utilización temporal de una flota limitada.

Es un motor de comparación de asignaciones de vehículo por despacho.

## Cuándo advertir al usuario

Mencioná límites cuando la pregunta dependa materialmente de ellos.

Ejemplos:

"¿Puedo ejecutar realmente esta alternativa mañana?"
→ No puede asegurarse sin disponibilidad de flota y restricciones operativas.

"¿Llegará a tiempo?"
→ v0.1 no usa tiempos de viaje ni ventanas de entrega.

"¿Por qué eligió ese camión por prioridad?"
→ prioridad todavía no participa de la función de decisión.

## Próximas variables de alto valor

Para evolucionar el DDA:

- disponibilidad real de flota,
- volumen/dimensiones,
- ventanas de entrega,
- tiempos de carga y descarga,
- costos de peaje,
- consolidación,
- múltiples depósitos,
- secuencia de paradas,
- restricciones comerciales,
- penalización por incumplimiento de SLA.

## Preguntas sugeridas al usuario

- ¿Qué cambia contra la operación actual?
- ¿Cuánto costo estimado se reduce y qué lo explica?
- ¿Qué trade-off existe entre costo y viajes?
- ¿Qué shipments generan la mayor diferencia?
- ¿Cuántos despachos cambian de vehículo?
- ¿Qué supuesto podría cambiar más esta recomendación?
- ¿Qué información faltaría para llevar esta recomendación a operación real?
