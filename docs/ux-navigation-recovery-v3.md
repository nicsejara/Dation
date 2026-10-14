# UX / Navigation / Recovery Saga v3

## A. Diagnóstico

El Overview ofrecía seis botones equivalentes entre Hero, pasos, cierre y versión móvil. `dda-logistics-landing.js` mantenía handlers independientes para datos/mapa/Inicio. El mapa agrupaba identidad, progreso y archivos en una card grande; Config compartía una card siempre expandida mediante `decisionCaseCard()`.

El error terminal del polling se mostraba con `errorBox()` y su Reintentar abría el mismo run fallido. El GET existente ya entrega `status`, `error_message`, `configuration_json`, caso, nodo y datasets; no hace falta ampliar el contrato. Se reutilizan el toolbar compartido, navegación por recurso, selector de casos compactos, hidratación, restauración temporal y polling existentes.

El E2E con una ventana imposible detectó además un defecto previo en la admisión: `SchedulingConfig.model_dump()` devolvía objetos `date`, y la serialización JSON de la intención de cola fallaba antes de crear el run. Una única corrección a `model_dump(mode="json")` conserva las mismas fechas ISO y permite admitir y registrar esas corridas.

## B. Cambios

- **Overview:** un solo CTA en el Hero. Sin casos ofrece Iniciar proceso de decisión y abre Datos. Un caso seleccionado continúa directamente a su mapa; sin selección y con varios casos reutiliza el selector. Se eliminaron botones inferiores/móviles y handlers legacy; el resto del contenido permanece informativo.
- **Map:** selector de Decision Case visible, progreso independiente siempre visible y contexto del caso/Data Pack en `<details>` cerrado. Expandido conserva ID/copia, estado, fecha, archivos, registros, validación, columnas y Cambiar datos con su confirmación existente. La selección de decisiones gana espacio y un encabezado explícito. Cambiar caso hidrata sólo el elegido y actualiza URL, datasets, readiness, progreso y cards sin pasar por Inicio. Escape/cancelar restituye el foco al selector.
- **Config:** `decisionCaseCard()` comparte el disclosure cerrado entre Assignment y Scheduling. Los handlers de datos y copia permanecen operativos. La Assignment aprobada de Scheduling permanece fuera del disclosure.
- **Assignment Dashboard:** los cuatro KPIs mantienen valores y definiciones accesibles, sin badges ni nota obsoleta. Comparative completado puede cerrarse/reabrirse y recuerda el estado por run en sessionStorage. Cerrar no escribe, borra ni genera evidencia; reabrir utiliza el mismo artefacto. Polling, restore, retry y `onEvidenceReady` permanecen activos.
- **Scheduling Dashboard:** se elimina exclusivamente la exportación duplicada del calendario y su función/import sin consumidores. CSV/JSON siguen disponibles en la toolbar, con los mismos formatos.
- **Toolbar:** Decision Map secundario en ambas decisiones mediante `caseActions.onMap`. Usa el caso persistido de la corrida, incluso si la sesión o URL venía de otro caso histórico. Limpia nodo/run de la URL y sólo navega; Nueva corrida y continuación mantienen sus destinos directos.
- **Error recovery:** `run.status === "error"` ofrece Volver a configurar asignación/planificación y Decision Map. Un helper compartido con Nueva corrida restaura intención, ventana, estrategia, reglas, opciones y Data Pack antes de abrir Config del mismo caso/nodo, sin runId. La siguiente ejecución genera otro UUID; conserva el run fallido y la aprobación upstream. Los errores transitorios siguen ofreciendo Reintentar para consultar estado. Fallos de recuperación muestran feedback local y permiten reintentar.
- **Traceability/CSS:** se reutiliza la lista compacta y el modal existente. No se agrega endpoint, toolbar o selector paralelo. Los disclosures tienen foco visible, wrapping móvil y chevron; toolbar y comparativo mantienen acciones accesibles. Se retiraron reglas específicas de badges/nota KPI que quedaron sin consumidores.
- **Tests:** se actualizan contratos de presentación y se agregan doce recorridos Chromium, tres casos de lineage Node y tres pruebas Python de serialización. El E2E real incluye una planificación imposible, reconfiguración, nueva corrida y aprobación, con verificación de las tres filas históricas.

## C. Archivos modificados

