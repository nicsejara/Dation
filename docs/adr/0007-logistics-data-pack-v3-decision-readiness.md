# ADR 0007 — Logistics Data Pack V3 y Decision Readiness

Estado: implementado en Fase 1 de la nueva Decision Chain.

## Contexto

El flujo Dispatch 2.x mezclaba en un mismo contrato datos necesarios para asignar carga, programar viajes y asignar recursos físicos. También exponía `fleet_pool_id`, una abstracción útil para el solver pero innecesaria para el usuario del MVP.

Dation necesita permitir que una empresa empiece con la información disponible y complete el Data Pack a medida que quiera resolver decisiones más profundas.

## Decisión

La ingesta logística se redefine como un **Data Pack progresivo** con sólo dos archivos:

- `orders_v3`
- `fleet_v3`

Las plantillas muestran el contrato completo, pero cada columna declara:
- si es requerida para comenzar;
- en qué decisión se utiliza;
- qué capacidad futura habilita.

Faltantes en columnas opcionales no son errores de calidad y no bloquean DDA 1.

## Orders V3

Núcleo mínimo:
- order_id
- product
- quantity_units
- unit_weight_kg
- origin
- destination
- distance_km

Campos temporales y de prioridad son opcionales y se reservan para Scheduling.

No se acepta ninguna asignación de camión como input de negocio.

## Fleet V3

Cada fila representa una unidad física real.

Núcleo mínimo:
- vehicle_id
- vehicle_type
- ownership
- base_site
- capacity_kg

Patente, proveedor, costos, CO₂ y disponibilidad son enriquecimientos progresivos.

`fleet_pool_id` y `units_available` desaparecen del contrato público.

## Decision Readiness

Luego de validar el Data Pack, el backend calcula capacidad de decisión de forma determinística.

Estados iniciales de Fase 1:
- Assignment: AVAILABLE cuando ambos núcleos son válidos;
- Scheduling: LOCKED, aunque puede estar data-ready;
- Final Assignment: LOCKED, aunque puede estar data-ready.

En Fase 2 los estados dependerán además de Decision Cases y aprobación upstream.

## Compatibilidad transitoria

El motor Dispatch 2.2 todavía necesita estructuras espaciales y temporales anteriores. Para evitar una migración big-bang:

- cada Fleet V3 unitario se adapta internamente como un recurso finito de una unidad;
- campos temporales ausentes reciben defaults internos neutrales;
- esos campos no forman parte del Data Pack público ni de Decision Readiness;
- Fleet V1/V2 histórico sigue siendo legible mediante adaptadores en memoria.

La compatibilidad se eliminará cuando Assignment y Scheduling estén separados en motores distintos.

## Persistencia

No se agrega migración en esta fase porque `datasets.schema_version` es texto y `profile_json` JSONB.

## Consecuencias

Ventajas:
- menor barrera de entrada;
- plantilla única para toda la cadena;
- no obliga a reunir información que todavía no interviene;
- hace visible el valor progresivo de enriquecer datos;
- elimina pools de la UX;
- prepara lineage sin reescribir el motor actual.

Limitaciones temporales:
- después de Cargar datos el flujo todavía continúa al configurador Dispatch existente;
- Decision Map, aprobación y unlock real llegan en Fase 2;
- Assignment todavía no está separado matemáticamente del Scheduling hasta Fase 3.
