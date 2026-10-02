# ADR 0003 — Transición del contrato de órdenes hacia Dispatch v2

Estado: fase 1 implementada en código; no modifica todavía el solver temporal.

## Contexto

El contrato original pedía `dispatch_date` y permitía `current_vehicle_type` como referencia opcional. Esa semántica mezcla dos conceptos distintos: disponibilidad de la carga y decisión de despacho. Además, informar un tipo de vehículo en órdenes puede condicionar o sesgar una decisión que debe producir el optimizador.

La evolución completa de Dispatch v2 incorporará ubicación de flota, ocupación temporal de recursos, nuevos objetivos y SLA jerárquico. Esos cambios no se activan en esta fase para evitar que la interfaz prometa restricciones que el solver 1.x todavía no modela.

## Decisión de esta fase

1. El contrato público de órdenes pasa a `orders_v2`.
2. `ready_date` reemplaza a `dispatch_date` como campo canónico.
3. `dispatch_date` continúa aceptándose temporalmente como alias para archivos existentes.
4. `current_vehicle_type` y `vehicle_type` dejan de formar parte del contrato de órdenes.
5. Si esas columnas históricas aparecen, la validación puede marcarlas como extras pero se eliminan antes de entregar registros al motor. Por lo tanto no pueden generar una referencia de asignación ni influir en la solución.
6. Para mantener compatibilidad con Dispatch Engine 1.x, el normalizador genera internamente `dispatch_date = ready_date`. Esa clave es interna y desaparecerá cuando se active el solver temporal V2.
7. `fleet_v1` permanece sin cambios en esta fase. `base_location` y `fleet_pool_id` no se exponen aún porque el solver actual no los respetaría.

## Consecuencias

- Las plantillas nuevas de órdenes tienen 10 columnas, incluyen `ready_date` y no incluyen asignación histórica.
- Los CSV existentes con `dispatch_date` siguen siendo válidos.
- Las corridas nuevas dejan de producir el escenario opcional basado en `current_vehicle_type`.
- Las corridas históricas persistidas no se alteran.
- Supabase no requiere migración para esta fase: `datasets.schema_version` ya es texto y puede almacenar `orders_v2`.
- El resultado del motor continúa siendo `dispatch_v1` hasta que se implemente la fase temporal.

## Próxima fase

Introducir `fleet_v2` con `fleet_pool_id` y `base_location`, normalización geográfica y ocupación temporal real de la flota. Sólo entonces esos campos deben aparecer en las plantillas oficiales.
