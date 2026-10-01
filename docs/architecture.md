# Arquitectura vigente — Dispatch 1.0.0

Dation ejecuta decisiones de logística a partir de **órdenes + una versión de flota + configuración**. FastAPI sirve `/app`, `/upload`, API autenticada y módulos JavaScript. Supabase almacena CSV privados, perfiles, corridas, explicaciones y mensajes. La IA explica resultados persistidos; no participa del cálculo.

## Componentes y responsabilidades

| Componente | Responsabilidad |
|---|---|
| `validators/*_schema.py` | Contratos separados, UTF-8, validación por fila y perfiles |
| `models/dispatch_config.py` | Tres prioridades, presets y presupuestos |
| `engines/dispatch/normalization.py` | Capacidad por unidades enteras, ventanas y preflight |
| `engines/dispatch/plans.py` | Referencias, construcción determinística, invariantes y métricas |
| `engines/dispatch/model.py` | CP-SAT de slots de viaje, capacidad y salidas diarias |
| `engines/dispatch/engine.py` | Escenarios, selección, sensibilidad y huella reproducible |
| `services/dispatch_service.py` | Versionado, deduplicación por tipo, ejecución en hilo y progreso persistido |
| `routes/dispatch.py` | Endpoints nuevos registrados antes de la ruta legacy dinámica |
| `static/js/dispatch/*.mjs` | Carga/configuración, hero, KPIs, plan, comparador, sensibilidad e IA |
| `services/dispatch_context.py` | Evidencia acotada y comprobación conservadora de cifras |

## Persistencia y compatibilidad

La migración es aditiva. Los datasets anteriores quedan como `logistics_legacy`; los nuevos son `orders` o `fleet`, con perfil y hash. Una flota nueva conserva `parent_dataset_id`. Marcar una flota vigente es una operación transaccional serializada; no modifica versiones pasadas. Un CSV idéntico reutiliza su versión por `(dataset_type, sha256)`.

Cada corrida nueva conserva ambos IDs, hashes, configuración, opciones, motor, solver, resumen y resultado completo. `dataset_id` sigue apuntando a órdenes por compatibilidad. El trigger verifica las referencias. Se mantienen Basic Auth, RLS existente, tablas y endpoints históricos. El chequeo de Supabase ahora también requiere autenticación.

`schema_version: dispatch_v1` decide qué renderer/contexto usar. El motor 0.2 y sus corridas continúan disponibles. La interfaz ofrece “Usar formato anterior”. Sin migración, los endpoints nuevos informan que falta activación y no escriben datos del contrato nuevo.

## Ejecución y límites

La petición POST permanece abierta mientras `asyncio.to_thread` ejecuta el motor. El event loop puede atender el polling. Se persisten etapas reales, sin porcentajes artificiales. La lectura de una corrida atascada aplica `DATION_STALE_RUN_SECONDS` (600 por defecto, mínimo 300) y la marca como error condicionalmente si todavía estaba corriendo.

CP-SAT usa un hilo, seed 0 y presupuesto determinístico. Default: 10 s de reloj por solve, 0,1 de tiempo determinístico, 90 s globales. Hasta 300 órdenes se intenta el modelo, con tope de 25.000 variables estimadas. Para más órdenes se usa la heurística determinística; también puede utilizarse el mejor candidato validado cuando no hay solución del solver. No se etiqueta como óptimo un resultado heurístico. Un corte de reloj antes de completar el presupuesto determinístico es error; no se publica un incumbent dependiente de velocidad de máquina. El límite global se controla entre etapas y antes de publicar; una etapa en curso puede tardar en devolver el control. No hay cancelación dura de threads.

Las cargas usan unidades y gramos enteros. Cada candidato se valida antes de compararlo: cobertura exacta, capacidad, ruta, salida, llegada y disponibilidad diaria. No se publican planes parciales. Se limita a 10.000 viajes por candidato; fuera de ese alcance se solicita dividir el horizonte. Este servicio no es todavía un sistema de colas ni tiene aislamiento de CPU por usuario. Dimensionar concurrencia y timeout en Cloud Run antes de uso intensivo.

El JSON guarda viajes y resultados por orden solamente en `selected` y `baseline_direct`. Los demás escenarios y puntos de sensibilidad conservan métricas y huellas; sensibilidad incluye órdenes que cambian respecto de la decisión y del punto anterior. La huella excluye horas de ejecución, IDs de almacenamiento y tiempos del solver, pero incluye hashes de los archivos y configuración. OR-Tools y Python están fijados; no se promete identidad de planes entre versiones distintas del solver.

## Frontend y gráficos

Módulos vanilla independientes del renderer histórico. Los textos externos se escapan antes de insertarlos en HTML; el chat usa nodos de texto. Los CSV de exportación protegen fórmulas de hojas de cálculo. ECharts 6.0.0 está empaquetado localmente con SVG, barras, líneas y dispersión, sin CDN en runtime. Licencia y NOTICE acompañan el bundle.

Para reconstruir el bundle desde la raíz, en un directorio temporal:

```bash
mkdir -p /tmp/dation-charts
npm install --prefix /tmp/dation-charts echarts@6.0.0 esbuild@0.25.10
cp scripts/echarts-entry.mjs /tmp/dation-charts/entry.mjs
/tmp/dation-charts/node_modules/.bin/esbuild /tmp/dation-charts/entry.mjs --bundle --minify --format=iife --global-name=DationCharts --outfile=backend/app/static/vendor/echarts-dispatch-6.0.0.min.js
```

## IA

Prompt `decision_interpreter_v1.0`. Contexto de máximo 18.000 caracteres serializados, con reducción explícita de detalles opcionales; cifras y restricciones provienen del resultado. La comprobación numérica admite números presentes y sus redondeos, no certifica que una frase los interprete correctamente. Si falla, la explicación usa un resumen determinístico; el chat indica que no pudo validar la respuesta. La conexión real a Groq no fue ejecutada durante esta validación.

## Deuda registrada

- Retirar el renderer/motor legacy solamente tras decisión expresa y migración de usuarios.
- Evaluar colas, cancelación y procesos aislados al aumentar concurrencia.
- Incorporar ocupación real de vehículos, volumen y multiparada en un modelo posterior.
- La sensibilidad de ±1 camión es un stretch pendiente; no está simulada en esta versión.
- Probar migración y despliegue reales con el propietario; esta entrega no aplica SQL productivo.

Ver `validation-dispatch-v1.md`, `data-contracts.md`, ADR 0001 y `backend/DEPLOYMENT.md`.
