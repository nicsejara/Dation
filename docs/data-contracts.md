# Contratos de datos — transición Dispatch v2

La ingesta usa dos archivos CSV separados: **órdenes** y **flota**. Órdenes usa **orders_v2** y flota usa **fleet_v2** con pools y base operativa. Desde Dispatch Engine **2.2.0**, las corridas nuevas producen el envelope **dispatch_v2**, con capacidad espacial/temporal y SLA jerárquico. Ambos archivos aceptan UTF-8 con BOM opcional, encabezado en la primera fila, separador `;` o `,`, hasta 10 MB. Se recomiendan fechas ISO y decimales con punto; con separador punto y coma también se admite coma decimal. La validación informa hasta 100 problemas con código, fila, columna, mensaje y sugerencia.

La fuente ejecutable de estos contratos es `backend/app/validators/contracts.py`. El endpoint `GET /api/dispatch/contracts`, la ayuda de la pantalla y las plantillas descargables se derivan de esa definición. Cada plantilla incluye exactamente 5 registros de ejemplo válidos y funciona como template y ejemplo a la vez. Los archivos `sample_data/v1/orders.csv` y `fleet.csv` se mantienen sólo como fixtures internos de QA.

## orders.csv — orders_v2

| Columna | Contrato |
|---|---|
| `order_id` | Identificador único; alias `shipment_id` |
| `product` | Nombre del producto |
| `quantity_units` | Entero positivo; cada unidad es indivisible |
| `unit_weight_kg` | Peso positivo por unidad, kg |
| `origin`, `destination` | Textos no vacíos y distintos |
| `distance_km` | Distancia positiva de ida; consistente para la misma ruta |
| `priority` | `High`, `Normal` o `Low` |
| `max_delivery_days` | Entero de 1 a 90 |
| `ready_date` | Primera fecha en la que la carga está disponible; `YYYY-MM-DD` o día/mes/año |

`dispatch_date` se acepta temporalmente como alias de `ready_date` para archivos ya existentes. `current_vehicle_type` y `vehicle_type` ya no forman parte del contrato de órdenes: si aparecen en un archivo histórico se informan como columnas extra y se eliminan antes de ejecutar el motor, por lo que no pueden condicionar la decisión. `10/1/2026` significa 10 de enero. No se infiere formato estadounidense. Una variación de peso para el mismo producto es advertencia; no se normaliza ni corrige en silencio. Un CSV del formato histórico mezclado se detecta como `legacy_mixed` y la interfaz explica que debe separarse en órdenes y flota.

## fleet.csv — fleet_v2

| Columna | Contrato |
|---|---|
| `fleet_pool_id` | Identificador único del pool de flota |
| `vehicle_type` | Tipo de vehículo; puede repetirse entre pools |
| `ownership` | `own` o `third_party` |
| `base_location` | Base desde la que puede iniciar el despacho; `*` sólo para tercerizados disponibles desde cualquier origen |
| `capacity_kg` | Capacidad positiva por viaje |
| `cost_per_km`, `fixed_trip_cost` | Valores no negativos |
| `units_available` | Entero no negativo para propios; vacío en tercerizados = sin límite |
| `avg_speed_kmh` | Velocidad positiva |
| `driving_hours_per_day` | Entre 1 y 24 |
| `fuel_l_per_100km` | No negativo |
| `co2_kg_per_km` | No negativo; informativo y no certificado |

Un mismo `vehicle_type` puede existir en varias bases porque la identidad operacional es `fleet_pool_id`. La flota propia debe informar una ubicación concreta. Un pool tercerizado puede usar `base_location=*` cuando el proveedor realmente puede despachar desde cualquier origen.

Los archivos `fleet_v1` históricos siguen siendo ejecutables. Al no contener ubicación, se adaptan sólo en memoria con un pool sintético por tipo y alcance global `*`; la validación devuelve la advertencia `LEGACY_FLEET_GLOBAL_SCOPE`. Esta compatibilidad evita romper corridas antiguas, pero no debe usarse para representar una flota real cuando la ubicación importa.

## Validar no es guardar

`POST /api/datasets/validate?dataset_type=orders|fleet` valida el multipart `file` sin leer ni escribir Supabase. Por eso funciona aun cuando las migraciones de persistencia todavía no estén activadas.

Respuesta resumida:

```json
{
  "valid": false,
  "detected_format": "orders_v2",
  "file": {"name": "orders.csv", "size_bytes": 8600, "sha256": "..."},
  "rows": 100,
  "columns": 11,
  "profile": null,
  "errors": [
    {
      "code": "INVALID_DATE",
      "row": 15,
      "column": "ready_date",
      "message": "La fecha no es válida.",
      "hint": "Usá AAAA-MM-DD o d/m/AAAA."
    }
  ],
  "warnings": [],
  "counts": {"errors": 1, "warnings": 0},
  "truncated": false
}
```

Los consumidores estrictos del motor continúan usando `validate_orders_csv` y `validate_fleet_csv`: si existe un error, esos wrappers lanzan el primer problema y nunca entregan registros parcialmente válidos.

## Validación conjunta

