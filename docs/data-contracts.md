# Contratos de datos — Logistics Data Pack V3

Dation Logística usa un **Data Pack progresivo** compuesto por dos CSV:

- `orders.csv` — demanda a transportar;
- `fleet.csv` — una fila por camión real, propio o tercerizado.

La plantilla descargable contiene el contrato completo para toda la cadena de decisiones, pero **no todas las columnas son obligatorias para comenzar**. Dation valida el núcleo mínimo y calcula **Decision Readiness** para explicar qué decisiones ya pueden ejecutarse y qué datos opcionales desbloquean capacidades posteriores.

La fuente ejecutable del contrato es `backend/app/validators/contracts.py`. `GET /api/dispatch/contracts`, las plantillas y la ayuda de la pantalla se derivan de esa definición.

## Reglas generales

Ambos archivos aceptan UTF-8 con BOM opcional, encabezado en la primera fila, separador `;` o `,` y hasta 10 MB. Las fechas aceptan `YYYY-MM-DD` o día/mes/año. La validación acumula hasta 100 problemas con código, fila, columna, mensaje y sugerencia.

Una columna **opcional** no se ignora: si está presente se valida, se perfila y puede habilitar una capacidad o una decisión posterior.

## orders.csv — orders_v3

### Núcleo requerido para Asignación

| Columna | Uso |
|---|---|
| `order_id` | Identificador único de la orden; acepta alias histórico `shipment_id` |
| `product` | Producto |
| `quantity_units` | Cantidad entera positiva |
| `unit_weight_kg` | Peso positivo por unidad |
| `origin` | Site de salida |
| `destination` | Ciudad destino, distinta del origen |
| `distance_km` | Distancia positiva de ida, consistente para la misma ruta |

La orden **no contiene un camión asignado**. La asignación es un resultado de Dation.

### Columnas opcionales para niveles posteriores

| Columna | Desbloquea |
|---|---|
| `estimated_dispatch_date` | Planificación; acepta temporalmente `ready_date` y `dispatch_date` como aliases |
| `priority` | Planificación avanzada |
| `delivery_due_date` | Evaluación de SLA durante Planificación |

Para la historia del MVP, el origen esperado es el site Córdoba y los destinos pueden ser ciudades de Córdoba o del resto del país. El contrato no codifica Córdoba como constante para no impedir futuras instalaciones multi-site.

## fleet.csv — fleet_v3

Fleet V3 elimina el concepto de pool de la experiencia y del archivo de usuario.

> **Una fila = un camión real.**

### Núcleo requerido para Asignación

| Columna | Uso |
|---|---|
| `vehicle_id` | Identificador único de la unidad física |
| `vehicle_type` | Tamaño/categoría logística |
| `ownership` | `own` o `third_party` |
| `base_site` | Site operativo |
| `capacity_kg` | Capacidad máxima por viaje |

### Columnas opcionales

| Columna | Desbloquea / aporta |
|---|---|
| `license_plate` | Asignación final a patente |
| `provider_name` | Detalle de proveedor tercerizado |
| `capacity_m3` | Restricción volumétrica futura |
| `cost_per_km`, `fixed_trip_cost` | Objetivo Costo |
| `fuel_l_per_100km` | Análisis de combustible |
| `co2_kg_per_km` | Objetivo CO₂ |
| `avg_speed_kmh`, `driving_hours_per_day` | Planificación |
| `status` | Disponibilidad operativa: `available`, `maintenance`, `unavailable` |
| `available_from`, `available_until` | Planificación y Asignación final |

Las patentes son opcionales para DDA 1. Si se informan, deben ser únicas. La flota propia debe declarar un `base_site` concreto.

## Decision Readiness

Al validar ambos archivos, `POST /api/runs/preflight` devuelve además:

```json
{
  "decision_readiness": {
    "data_pack": "logistics_data_pack_v1",
    "orders_schema": "orders_v3",
    "fleet_schema": "fleet_v3",
    "decisions": [
      {
        "id": "logistics_assignment",
        "level": 1,
        "state": "available",
        "data_ready": true
      },
      {
        "id": "logistics_scheduling",
        "level": 2,
        "state": "locked",
        "data_ready": false,
        "missing": []
      },
      {
        "id": "logistics_final_assignment",
        "level": 3,
        "state": "locked",
        "data_ready": false,
        "missing": []
      }
    ]
  }
}
```

