# Contratos de datos — dispatch_v1

Dos archivos UTF-8 (BOM opcional), con encabezado y separador `;` o `,`. Se recomiendan fechas ISO y decimal con punto. Con separador `;` también se admite coma decimal. Hasta tres decimales, magnitudes finitas de máximo 1.000.000.000. Campos obligatorios no vacíos; IDs únicos, sin encabezados duplicados ni filas desalineadas. Los mensajes indican fila y columna. Tamaño de carga máximo: 10 MB.

## orders.csv — orders_v1

| Columna | Contrato |
|---|---|
| `order_id` | Identificador único; alias `shipment_id` |
| `product` | Nombre del producto |
| `quantity_units` | Entero positivo; la unidad es indivisible |
| `unit_weight_kg` | Peso positivo por unidad, kg |
| `origin`, `destination` | Textos no vacíos, distintos |
| `distance_km` | Distancia positiva de ida; consistente para la misma ruta |
| `priority` | `High`, `Normal` o `Low` |
| `max_delivery_days` | Entero de 1 a 90 desde disponibilidad hasta entrega |
| `dispatch_date` | Fecha de disponibilidad ISO `YYYY-MM-DD` o explícitamente día/mes/año |
| `current_vehicle_type` | Opcional, exclusivamente para referencia; alias `vehicle_type` |

`10/1/2026` significa 10 de enero. No se infiere formato estadounidense. Preferí ISO para evitar confusión. Variaciones de peso para el mismo producto generan advertencia, no una normalización silenciosa. Columnas de resultado no alimentan el motor. Un archivo mezclado del formato anterior con tarifas/capacidades se rechaza y requiere conversión explícita.

```csv
order_id;product;quantity_units;unit_weight_kg;origin;destination;distance_km;priority;max_delivery_days;dispatch_date
A;Pallet;2;400;Origen;Destino;100;Normal;2;2026-10-01
```

## fleet.csv — fleet_v1

| Columna | Contrato |
|---|---|
| `vehicle_type` | Identificador único del tipo de camión |
| `ownership` | `own` o `third_party` |
| `capacity_kg` | Capacidad positiva |
| `cost_per_km`, `fixed_trip_cost` | No negativos, moneda homogénea para todo el archivo |
| `units_available` | Entero no negativo, obligatorio para propios; vacío solo en tercerizados = sin límite |
| `avg_speed_kmh` | Velocidad positiva |
| `driving_hours_per_day` | Entre 1 y 24 horas |
| `fuel_l_per_100km` | Litros por 100 km, no negativo |
| `co2_kg_per_km` | Factor informado por km, no negativo; no certificado |

```csv
vehicle_type;ownership;capacity_kg;cost_per_km;fixed_trip_cost;units_available;avg_speed_kmh;driving_hours_per_day;fuel_l_per_100km;co2_kg_per_km
Small;own;1000;1;10;1;100;10;20;0.5
External;third_party;1000;2;20;;100;10;20;0.5
```

## Validación conjunta

Errores: vehículo de referencia desconocido; ninguna flota habilitada; ninguna unidad entera cabe en vehículos disponibles. Advertencias: flota finita, al menos 21 viajes para una orden, tardanza inevitable. Anomalía de peso: carga mayor que 20 veces la mayor capacidad propia (o de flota habilitada si no hay propia). Requiere decisión explícita `include`/`exclude`, conservada en el resultado. Excluir no altera el archivo fuente; todos los escenarios usan el mismo universo incluido. Ausencia de plan encontrado no siempre prueba inviabilidad global.

## Configuración y API

`POST /api/runs` recibe `orders_dataset_id`, `fleet_dataset_id`, `configuration` y `options`. Los IDs son UUID. `?run_id=` permite recuperar una petición que continúa ejecutándose.

```json
{
  "orders_dataset_id": "00000000-0000-4000-8000-000000000001",
  "fleet_dataset_id": "00000000-0000-4000-8000-000000000002",
  "configuration": {
    "mode": "custom", "objective": "custom",
    "weights": {"cost": 0.4, "trips": 0.3, "time": 0.3}
  },
  "options": {"allow_third_party": true, "anomaly_decisions": {}, "sensitivity": true}
}
```

Presets: `min_cost` 1/0/0, `min_trips` 0/1/0, `min_time` 0/0/1, `balanced` tercios exactos. Pesos personalizados suman 1; configuraciones de dos pesos admiten `time=0`.

| Endpoint | Uso |
|---|---|
| `POST /api/datasets/upload?dataset_type=orders` o `fleet` | Multipart `file`, opcionales `label`, `parent_dataset_id` |
| `GET /api/datasets?type=orders` o `fleet` | Versiones disponibles |
| `GET /api/datasets/{id}/profile` | Perfil según tipo |
| `POST /api/datasets/{id}/default` | Marcar flota vigente |
| `POST /api/runs/preflight` | Ambos IDs, opcional `allow_third_party` |
| `POST /api/runs` | Ejecutar despacho nuevo |
| `GET /api/runs/{id}` | Resultado y etapa persistida |
| `GET /api/dispatch/status` | Disponibilidad de la migración |
| `GET /api/dispatch/templates/orders` o `fleet` | Ejemplos sintéticos |

Todos requieren la autenticación de la plataforma. Upload sin tipo y `POST /api/runs/{dataset_id}` conservan el contrato anterior. Conversor: `python scripts/convert_legacy_csv.py sample_data/InputData-LogisticsDDA.csv sample_data/v1/orders.csv`.

## Resultado

`schema_version=dispatch_v1`, motor 1.0.0, inputs versionados, configuración, reglas, anomalías, escenarios, sensibilidad y huella. Los viajes incluyen cargas enteras por orden, fechas, ruta, peso, utilización, costo, combustible y CO₂. Los estados del solver y la factibilidad de la referencia deben interpretarse antes de comparar ahorros. `result_fingerprint` identifica la parte determinística, no los metadatos de persistencia.
