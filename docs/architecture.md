# Arquitectura vigente — Dispatch 1.0.0

Dation ejecuta decisiones de logística a partir de **órdenes + una versión de flota + configuración**. FastAPI sirve la SPA y una API autenticada; Supabase almacena CSV privados, perfiles, corridas, explicaciones y mensajes. La IA explica resultados persistidos y no participa del cálculo.

## Flujo de ingesta

La etapa de carga es una sola pantalla:

```text
Órdenes CSV ──┐
              ├─> validación local sin DB ─> persistencia versionada ─┐
Flota CSV ────┘                                                       ├─> preflight
                                                                      └─> Configurar decisión
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
| `engines/dispatch/*` | Motor determinístico, invariantes, escenarios y sensibilidad |

## Persistencia y compatibilidad

La migración Dispatch agrega el modelo `orders/fleet`. La migración de biblioteca agrega archivado lógico y marca de datos de ejemplo. Ambas son aditivas. Los datasets previos siguen siendo `logistics_legacy`; las corridas históricas mantienen sus endpoints y renderer.

Se retiró **la pantalla legacy de carga**, no la compatibilidad histórica. Permanecen el upload sin tipo, `POST /api/runs/{dataset_id}`, el motor/renderer histórico y la apertura de corridas previas. El archivo estático de plantilla histórica puede seguir existiendo como compatibilidad, pero ya no se ofrece en la UI nueva.

La clase `dispatch-enabled` todavía se conserva para aislar la configuración Dispatch v1 del configurador histórico; retirarla requiere desacoplar también esa segunda etapa.

## Estado del sistema

`GET /api/dispatch/status` comprueba conexión, columnas visibles por PostgREST, RPC de flota y bucket privado. Si las columnas no están visibles, el endpoint no puede demostrar si faltó ejecutar SQL o sólo falta refrescar el schema cache; la UI lo expresa como diagnóstico verificable y remite a SQL Editor.

`validate_dispatch_run` es una función trigger y no se considera verificable de forma fiable por la API REST; su existencia se confirma manualmente con `pg_proc`.

## Ejecución y límites

El request de ejecución permanece abierto mientras `asyncio.to_thread` ejecuta el motor y el navegador consulta progreso persistido. CP-SAT usa un hilo, seed 0 y presupuestos acotados. Cada candidato se valida antes de compararse; no se publican planes parciales ni se etiqueta como óptimo un resultado no certificado.

El modelo actual no representa multiparada, volumen, ventanas horarias completas ni ocupación física de un vehículo durante varios días.

## Frontend

La pantalla de ingesta usa módulos ES legibles bajo `static/js/dispatch/upload/`. Los valores provenientes de archivos se insertan con nodos de texto; el informe CSV utiliza la protección contra fórmulas existente. La pantalla es de dos columnas en escritorio y una en móvil; la barra final siempre comunica por qué el siguiente paso está bloqueado.

El dashboard sigue usando ECharts 6.0.0 empaquetado localmente y mantiene su renderer histórico para resultados anteriores.

## IA

El intérprete recibe un contexto derivado del `DecisionResult`. No recalcula ni selecciona el plan. La guardia numérica sigue siendo conservadora y la indisponibilidad del LLM no invalida una decisión persistida.

## Deuda registrada

- Crear un baseline SQL reproducible cuando se disponga del DDL completo de las tablas originales.
- Desacoplar y retirar el configurador legacy cuando las corridas históricas estén cubiertas por pruebas de navegador.
- Incorporar ocupación real de vehículos, volumen y multiparada en una versión posterior.
- Evaluar colas y aislamiento al aumentar concurrencia.


## UX de carga 2026-10-02

La pantalla de carga funciona como asistente de ingesta: stepper Órdenes → Flota →
Revisión, resumen sticky en escritorio y barra inferior en móvil. La flota vigente se
reutiliza automáticamente, la carga se compacta una vez validada y el frontend muestra
qué interpretó del CSV antes de avanzar.

Los avisos del preflight llegan agrupados desde backend; la UI no traduce códigos del
motor. El gráfico de demanda versus capacidad propia usa ECharts vendorizado y tiene
alternativa tabular. La guía de formato usa el contrato servido por backend.
