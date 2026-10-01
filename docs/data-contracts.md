# Contratos de datos — dispatch_v1

La ingesta nueva usa dos archivos CSV separados: **órdenes** y **flota**. Ambos aceptan UTF-8 con BOM opcional, encabezado en la primera fila, separador `;' o `,`, hasta 10 MB. Se recomiendan fechas ISO y decimales con punto; con separador punto y coma también se admite coma decimal. La validación informa hasta 100 problemas con código, fila, columna, mensaje y sugerencia.

La fuente ejecutable de estos contratos es `backend/app/validators/contracts.py`. El endpoint `GET /api/dispatch/contracts`, la ayuda de la pantalla y las plantillas descargables se derivan de esa definición. Los archivos `sample_data/v1/orders.csv` y `fleet.csv` se mantienen como fixtures completos y los tests verifican que sigan validando.

## orders.csv — orders_v1

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
| `dispatch_date` | `YYYY-MM-DD` o día/mes/año |
| `current_vehicle_type` | Opcional; referencia informada, alias `vehicle_type` |

`10/1/2026` significa 10 de enero. No se infiere formato estadounidense. Una variación de peso para el mismo producto es advertencia; no se normaliza ni corrige en silencio. Un CSV del formato histórico mezclado se detecta como `legacy_mixed` y la interfaz explica que debe separarse en órdenes y flota.

## fleet.csv — fleet_v1

| Columna | Contrato |
|---|---|
| `vehicle_type` | Identificador único del tipo de camión |
| `ownership` | `own` o `third_party` |
| `capacity_kg` | Capacidad positiva |
| `cost_per_km`, `fixed_trip_cost` | Valores no negativos |
| `units_available` | Entero no negativo para propios; vacío en tercerizados = sin límite |
| `avg_speed_kmh` | Velocidad positiva |
| `driving_hours_per_day` | Entre 1 y 24 |
| `fuel_l_per_100km` | No negativo |
| `co2_kg_per_km` | No negativo; informativo y no certificado |

## Validar no es guardar

`POST /api/datasets/validate?dataset_type=orders|fleet` valida el multipart `file` sin leer ni escribir Supabase. Por eso funciona aun cuando las migraciones de persistencia todavía no estén activadas.

Respuesta resumida:

```json
{
  "valid": false,
  "detected_format": "orders_v1",
  "file": {"name": "orders.csv", "size_bytes": 8600, "sha256": "..."},
  "rows": 100,
  "columns": 11,
  "profile": null,
  "errors": [
    {
      "code": "INVALID_DATE",
      "row": 15,
      "column": "dispatch_date",
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

Cuando ambos datasets válidos ya están guardados, `POST /api/runs/preflight` verifica compatibilidad cruzada: referencias de camión, capacidad por unidad, disponibilidad y plazos. Los errores bloquean; las advertencias permiten continuar; las anomalías requieren una decisión explícita posterior.

## Biblioteca y versionado

Las cargas `orders` y `fleet` se listan por separado. La biblioteca admite búsqueda, paginación por `limit/offset`, archivado lógico y reutilización. Una flota vigente no puede archivarse hasta marcar otra versión como vigente. Un archivo idéntico reutiliza la fila existente por `(dataset_type, sha256)`.

## API de ingesta

| Endpoint | Uso |
|---|---|
| `GET /api/dispatch/contracts` | Contratos y reglas de archivo |
| `POST /api/datasets/validate?dataset_type=...` | Validación sin persistencia |
| `GET /api/dispatch/templates/orders` o `fleet` | Plantilla generada desde el contrato |
| `GET /api/dispatch/examples/orders` o `fleet` | Fixture sintético completo |
| `POST /api/datasets/upload?dataset_type=...` | Guardar un archivo ya válido |
| `GET /api/datasets?type=...&q=...&limit=...&offset=...` | Biblioteca activa |
| `POST /api/datasets/{id}/archive` | Archivar lógicamente |
| `POST /api/datasets/{id}/unarchive` | Recuperar un archivado |
| `POST /api/datasets/{id}/default` | Marcar flota vigente |
| `POST /api/runs/preflight` | Validación cruzada |
| `POST /api/runs` | Ejecutar Dispatch v1 |
| `GET /api/dispatch/status` | Diagnóstico de activación |

Todos requieren la autenticación de la plataforma. El upload sin `dataset_type` y `POST /api/runs/{dataset_id}` se preservan para compatibilidad histórica.

## Resultado

`schema_version=dispatch_v1`, motor 1.0.0, inputs versionados, configuración, reglas, anomalías, escenarios, sensibilidad y huella. El `result_fingerprint` identifica la parte determinística, no metadatos de persistencia.
