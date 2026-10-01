# Contrato dispatch_v1
Estas reglas corresponden exclusivamente a logistics-dispatch-engine 1.0.0.
La referencia principal es Despacho directo, una política declarada sin consolidación ni reprogramación. No es una operación verificada. Si no encuentra cobertura, no se muestran ahorros ejecutables contra ella.
Cada viaje tiene un origen, un destino, fecha, tipo de camión y cargas de unidades enteras. Las órdenes pueden dividirse. La llegada de una orden es su última entrega; el plazo medio pondera cada unidad por su llegada.
Disponibilidad: salidas por tipo y día; no se modela ocupación durante ida y retorno. La flota tercerizada puede ser ilimitada si así lo declara el dataset.
Costo: distancia de ida × 2 × costo por km + costo fijo. El combustible ya está incluido en costo/km. CO₂ y litros se calculan sobre ida y vuelta, con factores informados, no certificados.
Nunca llamar óptimo a un plan feasible o heurístico. Una búsqueda agotada no prueba inviabilidad. No inventar brecha cuando no existe cota verificable.
Las anomalías excluidas quedan registradas. La cobertura corresponde solo a órdenes incluidas. Una orden tardía inevitable debe salir en su primera fecha disponible.
El intérprete no calcula ni altera asignaciones. La guardia de cifras comprueba presencia numérica, no la exactitud semántica de toda afirmación. La validación humana del plan sigue siendo necesaria.
