# Baseline y CI — Platform MVP, Fase 0

Baseline funcional: `22f1187451429c8e98dfcb9874f89b974500cb35` (`main`, PR #72).
La Fase 0 conserva el flujo privado compartido y documenta el punto de partida antes de introducir identidad y workspaces. No cambia motores, métricas, aprobaciones, rutas ni datos productivos.

## Resultado comprobado

Resumen verificable versionado: [baseline-results.json](baseline-results.json). Los SHA de ese reporte identifican el código de aplicación auditado, no el commit documental posterior.

| Comprobación local de esta Fase 0 | Resultado | Alcance |
| --- | --- | --- |
| Python `unittest discover` | 350/350, 0 omitidos | Contratos API, servicios, persistencia, motores, interfaz y seguridad existente |
| Funciones Python fuera de `unittest` | 13/13 | Tres módulos con funciones `test_*` de nivel superior |
| Node | 77/77, 0 omitidos | Selectores, KPIs y lógica JavaScript |
| PostgreSQL 17 aislado | 46/46, 0 omitidos | Esquema, historial, concurrencia, aprobaciones, colas, evidencia IA y permisos |
| E2E con API/worker/base de datos reales | 10/10, 0 omitidos | Flujo de navegador desktop/móvil y recuperación de procesos |
| Chromium IA focalizado | 6/6, 0 omitidos | Cache, reintento, regeneración explícita, chat y procedencia D1/D2 |
| Helper de persistencia IA con proveedor HTTP local | Aprobado | Dos resúmenes y dos turnos recuperados tras reiniciar la API |
| `pip check` y compilación Python | Aprobados | Dependencias instaladas y código ejecutable |
| Sintaxis JavaScript | 67/67 archivos | Todos los `.js` y `.mjs` de `app/static/js` |
| Catálogo público reconstruido frente al snapshot real | Equivalente | 12 tablas, 33 funciones, 0 policies; diferencia normalizada vacía |

Herramientas locales verificadas: Python 3.13.5, Node 22.23.3, Docker 28.4.0, Chromium 151.0.7922.173. El PostgreSQL reconstruido es 17.11; el snapshot de producción indica 17.6. La diferencia de versión menor se excluye de la comparación de DDL.

Los logs, trazas, capturas y reportes JSON de esta ejecución se guardaron fuera del checkout en `/workspace/dation-audit/platform-mvp-phase0`. No contienen registros de clientes: los flujos crean fixtures y bases de datos desechables locales. Los helpers eliminan sus propios contenedores y procesos al terminar.

## Flujo funcional preservado

Las diez pruebas de `backend/tests/e2e/run_suite.py` usan PostgreSQL y PostgREST reales, un gateway de Storage local, API FastAPI, worker y Chromium. Las respuestas del motor y las aprobaciones se calculan y persisten; las APIs de negocio del navegador no se sustituyen por respuestas estáticas.

En desktop y móvil se comprobó:

1. Inicio/Overview → subida y validación de órdenes y flota → creación persistida del Decision Case antes de la primera corrida.
2. Mapa → configuración/revisión D1 → ejecución aceptada en cola → recarga durante ejecución → dashboard con resultado real.
3. Generación y restauración del comparativo, detalle de viaje y aprobación D1 sin recalcular el resultado seleccionado.
4. Navegación a D2, configuración/revisión, manejo de una ejecución temporal inválida, reconfiguración como nueva corrida y conservación del intento fallido.
5. Resultado y aprobación D2; acceso en pestaña nueva mediante enlace con `case_id`, `node_id` y `run_id`, recuperando el upstream aprobado.
6. Volver/avanzar, recarga, historial móvil, exportación CSV con registros y nuevo caso sin borrar el anterior.

Las otras regresiones de la suite comprueban recuperación tras reiniciar API o perder un worker, fencing de leases, idempotencia, denegación anónima de RPC, deduplicación de uploads, rechazo de Storage alterado, observabilidad y consistencia del historial. El reporte termina con `passed: true`, diez pruebas, cero errores, fallos u omisiones.

La matriz D1 utiliza cinco objetivos con evidencia del worker. El recorrido D2 examina Essential/Advanced a 1440, 768 y 390 px y verifica que la asignación upstream conserve su fingerprint. El recorrido completo desktop usa 1440 px y el móvil 390 px.

### IA: contrato integrado y límites

La suite E2E habitual deshabilita el proveedor externo de IA. Para cubrir también el trayecto completo del intérprete, se conserva el helper reproducible [`scripts/qa/platform_baseline_ai.py`](../../scripts/qa/platform_baseline_ai.py):

- Crea órdenes/flota, un caso y D1/D2 aprobadas mediante API y worker reales en el sandbox.
- Comprueba que la IA sin configurar responda HTTP 503, sin llamar al proveedor.
- Arranca un proveedor HTTP determinista en `127.0.0.1`; genera y persiste un resumen y un turno por decisión mediante los endpoints reales.
- Reinicia la API; recupera exactamente los resúmenes y mensajes. Repetir cada `turn_id` devuelve su primera respuesta sin nueva inferencia.
- Verifica cuatro llamadas al proveedor en total y compara el estado completo de corridas, caso y eventos de aprobación antes/después: permanece idéntico.

Las seis pruebas de navegador complementarias verifican la presentación cacheada D1/D2, error/reintento y regeneración explícitos, turnos idempotentes, historial de chat y procedencia cuando termina un comparativo durante una respuesta. Sus APIs son fixtures sintéticos interceptados; no equivalen al helper anterior ni a una llamada a un proveedor externo.

No se evaluaron disponibilidad, calidad, coste ni resultados de un modelo real. No se generaron resúmenes, chats, datasets, corridas o aprobaciones en producción para esta Fase 0.

### Dataset de referencia

Se usaron los fixtures V3 reproducibles existentes en `backend/tests/e2e/fixtures.py`: recorrido pequeño de órdenes/flota, matriz D1 y escenario temporal D2. El paquete externo **Golden Pallets v2 no está disponible en el repositorio**. Estas pruebas acreditan el flujo y sus invariantes, pero no se presentan como una validación contra ese paquete ni contra un dataset de cliente.

## Comandos reproducibles

Desde la raíz, con Python/backend instalados según los requisitos del repositorio, Node 22, Docker y Chromium disponibles. En el entorno de nube actual se activa primero `source /workspace/.dation-cloud/activate.sh`. Los directorios de artefactos pueden situarse fuera del checkout.

```bash
cd backend
python -m pip check
python -m compileall -q app main.py worker.py
python -m unittest discover -s tests -v

python - <<'PY'
import glob
import subprocess
raise SystemExit(subprocess.call([
    "node", "--test",
    *sorted(glob.glob("tests/test_*.js") + glob.glob("tests/test_*.mjs")),
]))
PY
```

Para verificar sintaxis de todos los módulos:

```bash
python - <<'PY'
from pathlib import Path
import subprocess
for path in sorted([*Path("app/static/js").rglob("*.js"),
                    *Path("app/static/js").rglob("*.mjs")]):
    with path.open("rb") as source:
        subprocess.run(["node", "--input-type=module", "--check"], stdin=source, check=True)
PY
```

PostgreSQL: usar un contenedor propio y desechable, esperar al servidor TCP final y ejecutar la suite con su nombre. El helper SQL crea y elimina sus propias bases de datos dentro de ese contenedor.

```bash
docker run -d --name dation-platform-baseline-pg \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17-alpine
# Esperar a que devuelva código 0:
docker exec dation-platform-baseline-pg pg_isready -h 127.0.0.1 -U postgres
DATION_SQL_TEST_CONTAINER=dation-platform-baseline-pg \
  python -m unittest discover -s tests/integration -v
docker rm -f dation-platform-baseline-pg
```

En esta ejecución un helper externo envolvió ese proceso en `try/finally` para garantizar su limpieza y comprobó la disponibilidad TCP antes de la suite.

E2E completo y persistencia IA, desde la raíz:

```bash
cd backend
DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
DATION_E2E_ARTIFACTS=/tmp/dation-platform-e2e \
  python tests/e2e/run_suite.py
cd ..
python scripts/qa/platform_baseline_ai.py --artifacts /tmp/dation-platform-ai
```

`DATION_RUNTIME_PYTHON` debe apuntar al intérprete que tiene las dependencias del backend; en otra máquina se adapta esa ruta. Los recorridos de Chromium usan por defecto `backend/.browser-venv/bin/python`, o el valor de `DATION_BROWSER_PYTHON`. Los tests detectan `/usr/bin/chromium` en este entorno.

Los seis tests focalizados de IA se ejecutaron desde `backend` con:

```bash
DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
.browser-venv/bin/python - <<'PY'
import sys
import unittest
sys.path.insert(0, "tests/browser")
from test_navigation import NavigationTests
names = [
    "test_d1_v2_ai_cached_brief_copy_chat_and_collapse_without_inference",
    "test_d1_v2_ai_loading_error_retry_regeneration_are_explicit_and_coalesced",
    "test_d2_v21_ai_cache_generation_freshness_and_chat",
    "test_d2_v21_ai_retry_approval_and_approved_state",
    "test_chat_retry_reuses_turn_id_and_older_messages_prepend",
    "test_ia_retains_and_labels_original_turn_when_comparative_finishes_mid_response",
]
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.TestSuite(NavigationTests(name) for name in names)
)
raise SystemExit(not result.wasSuccessful())
PY
```

Las trece funciones Python adicionales se ejecutaron con el helper local preexistente `/workspace/.dation-cloud/validate-function-tests.py`. Para reproducirlas sin ese archivo, desde `backend`:

```bash
python - <<'PY'
import importlib.util
import inspect
from pathlib import Path
import unittest
suite = unittest.TestSuite()
for name in ("test_assignment_filter_collapse.py",
             "test_assignment_config_visual_consistency.py",
             "test_scheduling_config_phase2_acceptance.py"):
    path = Path("tests") / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for item, function in inspect.getmembers(module, inspect.isfunction):
        if item.startswith("test_"):
            suite.addTest(unittest.FunctionTestCase(function))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

## CI existente y cobertura pendiente

El workflow [`.github/workflows/backend-tests.yml`](../../.github/workflows/backend-tests.yml) se ejecuta en pull requests a `main`, pushes a `main` y manualmente. Instala requisitos con hashes, ejecuta `pip check` y auditorías de dependencias, compila Python, verifica sintaxis JavaScript, ejecuta Python/Node, navegador sintético, PostgreSQL 17 y E2E real. El runner E2E considera fallo cualquier omisión o ausencia de pruebas; guarda diagnóstico sintético durante siete días.

Se consultó de nuevo la metadata de la [CI de `main` #39050288728](https://github.com/nicsejara/Dation/actions/runs/39050288728): `completed/success` para el SHA exacto del baseline. Todas sus etapas están aprobadas. La suite de navegador de ese árbol contiene 146 métodos y su etapa CI pasó; en esta Fase 0 se volvieron a ejecutar localmente los seis específicos de IA y los diez E2E, sin repetir manualmente los 146.

Se distingue esa CI histórica del SHA base de una futura CI del commit de documentación/helpers de Fase 0. Los resultados locales anteriores pertenecen a esta ejecución; no se inventa un nuevo run de CI para cambios todavía sin publicar.

Hueco detectado: `unittest discover` no recoge las trece funciones Python de nivel superior de los tres módulos enumerados. Pasaron con el helper explícito; el workflow actual aún no las ejecuta. El helper IA nuevo tampoco está añadido automáticamente al workflow. Son tareas concretas de cobertura para el siguiente ajuste de CI; esta auditoría mantiene intacto el workflow y no usa su estado verde como prueba de esas verificaciones adicionales.

## Equivalencia del esquema reconstruido

Se consultó únicamente el catálogo público del PostgreSQL local mediante el `SQL` de `scripts/capture_public_schema.py` dentro de una transacción `READ ONLY`. Se comparó con el snapshot de producción ya capturado en [`schema/live-catalog.json`](schema/live-catalog.json), sin volver a consultar producción ni aplicar DDL allí.

El resultado versionado está en [`schema/catalog-comparison.json`](schema/catalog-comparison.json). Coinciden tablas, columnas en orden, tipos, defaults, nullability, constraints, índices, triggers, RLS/FORCE RLS, grants por rol, firmas/cuerpos de funciones y policies públicas. Se normalizaron espacios fuera de strings SQL y el orden de colecciones y ACL; el diff quedó vacío. No se comparan filas, versión menor del servidor ni los esquemas administrados `auth`/`storage`, que requieren otro tratamiento.

## Gates antes de identidad y workspaces

El baseline actual prueba un **workspace privado compartido**, protegido con autenticación Basic y backend `service_role`. Su E2E verifica explícitamente `approved_by = shared_workspace:dation`. Las denegaciones SQL actuales para `anon` y `authenticated` no equivalen a aislamiento por tenant: todavía no hay usuarios, memberships ni autorización por workspace en estas tablas.

Antes de publicar el modelo nuevo, se necesitarán pruebas adicionales para:

- Inicio/cierre y recuperación de sesión, expiración, recuperación de contraseña e identidad de actor en aprobaciones y auditoría.
- Dos usuarios/workspaces con datos independientes: acceso propio permitido y lectura/escritura cruzadas denegadas para datasets, casos, corridas, historial, exports, aprobaciones, comparativos, resúmenes, chats y Storage.
- D1/D2 y workers conservando workspace y upstream coherentes en admisión, reintentos, proyecciones y recuperación de procesos.
- Backend con `service_role` haciendo autorización explícita por recurso; no basta con RLS cuando esa credencial la omite.
- Recarga, enlace directo y navegación sin reutilizar contexto, cache ni drafts de otra sesión o workspace.

Estos gates son cobertura pendiente de funcionalidades futuras; no son regresiones del baseline ni pruebas ya aprobadas en esta Fase 0.
