# ADR 0001 — Plan de despachos con flota versionada

Estado: diseño aprobado por el usuario; implementación lista para activar tras migración manual.

## Decisión

Separar demanda y recursos. Una orden puede dividirse en unidades enteras; varias órdenes pueden compartir un viaje si coinciden origen, destino, día y tipo de vehículo. No se divide una unidad: con unidades de 600 kg y capacidad de 1.000 kg, tres unidades requieren tres viajes, no dos.

El problema es una asignación temporal con consolidación y disponibilidad diaria. Se usa OR-Tools CP-SAT, con candidatos heurísticos determinísticos validados como respaldo. No se usa el vehículo histórico como objetivo ni como regla de decisión: `current_vehicle_type` es exclusivamente una referencia opcional.

## Fórmulas y restricciones

- Peso de orden = cantidad × peso unitario. Capacidad individual = floor(capacidad / peso unitario).
- Tránsito en días = ceil(distancia / (velocidad × horas de conducción por día)).
- Plazo final = fecha de disponibilidad + días máximos de entrega.
- Si algún vehículo habilitado llega a tiempo, solo se permiten salidas y vehículos que cumplan el plazo. Si todos llegan tarde, se obliga a salir el primer día; la tardanza se declara inevitable.
- La entrega completa de una orden corresponde a su última llegada. El plazo medio se pondera por unidades, no por viajes.
- La disponibilidad de flota limita salidas por día y tipo. No representa ocupación del vehículo durante la ida/vuelta. Tercerizados con disponibilidad vacía son ilimitados; deshabilitarlos excluye sus viajes.
- Costo por viaje = 2 × distancia × costo por km + costo fijo. No se agrega combustible al costo porque ya está incluido en la tarifa por km.
- Combustible = 2 × distancia × litros/100 km / 100. CO₂ = 2 × distancia × factor informado por km. Son indicadores, no objetivos ni valores certificados.
- Se suman valores monetarios exactos con Decimal antes de redondear cada total final, con ROUND_HALF_UP a dos decimales. Los importes por viaje se presentan redondeados aparte; con tarifas de tres decimales su suma visual puede diferir por centavos del total agregado. No se redondea cada unidad ni se vuelve a sumar un importe ya redondeado.

## Referencias y prioridades

Despacho directo: sin consolidación ni reprogramación; prioriza flota propia y el menor camión que permite cubrir la carga en el menor número de viajes. Si no alcanza la flota, la referencia se marca no factible y no se presenta ahorro ejecutable contra ella. No representa la operación real observada.

Asignación informada: opcional si todas las órdenes tienen un vehículo de referencia conocido. Respeta disponibilidad; puede resultar no factible. Una referencia tercerizada conocida sigue siendo válida como dato aunque se deshabilite tercerizar el plan.

Costo, viajes y plazo se normalizan con los mejores extremos factibles conocidos. Escala = máximo entre diferencia referencia−mejor, rango entre escenarios, 1 % del mejor absoluto y 1. El piso evita divisiones nulas. Restar el mejor es una constante y no altera el argmin, por eso el score usa métrica/escala. Solo se llama óptimo al estado certificado por CP-SAT; las escalas no se presentan como óptimos exactos cuando no lo son.

La selección ponderada incorpora la referencia factible como candidata, para no empeorar su objetivo. Los extremos de pesos reutilizan exactamente sus escenarios. Entre candidatos empatados se ordena por costo, viajes y firma estructural. La heurística procesa plazo, prioridad, carga e ID; prioridad no modifica fechas ni vuelve factible una entrega imposible. CP-SAT usa orden estable, un hilo y seed fijo; no implementa una segunda optimización lexicográfica exhaustiva dentro del conjunto de óptimos equivalentes.

## Alternativas y límites

Se descartó seguir comparando camiones por fila: no modelaba consolidación ni disponibilidad. Se descartó un VRP geográfico porque faltan coordenadas, horarios y recorridos. Se rechazó el ceil simple de peso/capacidad porque puede dividir unidades físicas. Para 1.000 órdenes se prioriza una solución determinística válida en el presupuesto; no se promete óptimo global.

La flota de ejemplo es sintética: 4 pequeños, 4 medianos y 3 grandes, capacidad agregada propia 167.000 kg/día. La demanda original suma 2.384.000 kg en 10 días, por lo que reprogramación y tercerización tienen sentido. No es una calibración de operación real. La ruta, distancia y fechas se preservaron; combustible/emisiones y recargo tercerizado son supuestos explícitos del ejemplo.
