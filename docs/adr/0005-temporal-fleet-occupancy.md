# ADR 0005 — Ocupación temporal multiday de flota

Estado: implementado en la fase 3 de la transición a Dispatch v2.

## Contexto

Dispatch 1.1.0 ya asignaba cada viaje a un `fleet_pool_id` compatible con el origen, pero la disponibilidad seguía siendo diaria: una unidad utilizada en una salida volvía a aparecer disponible al día siguiente aunque el viaje y el retorno requirieran varios días.

Eso sobreestima la capacidad real y puede generar dobles asignaciones físicamente imposibles.

## Decisión

1. El motor se versiona como **1.2.0**.
2. La duración de tránsito de entrega continúa calculándose como:

   `ceil(distance_km / (avg_speed_kmh * driving_hours_per_day))`.

3. La ocupación del recurso se calcula sobre el ciclo completo ida + retorno:

   `cycle_days = max(1, ceil(2 * distance_km / (avg_speed_kmh * driving_hours_per_day)))`.

4. Un recurso finito queda ocupado desde `dispatch_date` inclusive hasta `resource_available_again` exclusive.
5. Cada viaje persiste:
   - `cycle_days`
   - `resource_available_again`
6. La heurística greedy mantiene un calendario de ocupación por `fleet_pool_id + día`.
7. CP-SAT crea intervalos opcionales de duración fija para cada slot de viaje y aplica una restricción acumulativa por pool con capacidad igual a `units_available`.
8. La validación final reconstruye la ocupación de todos los viajes y rechaza cualquier doble asignación temporal.
9. Los pools con `units_available = null` continúan tratándose como capacidad ilimitada y no necesitan restricción acumulativa.
10. El dashboard representa ocupación diaria, salidas, capacidad del pool y fecha de liberación del recurso.

## Interpretación de fechas

Si una salida ocurre el 1 de octubre y `cycle_days = 2`, la unidad está ocupada los días 1 y 2 y vuelve a estar disponible el 3 de octubre.

`arrival_date` representa la llegada al destino. `resource_available_again` representa el regreso operativo a base y no debe confundirse con la fecha de entrega.

## Compatibilidad

Las corridas históricas persistidas no se recalculan. El frontend mantiene fallback para viajes antiguos que no contienen `cycle_days` ni `resource_available_again`.

Reejecutar un input histórico con motor 1.2.0 puede producir una distribución distinta porque ahora se respeta la ocupación multiday.

## Supabase

No se requieren nuevas tablas ni columnas. Los campos temporales viven dentro de `decision_runs.result_json`, que ya es JSONB.

## Limitaciones deliberadas

El ciclo supone ida y retorno a la misma base. No se modelan todavía:
- reposicionamiento entre bases;
- encadenamiento de viajes desde el destino anterior;
- tiempos de carga y descarga;
- descanso detallado por conductor;
- ventanas horarias;
- multiparada.

Estas extensiones deben tratarse como decisiones de modelado separadas y no inferirse del calendario actual.
