# Dashboard: navegación directa y análisis progresivo

## Diagnóstico

El Dashboard activo de Assignment es `dashboard.mjs` → `assignment-dashboard-shell.mjs`. Antes elegía entre Summary/Evidence/Validation para Essential y ComparativeSummary/Comparison/Validation para Comparative. Esa bifurcación ocultaba la evidencia operativa cuando se profundizaba el análisis. El shell, la barra de decisiones, Scheduling y el stepper global ofrecían entradas al mapa desde un resultado; aprobar llevaba al mapa y obligaba a seleccionar otra vez el nodo.

`dashboard-stage.js` es una generación anterior, conservada para compatibilidad. Scheduling sigue usando `scheduling-dashboard.mjs`; los resultados anteriores mantienen el renderer de compatibilidad. El mapa continúa siendo la entrada al caso desde Inicio y el lugar donde se elige una corrida existente.

El motor también tiene un runtime que aplica filtros, política de flota y serialización canónica. Essential balanceado ya guarda todas las referencias; algunos objetivos Essential sólo guardan la referencia elegida. Esta diferencia determina si se reutiliza evidencia o se calcula únicamente lo que falta.

## Cambios

- **Navegación:** se retiraron los accesos al mapa y a cambiar datos del Dashboard, incluido el stepper global. Nueva corrida restaura la configuración de la corrida actual y abre Config del mismo caso/nodo. Nueva decisión guarda el borrador anterior, limpia el contexto activo y abre Carga de datos; no elimina casos, archivos, corridas o borradores históricos. La continuación consulta la aprobación vigente, metadatos del nodo y readiness real, y vuelve a validarlos antes de navegar. La barra sólo abre corridas existentes.
- **Viajes:** detalle inicialmente ausente; Ver detalle inserta un panel junto a la fila. Un solo viaje abierto, selección visible, cierre/toggle/Escape y retorno de foco. Tabs con navegación de teclado. En móvil, el detalle se ajusta al ancho visible de la tabla sin desplazar la página. Se conservan vehículo, ruta, capacidad, utilización, flota, proveedor, costos y cargas.
- **Comparative:** Essential permanece siempre como base. La capa comparativa se inserta después de Validación y antes de Dation IA; reutiliza los módulos comparativos existentes. La corrida Comparative original la muestra automáticamente. Essential ofrece generación local, cola/progreso, errores/reintento y restauración desde la base de datos.
- **Backend:** GET/POST autenticados `/api/runs/{run_id}/comparative`. El servidor reconstruye la intención desde un Assignment completado; sólo cambia `analysis_depth`. Si hay referencias suficientes, las guarda sin ejecutar el motor. Si faltan, el worker reaplica los filtros/política originales, verifica hashes de archivos y datos canónicos, reutiliza referencias existentes y conserva exactamente `scenarios.selected`.
- **Persistencia:** un artefacto único por corrida base, separado de `decision_runs`, con admisión transaccional, límite de cola, leases, heartbeat, fencing, máximo de recuperaciones y reintento explícito con la misma identidad. El resultado completado es inmutable. No actualiza nodos, historial, aprobaciones, upstream ni proyección del caso.
- **IA:** combina la recomendación original con referencias deterministas persistidas, incluida `sensitivity.frontier`. Explicaciones y turnos registran la evidencia utilizada en la misma transacción. El historial distingue interpretaciones originales cuando aparece evidencia nueva, conserva respuestas en curso y prefiere una explicación enriquecida aunque una explicación original termine más tarde. No dispara optimización desde el intérprete.

## Archivos principales

Frontend (`backend/app/static/js/dispatch/`):

- `workspace.mjs`, `decision-case.mjs`, `decision-ui.mjs`, `decision-nav.mjs`, `dashboard-actions.mjs`.
- `dashboard.mjs`, `assignment-dashboard-shell.mjs`, `scheduling-dashboard.mjs`.
- `assignment-evidence.mjs`, `comparative-upgrade.mjs`, `assignment-comparative-summary.mjs`, `assignment-dashboard-selectors.mjs`, `explanation.mjs`.
- Estilos: `backend/app/static/css/assignment-dashboard-essential.css`, `backend/app/static/css/assignment-dashboard-comparative.css`.
- Stepper: `backend/app/templates/app.html`.

Backend:

- `backend/app/services/comparative_analysis_service.py`, `dispatch_job_service.py`, `decision_interpreter_service.py`, `operations_service.py`.
- `backend/app/engines/assignment/engine.py`, `runtime.py`.
- `backend/app/routes/dispatch.py`, `backend/app/observability.py`, `backend/worker.py`.

Persistencia y verificación:

