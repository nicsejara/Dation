# Fase 7: observabilidad y auditoría del intérprete

Cada solicitud recibe `X-Request-ID` y `traceparent`, también en respuestas 401,
422 y 500. Se aceptan únicamente UUID y contextos de traza válidos. La admisión
conserva esa identidad en la cola sin incorporarla al fingerprint de intención;
el worker la recupera al reclamar el trabajo. Corridas históricas sin contexto
reciben una traza nueva al ejecutarse, sin inventar una identidad anterior.

Los procesos API y worker escriben JSON en stdout para Cloud Logging. Los eventos
identifican admisión, replay, claim, etapas, finalización, fencing, dependencias y
reconciliación. Incluyen revisión, request/run/case, intento, latencia, resultado y
tipo de error. Una lista permitida excluye mensajes libres, cuerpos, consultas,
URLs, archivos, prompts, claves y textos de excepciones. Los histogramas usan
rutas registradas y categorías acotadas; nunca UUID como etiquetas.

## Diagnóstico privado

| Endpoint | Alcance |
| --- | --- |
| `/health` | Liveness pública; conserva el contrato anterior. |
| `/ready` | Basic del workspace; DB operativa y al menos un worker sano reportado en los últimos 90 s. Devuelve 503 cuando faltan. |
| `/api/system/operations` | Basic; agregados de cola, leases, reintentos, reconciliación, workers y corridas/IA de las últimas 24 h. Lectura SQL STABLE sin mantenimiento ni reparación. |
| `/metrics` | Basic; contadores e histogramas de este proceso API y gauges de la base compartida. |
| Worker `/ready`, `/metrics` | IAM privado de Cloud Run; disponibilidad y métricas de ese proceso worker. Su raíz conserva liveness para el probe de arranque. |

El worker registra su UUID de proceso y revisión al arrancar y cada 15 s, incluso
mientras trabaja el solver. El cierre ordenado publica indisponibilidad. Una
muerte abrupta vence por antigüedad; no se interpreta el último heartbeat como
salud indefinida. Los registros mayores de 24 h se eliminan al reportar.

El diagnóstico identifica falta de DB/worker, cola sin consumidor, espera mayor
de 30 s, leases/deadlines vencidos y reconciliación pendiente mayor de 60 s.
Las advertencias de negocio no fuerzan reinicios de un proceso vivo. El p95 de
corridas se calcula sobre `duration_ms` persistido de completadas de las últimas
24 h; si no hay muestras es null, no cero. No equivale al p95 HTTP.

Los histogramas son por instancia y se reinician con el proceso. Para un p95
HTTP global usar la métrica de latencia de Cloud Run, o agregar buckets de todas
las instancias con un scraper autenticado. Los gauges de SQL ya representan la
cola compartida. Se entregan condiciones y endpoints de alertas; esta fase no
crea políticas de notificación ni atribuye a un scraper externo una instalación
que no existe.

## Chat fiable

El proveedor comparte el pool HTTP con credenciales por solicitud. El deadline
es 60 s incluyendo un único reintento de 429 y una espera máxima de 5 s; todo el
turno, incluyendo lectura y persistencia, tiene un límite de 90 s. Un timeout
responde 504. La UI conserva `turn_id` si se pierde la respuesta.

Un RPC guarda pregunta, respuesta y auditoría en una transacción: proveedor,
modelo, versiones de conocimiento/prompt, token counts permitidos y request ID.
Repetir un turno ya guardado devuelve su respuesta sin llamar al proveedor.
Otra pregunta/corrida con el mismo UUID produce conflicto. Dos llamadas
simultáneas pueden consumir dos respuestas del proveedor antes de que una se
registre; la base conserva un solo par y devuelve la respuesta ganadora. No se
promete facturación exactamente una vez. Los mensajes antiguos conservan
`turn_id` null, sin inventar uso o versiones.

El historial abre los últimos 50 mensajes en orden cronológico; acepta `limit`
1–100 y `offset`. “Ver mensajes anteriores” añade páginas anteriores y elimina
solapamientos por ID. Navegar cancela solicitudes y evita renderizar en otra
pantalla. El polling de Assignment/Scheduling comienza después del 202; si se
pierde esa respuesta, recupera el UUID con la ventana de gracia existente.

## Operación y publicación

Desde la raíz, después de ejecutar las suites y con el token administrativo en
el entorno seguro:

```bash
python scripts/apply_production_observability.py
```

La migración `20261010233000_operational_observability.sql` es aditiva y atómica.
El instalador compara funciones, columnas, índices, constraints, RLS y permisos
contra el manifiesto generado en PostgreSQL 17 aislado. Repetirla verifica sin
escribir; un catálogo parcial o modificado detiene la publicación. Aplicar antes
de desplegar el worker y luego la API. No modifica resultados ni aprobaciones.

Consultar Cloud Logging en el proyecto `dation-510100`, por ejemplo:

```text
resource.type="cloud_run_revision"
(resource.labels.service_name="dation-core" OR resource.labels.service_name="dation-core-worker")
jsonPayload.request_id="UUID de X-Request-ID"
```

Cambiar el último filtro por `jsonPayload.run_id`, `jsonPayload.case_id` o
`jsonPayload.event="dispatch_dependency_unavailable"`. Priorizar disponibilidad,
queue wait, intentos, terminal errors y outbox; revisar dependencia y revisión
antes de reintentar. Un replay conserva el UUID y el resultado. No liberar leases
ni reaprobar históricos manualmente para resolver una alerta.

Rollback: devolver API y worker a sus revisiones previas; dejar tablas/columnas
aditivas instaladas. No borrar turnos ni evidencia. El worker anterior no reporta
la nueva disponibilidad: el diagnóstico indicará ese hecho durante el rollback.
La retención de logs sigue la configuración del bucket existente de Cloud
Logging; no se cambia ni se promete un plazo nuevo.

## Validación

Las nuevas regresiones cubren contexto paralelo, encabezados inválidos y errores,
privacidad, transporte/cancelación, deadlines y cooldown, replay sin proveedor,
persistencia atómica, historial reciente, SQL concurrente/rollback/permisos y
heartbeat vencido. El E2E real confirma la misma traza en API y worker, readiness,
p95 almacenado y métricas privadas. Chromium verifica reintento con el mismo
turno, historial anterior y ausencia de polling antes de la admisión. No se
facturan llamadas de IA en las pruebas: los proveedores son sintéticos.
