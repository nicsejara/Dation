# Arquitectura vigente — Dispatch 1.0.0

Dation ejecuta decisiones de logística a partir de **órdenes + una versión de flota + configuración**. FastAPI sirve la SPA y una API autenticada; Supabase almacena CSV privados, perfiles, corridas, explicaciones y mensajes. La IA explica resultados persistidos y no participa del cálculo.

## Flujo de ingesta y decisión

La carga continúa siendo una sola pantalla, pero ya no navega directamente al configurador:

```text
Órdenes V3 ──┐
             ├─> validación + persistencia ─> Decision Readiness
Fleet V3 ────┘                                   ↓
                                           Decision Case
                                                ↓
                                           Decision Map
                                                ↓
                                      Assignment disponible
                                                ↓
                                  configurar → ejecutar → revisar
                                                ↓
                                           aprobación humana
                                                ↓
                                   Scheduling se desbloquea si
                                   además tiene datos suficientes
```

La validación y la persistencia están desacopladas. Si Supabase o las migraciones todavía no están listos, el usuario puede validar ambos CSV y revisar sus problemas; sólo quedan bloqueados guardar y continuar.

`backend/app/validators/contracts.py` es la fuente única del contrato visible. Los validadores, `GET /api/dispatch/contracts` y las plantillas generadas consumen esa definición.

## Componentes

| Componente | Responsabilidad |
|---|---|
| `validators/contracts.py` | Columnas, obligatoriedad, reglas, ejemplos, alias y plantillas |
| `validators/*_schema.py` | Informe acumulativo + wrappers estrictos para el motor |
| `services/dispatch_service.py` | Estado, biblioteca, versionado, deduplicación, preflight y ejecución |
| `routes/dispatch.py` | Contratos, validación, plantillas, ejemplos, status y API Dispatch |
| `static/js/dispatch/upload/*` | Pantalla única de ingesta, errores, biblioteca, preflight y banner |
| `static/js/dispatch/workspace.mjs` | Orquestación de ingesta, configuración y corrida |
| `engines/assignment/*` | Motor activo de Assignment: packing, CP-SAT no temporal, invariantes y handoff |
| `engines/scheduling/*` | Motor activo de Scheduling: secuencia temporal con Assignment inmutable |
| `engines/dispatch/*` | Motor temporal Dispatch 2.2 conservado para corridas históricas |

## Persistencia y compatibilidad

La migración Dispatch agrega el modelo `orders/fleet`. La migración de biblioteca agrega archivado lógico y marca de datos de ejemplo. Ambas son aditivas. Los datasets previos siguen siendo `logistics_legacy`; las corridas históricas mantienen sus endpoints y renderer.

Se retiró **la pantalla legacy de carga**, no la compatibilidad histórica. Permanecen el upload sin tipo, `POST /api/runs/{dataset_id}`, el motor/renderer histórico y la apertura de corridas previas. El archivo estático de plantilla histórica puede seguir existiendo como compatibilidad, pero ya no se ofrece en la UI nueva.

La clase `dispatch-enabled` todavía se conserva para aislar la configuración Dispatch v1 del configurador histórico; retirarla requiere desacoplar también esa segunda etapa.

## Estado del sistema

`GET /api/dispatch/status` comprueba conexión, columnas visibles por PostgREST, RPC de flota y bucket privado. Si las columnas no están visibles, el endpoint no puede demostrar si faltó ejecutar SQL o sólo falta refrescar el schema cache; la UI lo expresa como diagnóstico verificable y remite a SQL Editor.

`validate_dispatch_run` es una función trigger y no se considera verificable de forma fiable por la API REST; su existencia se confirma manualmente con `pg_proc`.

## Ejecución y límites

El request de ejecución permanece abierto mientras `asyncio.to_thread` ejecuta el motor y el navegador consulta progreso persistido. CP-SAT usa un hilo, seed 0 y presupuestos acotados. Cada candidato se valida antes de compararse; no se publican resultados parciales ni se etiqueta como óptimo un resultado no certificado.

Para un Decision Case nuevo, `logistics_assignment` enruta a Assignment Engine 1.0.0. El modelo genera viajes abstractos respetando unidades enteras, capacidad, origen/site y ruta. Un mismo `vehicle_id` puede recibir varios viajes porque todavía no existe un calendario.

Fechas, transit time, SLA, tardanzas, velocidad, horas de conducción y ocupación temporal quedan fuera de Assignment y pertenecen a Scheduling. El resultado expone `handoff.schema_version=scheduling_input_v1` y `scenarios.selected.trips` como input versionado de la siguiente decisión.