- `backend/app/routes/dispatch.py`.
- `backend/app/static/css/assignment-config-v2.css`.
- `backend/app/static/css/assignment-dashboard-comparative.css`.
- `backend/app/static/css/assignment-dashboard-essential.css`.
- `backend/app/static/css/dashboard-toolbar.css`.
- `backend/app/static/css/decision-map-case-v2.css`.
- `backend/app/static/css/dispatch.css`.
- `backend/app/static/js/dda-logistics-landing.js`.
- `backend/app/static/js/dispatch/assignment-summary.mjs`.
- `backend/app/static/js/dispatch/comparative-upgrade.mjs`.
- `backend/app/static/js/dispatch/dashboard-toolbar.mjs`.
- `backend/app/static/js/dispatch/decision-config-ui.mjs`.
- `backend/app/static/js/dispatch/decision-map.mjs`.
- `backend/app/static/js/dispatch/navigation.mjs`.
- `backend/app/static/js/dispatch/scheduling-dashboard.mjs`.
- `backend/app/static/js/dispatch/traceability-controller.mjs`.
- `backend/app/static/js/dispatch/traceability-ui.mjs`.
- `backend/app/static/js/dispatch/workspace.mjs`.
- `backend/app/templates/app.html`.
- `backend/tests/browser/test_navigation.py`.
- `backend/tests/e2e/browser_journey.py`.
- `backend/tests/e2e/test_workflow.py`.
- `backend/tests/test_assignment_dashboard_phase2.py`.
- `backend/tests/test_frontend_contract.py`.
- `backend/tests/test_landing_navigation_contract.py`.
- `backend/tests/test_navigation.mjs`.
- `backend/tests/test_run_request_serialization.py`.
- `backend/tests/test_traceability_phase3.py`.
- `docs/ux-navigation-recovery-v3.md`.

## D. Backend / DB

**Backend: corrección mínima requerida.** `backend/app/routes/dispatch.py` normaliza la configuración de Scheduling con `model_dump(mode="json")` para que las ventanas globales y reglas con fechas puedan serializarse en la admisión durable de `POST /api/runs`. No cambia el schema del endpoint, las reglas del motor, la identidad de corridas previas ni la base de datos.

**DB / Supabase / migrations: No requerido.** No hay DDL, endpoints nuevos, cambios de dependencias ni modificaciones de infraestructura. Las pruebas de fallo y recuperación se realizan en infraestructura descartable; la comprobación productiva utiliza lecturas y previews sin crear corridas de QA.

## E. Tests

Desde el checkout, con `/workspace/.dation-cloud/activate.sh` activado:

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

Resultado local del 14 de octubre de 2026: **498 pruebas aprobadas: 349 Python, 37 Node, 59 Chromium, 46 SQL y 7 E2E**. Compilación Python, sintaxis de 60 archivos JavaScript, pip check y diff check correctos. Auditorías runtime/navegador sin vulnerabilidades conocidas. Capturas de Map, Config, comparativo cerrado, Overview y error terminal inspeccionadas en escritorio/móvil; Chromium no presenta errores JavaScript.

Los SQL/E2E crean y eliminan bases y servicios aislados. El navegador real sube archivos, ejecuta/aprueba Assignment, genera/cierra/restaura Comparative, admite una planificación imposible, restaura su ventana, ejecuta otra corrida y aprueba Scheduling. Se verifica que el run fallido sigue con error, sin aprobación/resultado, conserva sus fechas y comparte caso/upstream con la nueva corrida. El historial contiene las tres corridas, con identidades distintas. Los tests sintéticos cubren además red/reintento, error Assignment, cambio de casos/datasets, foco, disclosure, botones móviles, navegación histórica y ausencia de POST al reabrir Comparative.

## F. Confirmación explícita

```text
Overview = 1 CTA
Decision Case/Data Pack = disclosure
Progress = visible en Map
KPI badges = removidos
Comparative = closable
Scheduling error = reconfigurable
Timeline export duplicado = removido
Dashboard toolbar = Decision Map
Map = case selector
```

## G. Riesgos restantes

La reconfiguración utiliza la Assignment actualmente aprobada del caso: una fuente histórica reemplazada no puede volver a ejecutarse como upstream vigente. Cambiar configuración no garantiza factibilidad; si las nuevas restricciones también son incompatibles, el nuevo run conserva su propio error y ofrece otra reconfiguración. Los resultados históricos sin suficiente lineage/Data Pack requieren recuperar sus datos originales. Asignación final continúa sin motor implementado.
