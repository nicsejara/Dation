# Sample data — Dispatch spatial fleet v2

Este fixture mantiene las 100 órdenes sintéticas del caso original, pero usa el contrato `orders_v2`: `ready_date` reemplaza a `dispatch_date` y no existe asignación de vehículo en órdenes.

La flota usa `fleet_v2` con pools por base operativa. La capacidad propia total se conserva en 11 vehículos y 167.000 kg por día, distribuida entre Cordoba, Buenos Aires y Rosario. El pool `TP-ALL-L` representa capacidad tercerizada habilitada desde cualquier origen mediante `base_location=*`.

Este fixture se usa para el botón de datos de ejemplo y para QA espacial/temporal. Desde el motor 1.2.0, los pools con disponibilidad finita permanecen ocupados durante el ciclo completo ida + retorno y cada viaje informa cuándo vuelve a quedar libre el recurso.