Scheduling Engine 1.0.0 sólo acepta una corrida `assignment_v1` aprobada del mismo Decision Case y del mismo Data Pack. Conserva exactamente viajes, `vehicle_id`, rutas, órdenes, productos, unidades y kg. CP-SAT decide únicamente fechas de salida con `NoOverlap` por vehículo físico. Cuando `delivery_due_date` está completo y habilitado, la jerarquía es: órdenes tardías → días de tardanza → espera → makespan. Sin SLA: espera → makespan.

La aprobación humana de Assignment y Scheduling se persiste dentro de la metadata `decision_case` del run, de modo que el siguiente motor no dependa sólo de `sessionStorage`. La aprobación no altera el fingerprint matemático del resultado.

Dispatch 2.2 permanece disponible únicamente para recuperar y explicar corridas históricas.

## Frontend

La pantalla de ingesta usa módulos ES legibles bajo `static/js/dispatch/upload/`. Los valores provenientes de archivos se insertan con nodos de texto; el informe CSV utiliza la protección contra fórmulas existente. La pantalla es de dos columnas en escritorio y una en móvil; la barra final siempre comunica por qué el siguiente paso está bloqueado.

El dashboard sigue usando ECharts 6.0.0 empaquetado localmente y mantiene su renderer histórico para resultados anteriores.

## IA

El intérprete recibe un contexto derivado del `DecisionResult`. No recalcula ni selecciona el plan. La guardia numérica sigue siendo conservadora y la indisponibilidad del LLM no invalida una decisión persistida.

## Deuda registrada

- Crear un baseline SQL reproducible cuando se disponga del DDL completo de las tablas originales.
- Desacoplar y retirar el configurador legacy cuando las corridas históricas estén cubiertas por pruebas de navegador.
- Incorporar horas intradía, descansos regulatorios detallados, tiempos de carga/descarga, volumen y multiparada en una versión posterior.
- Evaluar colas y aislamiento al aumentar concurrencia.


## UX de carga 2026-10-02

La pantalla de carga funciona como asistente de ingesta: stepper Órdenes → Flota →
Revisión, resumen sticky en escritorio y barra inferior en móvil. La flota vigente se
reutiliza automáticamente, la carga se compacta una vez validada y el frontend muestra
qué interpretó del CSV antes de avanzar.

Los avisos del preflight llegan agrupados desde backend; la UI no traduce códigos del
motor. El gráfico de demanda versus capacidad propia usa ECharts vendorizado y tiene
alternativa tabular. La guía de formato usa el contrato servido por backend.


## Decision Chain — Fase 2

`static/js/dispatch/decision-case.mjs` implementa la máquina de estados del caso y `decision-map.mjs` su representación. El estado operativo de un nodo es distinto de su Data Readiness.

Estados soportados: `AVAILABLE`, `RUNNING`, `REVIEW`, `APPROVED`, `LOCKED`, `NEEDS_DATA`, `ERROR` y `STALE`.

Sólo Assignment tiene motor ejecutable en esta fase. Scheduling puede aparecer como `AVAILABLE` después de aprobar Assignment cuando sus datos están completos, pero el CTA informa que su motor llega en la siguiente fase. Final Assignment permanece bloqueado hasta disponer de una Scheduling aprobada.

El caso vive en `sessionStorage` para preservar navegación y recarga dentro de la sesión. Las corridas sí conservan lineage durable mediante `decision_case` dentro de JSON existente. No se agregó tabla ni migración.


## Decision Chain — Fase 3

Assignment y Scheduling dejan de compartir motor.

**Assignment 1.0.0**
- schema: `assignment_v1`;
- objetivos: viajes, costo, uso de flota propia y CO₂;
- no usa fechas ni SLA;
- salida principal: viajes + vehículo + cargas;
- handoff: `scheduling_input_v1`.

El preflight activo también es específico de Assignment y ya no genera hallazgos de tardanza o capacidad diaria. Decision Readiness conserva las columnas temporales para indicar si Scheduling tendrá datos suficientes una vez aprobado Assignment.

Las corridas `dispatch_v1/dispatch_v2` permanecen visibles, pero no pueden aprobar un nodo Assignment nuevo.


## Decision Chain — Fase 4

Scheduling pasa a ser un motor ejecutable.

**Scheduling 1.0.0**
- schema: `scheduling_v1`;
- input obligatorio: Assignment V1 aprobada + `scheduling_input_v1`;
- Assignment queda inmutable;
- usa `estimated_dispatch_date`, `available_from`, `available_until`, velocidad y horas de conducción;
- bloquea superposición de viajes del mismo `vehicle_id`;
- calcula salida, llegada, ciclo y próxima disponibilidad;
- puede proteger `delivery_due_date` de forma jerárquica cuando el dato está completo;
- handoff: `final_assignment_input_v1`.

El Decision Map permite configurar, ejecutar, revisar y aprobar Scheduling. Sólo después de una Scheduling aprobada puede desbloquearse Final Assignment si su Data Readiness está completo.
