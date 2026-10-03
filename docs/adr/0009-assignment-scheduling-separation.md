# ADR 0009 — Separación de Assignment y Scheduling

Estado: implementado en Fase 3.

## Contexto

Dispatch 2.2 resolvía simultáneamente dos preguntas distintas: cómo distribuir la carga y cuándo ejecutar cada viaje. Esa combinación era demasiado amplia para el MVP y hacía que el primer DDA dependiera de fechas, SLA y ocupación temporal aunque el negocio sólo quisiera decidir asignación.

## Decisión

Dation separa el primer nodo de la Decision Chain en un motor propio:

- engine: `logistics-assignment-engine`;
- version: `1.0.0`;
- result schema: `assignment_v1`;
- handoff schema: `scheduling_input_v1`.

Dispatch 2.2 queda disponible para corridas históricas, pero deja de ser el motor de nuevas ejecuciones de `logistics_assignment`.

## Scope de Assignment

Assignment responde: **cómo construir viajes y distribuir carga entre vehículos habilitados**.

Restricciones incluidas:
- unidades enteras;
- conservación de demanda;
- capacidad por viaje;
- compatibilidad origen/site;
- ruta origen-destino;
- estado operativo actual si está informado.

Fuera de scope:
- fecha de salida;
- fecha de llegada;
- SLA;
- tardanzas;
- velocidad;
- horas de conducción;
- duración del ciclo;
- ocupación temporal;
- disponibilidad futura.

## Semántica de recursos

`fleet_v3` mantiene una fila por vehículo real y Assignment usa `vehicle_id` como recurso. Un vehículo puede recibir más de un viaje abstracto. Esto no significa que pueda ejecutarlos simultáneamente: Scheduling deberá secuenciarlos y verificar conflictos temporales.

## Objetivos

Assignment soporta:
- `min_trips`;
- `min_cost`;
- `max_own_fleet`;
- `min_co2`;
- `balanced`;
- `custom`.

Viajes y uso de flota propia están disponibles con el core mínimo. Costo y CO₂ sólo pueden activarse con evidencia completa para esas dimensiones.

## Modelo

El motor construye candidatos heurísticos determinísticos y, cuando el tamaño lo permite, un modelo OR-Tools CP-SAT. El CP-SAT no crea intervalos temporales ni restricciones cumulative. Cada slot representa un viaje abstracto de una ruta y un `vehicle_id`.

Cada plan se valida antes de publicarse. Sólo puede llamarse óptimo cuando el solver lo certifica.

## Handoff

El resultado seleccionado expone:

`handoff.source_path = scenarios.selected.trips`

junto con fingerprint, trip count e IDs. Ese contrato será el input del motor Scheduling.

## Compatibilidad

- `dispatch_v1` y `dispatch_v2` siguen siendo legibles;
- una corrida histórica temporal no puede aprobar un Assignment nuevo;
- el frontend restaura ambos contratos;
- la IA usa contexto schema-aware y no atribuye fechas/SLA a Assignment.

## Persistencia

No se agregan tablas ni columnas. `decision_runs.schema_version` es texto y `configuration_json` / `result_json` son JSONB.

La API y el servicio validan que las corridas nuevas de Assignment usen Orders + Fleet y el modelo de configuración Assignment. El trigger histórico de integridad continúa cubriendo `dispatch_v1/dispatch_v2`.

## Consecuencia

La Decision Chain pasa a tener una frontera real de motores: Assignment produce evidencia aprobable y Scheduling podrá desarrollarse después consumiendo exactamente esa evidencia, sin recalcular cómo se armó la carga.
