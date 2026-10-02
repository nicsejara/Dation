# ADR 0004 — Fleet v2 y elegibilidad espacial por pool

Estado: implementado en la fase 2 de la transición a Dispatch v2.

## Contexto

El contrato histórico identificaba la flota mediante `vehicle_type` y asumía que todas las unidades podían atender cualquier origen. Esa simplificación deja de ser válida cuando la demanda sale de múltiples ciudades: tres `Truck_L` corporativos no equivalen a tres `Truck_L` disponibles simultáneamente en Córdoba, Rosario y Buenos Aires.

La fase temporal multiday todavía no está activa; por lo tanto esta decisión limita el alcance a identidad de recursos y ubicación.

## Decisión

1. La flota oficial adopta `fleet_v2`.
2. `fleet_pool_id` es la identidad operacional única del recurso.
3. `vehicle_type` pasa a ser un atributo y puede repetirse entre pools.
4. `base_location` define desde qué origen puede iniciar despachos un pool.
5. La flota propia requiere una base concreta.
6. Un pool `third_party` puede usar `base_location=*` sólo cuando represente capacidad disponible desde cualquier origen.
7. La comparación de ubicaciones ignora mayúsculas y diacríticos para evitar diferencias como `Cordoba` / `Córdoba`.
8. Greedy, validación del resultado y CP-SAT contabilizan disponibilidad mediante `fleet_pool_id + día`.
9. Un viaje persiste `fleet_pool_id`, `vehicle_type`, `ownership` y `base_location`.
10. El motor se versiona como 1.1.0. El envelope continúa siendo `dispatch_v1` porque todavía no se introdujo el nuevo modelo temporal ni el contrato final de salida V2.

## Compatibilidad

Los archivos `fleet_v1` existentes no se migran ni se reescriben. Durante validación se adaptan en memoria a pools sintéticos `LEGACY-<vehicle_type>` con `base_location=*`. Se emite `LEGACY_FLEET_GLOBAL_SCOPE` para dejar explícito que esa corrida no dispone de evidencia geográfica real.

Las corridas históricas persistidas permanecen inmutables.

## Supabase

No se agregan tablas ni columnas. `datasets.schema_version` ya acepta texto y puede registrar `fleet_v2`; `profile_json` almacena el perfil v3 con pools, bases y capacidad por base.

## Limitación deliberada

La disponibilidad sigue siendo diaria. Un vehículo utilizado hoy vuelve a estar disponible al día siguiente aunque el viaje/retorno dure más de un día. Esa limitación queda explícita en assumptions y será eliminada en la fase 3 mediante ocupación temporal de recursos.