Cuando ambos datasets válidos ya están guardados, `POST /api/runs/preflight` verifica compatibilidad cruzada: cobertura de flota por origen, capacidad por unidad, disponibilidad y plazos. Las columnas históricas de asignación de vehículo no participan de esta verificación. Los errores bloquean; las advertencias permiten continuar; las anomalías requieren una decisión explícita posterior.

## Biblioteca y versionado

Las cargas `orders` y `fleet` se listan por separado. La biblioteca admite búsqueda, paginación por `limit/offset`, archivado lógico y reutilización. Una flota vigente no puede archivarse hasta marcar otra versión como vigente. Un archivo idéntico reutiliza la fila existente por `(dataset_type, sha256)`.

## API de ingesta

| Endpoint | Uso |
|---|---|
| `GET /api/dispatch/contracts` | Contratos y reglas de archivo |
| `POST /api/datasets/validate?dataset_type=...` | Validación sin persistencia |
| `GET /api/dispatch/templates/orders` o `fleet` | Plantilla con 5 registros de ejemplo |
| `POST /api/datasets/upload?dataset_type=...` | Guardar un archivo ya válido |
| `GET /api/datasets?type=...&q=...&limit=...&offset=...` | Biblioteca activa |
| `POST /api/datasets/{id}/archive` | Archivar lógicamente |
| `POST /api/datasets/{id}/unarchive` | Recuperar un archivado |
| `POST /api/datasets/{id}/default` | Marcar flota vigente |
| `POST /api/runs/preflight` | Validación cruzada |
| `POST /api/runs` | Ejecutar Dispatch v2 |
| `GET /api/dispatch/status` | Diagnóstico de activación |

Todos requieren la autenticación de la plataforma. El upload sin `dataset_type` y `POST /api/runs/{dataset_id}` se preservan para compatibilidad histórica.

## Resultado

`schema_version=dispatch_v2` usa motor **2.2.0**. El SLA se resuelve antes que el objetivo de negocio: primero se minimizan órdenes tardías y luego días de tardanza ponderados por prioridad. Después se optimiza costo, tiempo, participación de flota propia, CO₂ o una ponderación personalizada. Viajes permanece como KPI y desempate. Cada resultado incluye `decision`, `feasibility`, `decision_drivers`, `exceptions`, escenarios comparables y la `Distribución recomendada`. Cada viaje conserva `cycle_days` y `resource_available_again`. El `result_fingerprint` identifica la parte determinística, no metadatos de persistencia.


## UX de ingesta v2

La validación devuelve además perfiles versionados, `preview`, `detected` y
`suggested_label`. Para órdenes, el perfil incluye orígenes, destinos, peso máximo,
mezcla de prioridades, rango de plazos y demanda diaria. Para flota, el perfil v3 incluye pools, tipos, bases, capacidad por base, unidades propias y presencia de tercerizados.

El preflight conserva `errors`, `warnings` y `anomalies`, y agrega:
`findings` agrupados en lenguaje de negocio, `capacity_check` para demanda versus
capacidad propia y `readiness` para decidir si la pantalla puede avanzar.

`POST /api/datasets/load-sample` carga o reutiliza por hash los fixtures de
`sample_data/v2`. `GET /api/datasets/{id}/download` permite descargar un input
guardado y `PATCH /api/datasets/{id}` actualiza su etiqueta.


## Alcance de validación en Cargar datos

La pantalla **Cargar datos** muestra únicamente calidad técnica del archivo y compatibilidad
mínima entre inputs. No presenta plazos, capacidad operativa, costos, viajes, utilización,
emisiones, consolidación ni resultados potenciales del optimizador. Esos datos pueden seguir existiendo en el preflight por compatibilidad, pero no se muestran como alertas durante **Configurar decisión**; las excepciones operativas pertenecen al resultado.

Las columnas históricas `current_vehicle_type` o `vehicle_type` pueden generar una advertencia
de columna extra, pero no bloquean la carga y se descartan antes del motor. La asignación de
vehículo será responsabilidad exclusiva de la decisión generada.


## Contrato de decisión — dispatch_v2

Las dimensiones configurables son `cost`, `time`, `utilization` y `co2`. Al menos una debe permanecer activa. En modo personalizado, las dimensiones inactivas tienen peso 0 y los pesos activos deben sumar 1. En modo `balanced`, el motor reparte el peso por igual entre las dimensiones activas. `max_utilization` significa minimizar la participación de kg tercerizados, mientras `own_load_utilization` se conserva como KPI complementario.

El horizonte de recuperación tardía está acotado por `max_late_days` (30 días por defecto). Si una distribución completa existe dentro de ese horizonte, el motor puede devolver `recommended_with_exceptions` en lugar de declarar inviabilidad.

La profundidad `essential` resuelve sólo los escenarios necesarios para la decisión elegida; `comparative` agrega los extremos de las dimensiones activas y una referencia balanceada; `deep` agrega además sensibilidad. La referencia `baseline_direct` es una política declarada y no representa una operación real verificada.

## Dashboard de decisión 2.2

La vista principal ya no presenta `baseline_direct` como ahorro. Esa referencia es sintética y sólo sirve para análisis de escenarios. El recorrido principal muestra la Decisión recomendada, la asignación de carga por pool, excepciones que requieren revisión e interpretación IA bajo demanda. Cada `load` de una corrida 2.2 incluye `product` para poder auditar qué productos y órdenes transporta cada pool.
