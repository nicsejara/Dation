# Contrato dispatch_v1
Estas reglas corresponden a logistics-dispatch-engine 1.1.0, que mantiene el envelope dispatch_v1 e incorpora flota espacial por pools.

La referencia principal es Despacho directo, una política declarada sin consolidación ni reprogramación. No es una operación verificada. Si no encuentra cobertura, no se muestran ahorros ejecutables contra ella.

Cada viaje tiene un origen, un destino, fecha, `fleet_pool_id`, base operativa, tipo de vehículo y cargas de unidades enteras. Las órdenes pueden dividirse. La llegada de una orden es su última entrega; el plazo medio pondera cada unidad por su llegada.

Ubicación: un pool sólo puede atender órdenes cuyo origen coincide con `base_location`. Un tercerizado con base `*` puede operar desde cualquier origen. `vehicle_type` no identifica de forma única un recurso: la identidad operacional es `fleet_pool_id`.

Disponibilidad: se limita por pool y día; todavía no se modela ocupación durante ida y retorno. La flota tercerizada puede ser ilimitada si así lo declara el dataset.

Costo: distancia de ida × 2 × costo por km + costo fijo. El combustible ya está incluido en costo/km. CO₂ y litros se calculan sobre ida y vuelta, con factores informados, no certificados.

Nunca llamar óptima a una solución feasible o heurística. Una búsqueda agotada no prueba inviabilidad. No inventar brecha cuando no existe cota verificable.

Las anomalías excluidas quedan registradas. La cobertura corresponde sólo a órdenes incluidas. Una orden tardía inevitable debe salir en su primera fecha disponible.

El intérprete no calcula ni altera asignaciones. La guardia de cifras comprueba presencia numérica, no la exactitud semántica de toda afirmación. La validación humana de la decisión recomendada sigue siendo necesaria.
