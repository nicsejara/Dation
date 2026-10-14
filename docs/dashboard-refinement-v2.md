# Dashboard Refinement v2

## A. Diagnóstico

Assignment usa `dashboard.mjs` y su shell modular; Scheduling conserva su timeline, SLA y excepciones en `scheduling-dashboard.mjs`. Ambos tenían acciones equivalentes, pero implementaciones y presentación diferentes. La aprobación de Assignment dependía de un botón inline y un proxy en la toolbar; Scheduling incluía información técnica dentro del menú de acciones.

Los resúmenes del motor y las referencias comparativas ya publican `total_trips`, `total_cost`, `load_utilization` y `own_weight_share`. Se verificaron los fixtures, la implementación de `plans.summarize`, la serialización y los artefactos persistidos de QA en producción. `load_utilization` representa carga transportada / capacidad total de los viajes utilizados; `own_weight_share` representa participación por **peso**, no cantidad de vehículos o viajes. No es necesario ampliar el contrato.

## B. Cambios

- **Toolbar:** un componente compartido ofrece Aprobar, Exportar y Más. Aprobar llama directamente al handler, evita llamadas duplicadas, muestra progreso y permite reintentar errores locales. Al completar, actualiza la aprobación y consulta la continuación existente sin recargar el Dashboard. Más contiene exactamente Nueva corrida, Nueva decisión y Detalles de ejecución.
- **KPIs:** una definición canónica genera los cuatro indicadores del resumen y del comparador: Cantidad de viajes, Utilización media, Costo promedio por viaje y % flota propia. Cada escenario calcula su propio `total_cost / total_trips`, sin redondeo intermedio. Datos ausentes, inválidos o cero viajes producen `—`. El costo promedio es descriptivo: minimizar costo total no equivale a minimizar este cociente. Los porcentajes incluyen su definición accesible.
- **Validación:** sin observaciones se muestra un único estado compacto. Se conservan las advertencias reales sobre infeasibilidad, excepciones del motor, tercerización, anomalías incluidas y órdenes divididas. No se muestra evidencia genérica del solver ni aprobación inline.
- **Comparative:** conserva el selector, el estado de misma distribución/no factibilidad y las mismas cuatro tarjetas. Se retiraron trazas técnicas visibles, contadores, prioridades y la narrativa de lectura de la elección. Los deltas mantienen el contrato recomendación menos referencia: viajes/costo promedio prefieren menos; utilización/flota propia prefieren más. Porcentajes usan puntos porcentuales; variación relativa con referencia cero queda no comparable. Se conservan restauración, generación, polling, reintento, identidad y procedencia del artefacto.
- **Scheduling:** comparte la toolbar y el drawer; mantiene aprobación, exportaciones originales, timeline, SLA, excepciones y chat. El drawer conserva corrida, caso, motor, solver/estado, Assignment fuente, viajes, vehículos, fechas, archivos, huella y servicio de IA.
- **CSS y lifecycle:** estilos neutrales compartidos, comparación en cuatro columnas / dos / una según el espacio, drawer con backdrop, Escape, control y retorno del foco. Se limpiaron reglas y handlers sin consumidores. Menús, drawer y chat limpian sus recursos al navegar.
- **Tests:** contratos adaptados a la interfaz activa, doce casos Node nuevos y ocho recorridos Chromium nuevos. El E2E real aprueba ambas decisiones mediante la toolbar.

La navegación conserva sus destinos: Nueva corrida abre Config del mismo caso y nodo; Nueva decisión abre Carga de datos; la continuación sólo abre Config de un nodo AVAILABLE. El mapa sigue siendo la entrada desde Inicio. La IA continúa interpretando evidencia después del comparador.

## C. Archivos

Frontend:

- `backend/app/static/js/dispatch/dashboard-toolbar.mjs` (nuevo).
- `backend/app/static/js/dispatch/assignment-dashboard-selectors.mjs`.
- `backend/app/static/js/dispatch/assignment-summary.mjs`.
- `backend/app/static/js/dispatch/assignment-validation.mjs`.
- `backend/app/static/js/dispatch/assignment-comparative-summary.mjs`.
- `backend/app/static/js/dispatch/assignment-comparison.mjs`.
- `backend/app/static/js/dispatch/comparative-upgrade.mjs`.
- `backend/app/static/js/dispatch/assignment-dashboard-shell.mjs`.
- `backend/app/static/js/dispatch/scheduling-dashboard.mjs`.
- `backend/app/static/js/dispatch/dashboard.mjs`.
- `backend/app/static/css/dashboard-toolbar.css` (nuevo).
- `backend/app/static/css/assignment-dashboard-v2.css`.
- `backend/app/static/css/assignment-dashboard-essential.css`.
- `backend/app/static/css/assignment-dashboard-comparative.css`.

Pruebas y documentación:

- `backend/tests/test_assignment_executive_kpis.mjs` (nuevo).
- `backend/tests/test_assignment_dashboard_phase1.py`.
- `backend/tests/test_assignment_dashboard_phase2.py`.
- `backend/tests/test_assignment_dashboard_phase3.py`.
- `backend/tests/test_frontend_contract.py`.
- `backend/tests/browser/test_navigation.py`.
- `backend/tests/e2e/browser_journey.py`.
- `docs/dashboard-refinement-v2.md` (este documento).

## D. Backend / DB

**No requerido.** No se modifican endpoints, motor, esquemas, migraciones, dependencias, secretos ni infraestructura. La publicación usa el flujo de despliegue existente. Los cálculos son selectores puros y no escriben métricas derivadas en los resultados, por lo que JSON y CSV conservan su contrato.

## E. Tests

Con el runtime instalado y activado desde `/workspace/.dation-cloud/activate.sh`:

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

Resultado local del 13 de octubre de 2026: **480 pruebas aprobadas: 346 Python, 34 Node, 47 Chromium, 46 SQL y 7 E2E**. Los tests de integración y E2E utilizan infraestructura aislada y eliminan sus bases/servicios al terminar. Compilación Python, sintaxis de 60 archivos JavaScript, `pip check` y `git diff --check` correctos. Auditorías de requisitos runtime y navegador sin vulnerabilidades conocidas. Capturas de Assignment y Scheduling inspeccionadas en escritorio y móvil; la suite comprueba límites del drawer y ausencia de overflow.

La cobertura incluye cociente por escenario, datos históricos incompletos, tipos inválidos, referencia cero, ausencia de redondeo anticipado, porcentajes ponderados por peso, puntos porcentuales, no factibilidad, advertencias reales, aprobación única/progreso/error/reintento, exportaciones CSV/JSON, foco/Escape/backdrop, limpieza al navegar y conservación de generación/restauración/IA y flujos existentes.

## F. Confirmación UX

```text
Assignment = 4 KPIs
Validation = sólo warnings reales
Approval = sólo toolbar
Comparative = mismos 4 KPIs
Trace visible = removida
Lectura elección = removida
Scheduling Más = homologado
```

La trazabilidad técnica continúa disponible en Detalles de ejecución y la procedencia de Comparative permanece persistida; su retirada afecta sólo al bloque ejecutivo visible.

## G. Riesgos restantes

Las corridas históricas que no contienen una métrica canónica muestran `—`; no se reconstruye una métrica con otra semántica. Asignación final continúa sin motor disponible, por lo que no se ofrece como siguiente configuración ejecutable. Ambos límites ya existían y no se alteran en esta iteración.
