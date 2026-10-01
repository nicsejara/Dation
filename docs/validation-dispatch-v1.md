# Validación de Dispatch 1.0.0 — 1 octubre 2026

## Evidencia ejecutada

- **51 tests Python aprobados**, incluyendo motor histórico, validadores, contratos frontend, contexto de IA y endpoints ASGI con persistencia simulada.
- Dos suites Node aprobadas: selectores/formatos anteriores y selectores nuevos (deltas semánticos, planes idénticos, sliders y filtros).
- Sintaxis de todos los JS/MJS, compilación Python y `git diff --check` sin errores.
- Nueve casos CSV descargables comprobados por `test_dispatch_fixtures.py` contra resultados calculables a mano: consolidación, indivisibilidad, salidas limitadas, reprogramación, tardanza inevitable, incluir/excluir anomalía y rechazos esperados.
- Conservación de unidades en cada escenario factible; validación de capacidad, disponibilidad, ruta, llegada y carga. Extremos de pesos equivalentes y selección ponderada no peor que la referencia factible.
- Repetición de 100 órdenes: huella idéntica `2e5924266e5369cf19deeef1eaa62edf9317695222731ee1fc74066c1005fca1`, incluso tras recrear el entorno de ejecución.

## Rendimiento observado

Python 3.12 y OR-Tools 9.15.6755 en el workspace local. No son mediciones de Cloud Run. Incluye todos los escenarios y sensibilidad; el benchmark se reproduce con `PYTHONPATH=backend python scripts/benchmark_dispatch.py`.

| Órdenes | Unidades conservadas | Viajes elegidos | Tiempo última medición | JSON UTF-8 | Método elegido |
|---|---:|---:|---:|---:|---|
| 100 | 2.682 | 143 | 5,397 s | 195.363 bytes | CP-SAT factible |
| 1.000 | 26.820 | 1.061 | 5,176 s | 1.546.850 bytes | Heurística |

Otras mediciones del mismo código/datos fueron 10,291–10,392 s para 100 y 7,982 s para 1.000, sin cambiar las huellas. El tiempo depende del host; no se promete ese tiempo en producción. El JSON puede variar unos bytes por tiempos y marcas temporales, excluidos de la huella. Para más de 300 órdenes se aplica deliberadamente la heurística; no se afirma optimalidad global.

## Prueba visual y funcional de navegador

Chromium con Playwright, FastAPI local y APIs simuladas, usando el resultado real del motor como fixture. `scripts/qa/dispatch-browser.cjs` reproduce el flujo de selección de órdenes/flota, tres prioridades, revisión, ejecución, recuperación por recarga, tabs, búsqueda, chat lateral, exportación JSON/CSV y regreso a configuración.

Se revisaron capturas a **1440 px y 390 px**: el ancho del documento coincide con el viewport; tablas anchas desplazan dentro de su sección. La barra “Configuración lista” coincide con el ancho del bloque de configuración. No aparecieron excepciones JavaScript. Se corrigieron dos referencias a funciones inexistentes del arranque anterior que impedían completar la inicialización.

Para reproducir: generar `/tmp/dispatch100.json` con el benchmark, servir `backend` en puerto 8765 con `DATION_ACCESS_PASSWORD=dispatch-qa`, instalar Playwright/Chromium y ejecutar `CHROMIUM_PATH=/ruta/chromium node scripts/qa/dispatch-browser.cjs`. Las capturas se escriben en `/tmp`. No ejecuta cambios en Supabase.

## Entregables por fase

| Fase | Cambios / archivos principales | Estado / puerta pendiente |
|---|---|---|
| 1 | `validators`, modelos, conversor, `sample_data/v1` | Tests aprobados; fechas día/mes explícitas y unidades indivisibles |
| 2 | `supabase/migrations/20261001004934_dispatch_v1.sql` | SQL preparado; aplicación y confirmación reservadas al usuario |
| 3 | `engines/dispatch`, tests, benchmark | Invariantes y rendimiento comprobados; fallback explícito |
| 4 | `routes/dispatch.py`, `dispatch_service.py`, `main.py` | HTTP autenticado y simulado aprobado; persistencia real pendiente |
| 5 | `workspace.mjs`, plantillas CSV, CSS | Carga/configuración modular, flota vigente y revisión |
| 6 | Módulos hero/KPIs/plan/compare/sensitivity/dashboard | Revisión a 1440/390 y flujo de navegador aprobado |
| 7 | Contexto y guardia numérica, conocimiento, ADR, contratos y despliegue | Implementados; revisión del usuario y prueba con proveedor IA pendiente |
| 8 | requirements, Python 3.12, workflow, limpieza | Checks locales aprobados; verificar ejecución de GitHub Actions del commit publicado |

## Límites de la verificación

No se aplicó la migración ni se escribió una corrida real en Supabase durante estas pruebas. No se verificó la revisión desplegada, CPU, memoria o timeout efectivos de Cloud Run. No se llamó al proveedor de IA: se probó la construcción de evidencia y el control numérico. Los históricos conservan motor y renderer; la compatibilidad automática cubre el motor y contrato DOM, no toda combinación posible de datos históricos.

Para aceptar la activación final: aplicar SQL, desplegar/confirmar backend nuevo, completar una carga y corrida persistida con los CSV, reabrirla desde el historial y probar una explicación real. La comprobación de cifras es conservadora, no una certificación semántica. La sensibilidad de ±1 camión queda registrada como mejora posterior.