- `supabase/migrations/20261013090000_progressive_comparative_analysis.sql`.
- `supabase/catalog/20261013090000_comparative.json`, `scripts/apply_production_comparative.py`.
- `backend/tests/test_progressive_comparative.py`, `backend/tests/integration/test_progressive_comparative_sql.py`.
- `backend/tests/browser/test_navigation.py`, `backend/tests/e2e/test_workflow.py`, `backend/tests/e2e/browser_journey.py`, `backend/tests/test_decision_case.mjs`.
- Se actualizaron los contratos de presentación de `test_assignment_dashboard_phase1.py`, `test_assignment_dashboard_phase2.py`, `test_assignment_dashboard_phase3.py`, `test_frontend_contract.py` y el contrato de persistencia de turnos de `test_observability_phase7.py`.

## Migración y publicación

El SQL completo está en [20261013090000_progressive_comparative_analysis.sql](../supabase/migrations/20261013090000_progressive_comparative_analysis.sql). Añade dos tablas, once funciones, dos triggers, índices, RLS y permisos de servicio. No altera columnas ni RPCs anteriores y no reescribe el historial.

Aplicar **antes** de desplegar el nuevo worker/API:

```bash
python scripts/apply_production_comparative.py
```

Usa el token administrativo guardado en el entorno; compara el catálogo exacto de la Fase 7 y el nuevo catálogo, admite repetición sin cambios y rechaza instalaciones parciales o drift. Después, integrar el commit con CI verde y comprobar Cloud Build, worker y API. Para rollback de código, volver a las revisiones previas y conservar las tablas aditivas y sus registros; no eliminar evidencia histórica.

## Validación reproducible

```bash
SUPABASE_URL='' SUPABASE_SECRET_KEY='' LLM_API_KEY='' DATION_ACCESS_PASSWORD='' \
  PYTHONPATH=backend python -m unittest discover -s backend/tests -p 'test_*.py'
node --test backend/tests/test_*.mjs backend/tests/test_*.js
CHROMIUM_EXECUTABLE=/usr/bin/chromium \
  DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
  backend/.browser-venv/bin/python -m unittest discover -s backend/tests/browser
DATION_SQL_TEST_CONTAINER=dation-progressive-sql \
  PYTHONPATH=backend/tests/integration python -m unittest discover -s backend/tests/integration
DATION_BROWSER_PYTHON=/workspace/Dation/backend/.browser-venv/bin/python \
  CHROMIUM_EXECUTABLE=/usr/bin/chromium python backend/tests/e2e/run_suite.py
```

Los tests SQL necesitan un contenedor PostgreSQL 17 propio, listo por TCP; cada clase crea y elimina su base aislada. Los E2E crean su propia infraestructura PostgreSQL/PostgREST/Storage/API/worker y la eliminan al terminar. Los reinicios forzados y la corrupción de archivos ocurren sólo allí. Chromium sintético intercepta la API; el recorrido E2E adicional usa API y persistencia reales de la infraestructura aislada.

La cobertura nueva verifica idempotencia concurrente, reutilización sin worker, inmutabilidad de selección/configuración/inputs, rechazo de intención inválida, aislamiento del estado de negocio, recuperación/fencing/deadline/reintento, RLS, persistencia atómica de procedencia, restauración tras reload, navegación directa, detalle móvil/teclado y respuesta IA en curso al completar Comparative. CI descubre automáticamente los nuevos tests.

Resultado local del 13 de octubre de 2026: **346 Python, 21 Node, 38 Chromium, 46 SQL y 7 E2E aprobados**. Compilación Python, sintaxis de los 59 archivos JavaScript, `pip check` y `git diff --check` correctos. Auditorías de `requirements.txt` y `requirements-browser.txt` sin vulnerabilidades conocidas. Los screenshots móviles se inspeccionaron y el test verifica que el panel completo cabe en el viewport.

## Flujos finales

| Origen y acción | Destino |
|---|---|
| Dashboard → Nueva corrida | Config actual, mismo caso/nodo/datasets |
| Dashboard → Nueva decisión | Carga de datos, contexto nuevo |
| Dashboard aprobado → Siguiente decisión | Config siguiente, con aprobación vigente y readiness |
| Inicio → Decision Case | Mapa |
| Mapa → Run existente | Dashboard de esa corrida |
| Dashboard Essential → Generar Comparative | Mismo Dashboard y mismo run, con artefacto persistido |

## Límites reales

Asignación final continúa sin motor implementado; se informa que no está disponible y no se abre una configuración vacía. Las corridas de otra versión de motor pueden reutilizar referencias guardadas, pero no generar referencias faltantes con un motor distinto. Si los archivos originales no están disponibles o sus hashes cambian, la profundización falla de forma local y la corrida original sigue accesible. La respuesta de un proveedor IA puede fallar; la evidencia determinista y el historial permanecen guardados y el usuario puede reintentar.