### Nivel 1 — Asignación de carga

Se habilita con el núcleo requerido de Orders V3 y Fleet V3.

Capacidades adicionales:
- Menor cantidad de viajes: disponible con el núcleo.
- Priorizar flota propia: disponible con el núcleo.
- Optimizar costo: requiere `cost_per_km` y `fixed_trip_cost`.
- Optimizar CO₂: requiere `co2_kg_per_km`.

### Nivel 2 — Planificación

En Fase 2 permanece `locked` hasta que **Asignación de carga** quede `APPROVED`. Después pasa a `AVAILABLE` si están completos:
- `estimated_dispatch_date`;
- `avg_speed_kmh`;
- `driving_hours_per_day`;
- `status`;
- `available_from`.

`delivery_due_date` habilita además análisis de SLA.

### Nivel 3 — Asignación final

En Fase 2 permanece `locked` porque el motor de Planificación todavía no está implementado. La identificación física queda data-ready cuando `license_plate` está completa y, conceptualmente, sólo se habilitará después de una Planificación aprobada.

## Validar no es guardar

`POST /api/datasets/validate?dataset_type=orders|fleet` valida sin escribir en Supabase.

Además de errores y warnings devuelve:
- `schema`;
- `profile`;
- `completeness`;
- `preview`;
- `detected`;
- `suggested_label`.

`completeness` mide lo realmente informado por el usuario antes de aplicar cualquier compatibilidad interna.

## Compatibilidad histórica

Las nuevas plantillas sólo exponen V3.

Durante la transición:
- Orders V2 puede leerse mediante aliases y campos de compatibilidad;
- Fleet V1/V2 se expande en memoria a recursos unitarios;
- los pools históricos nunca se vuelven a exponer en las plantillas V3;
- el motor Dispatch 2.2 existente recibe temporalmente campos internos compatibles para no romper corridas mientras Assignment y Scheduling se separan.

Estos adaptadores son implementación transitoria, no parte del nuevo contrato de producto.

## Decision Case y lineage

Fase 2 introduce `decision_case_v1` en el workspace. El caso se identifica por las versiones seleccionadas de Orders y Fleet y conserva el estado de la cadena:

`AVAILABLE → RUNNING → REVIEW → APPROVED`.

Si cambia cualquiera de los dos datasets, se crea un caso nuevo y el anterior queda referenciado como `STALE`.

Al ejecutar Assignment, la corrida guarda `decision_case.case_id` y `decision_case.node_id` dentro de `configuration_json` y `result_json`. Esta metadata no participa del fingerprint matemático del solver.

## Persistencia

Fases 1 y 2 no requieren migración de Supabase:
- `datasets.schema_version` ya es texto;
- `datasets.profile_json` ya es JSONB;
- `decision_runs.configuration_json` y `result_json` aceptan metadata del Decision Case.

Los nuevos datasets se guardan con `orders_v3` o `fleet_v3`.

## API

| Endpoint | Uso |
|---|---|
| `GET /api/dispatch/contracts` | Contratos V3 |
| `GET /api/dispatch/templates/orders` | Plantilla Orders V3 completa |
| `GET /api/dispatch/templates/fleet` | Plantilla Fleet V3 completa |
| `POST /api/datasets/validate?dataset_type=...` | Validación local |
| `POST /api/datasets/upload?dataset_type=...` | Persistir dataset válido |
| `POST /api/runs/preflight` | Compatibilidad + Decision Readiness |
| `POST /api/datasets/load-sample` | Cargar `sample_data/v3` |

## Dataset de ejemplo

`sample_data/v3` representa un site Córdoba con:
- 30 órdenes hacia ciudades de Córdoba y del país;
- 8 camiones físicos;
- 5 propios;
- 3 tercerizados;
- costos, emisiones y datos temporales completos.

La muestra está intencionalmente completa para demostrar toda la lectura de Decision Readiness. Un usuario real puede comenzar con sólo las columnas mínimas.
