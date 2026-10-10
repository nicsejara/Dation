# Fase 6: regresiones de extremo a extremo

CI ahora recorre Chromium → HTTP → API → cola durable → worker independiente →
motor real → PostgREST → PostgreSQL 17. Esto completa el hallazgo F16: las pruebas
unitarias, de navegador con respuestas sintéticas y SQL separadas no acreditaban
que esas capas funcionaran juntas.

## Cobertura

| Recorrido | Comprobaciones |
| --- | --- |
| Acceso e ingesta | App y API privadas, RPC denegado al rol anónimo, CSV inválido sin registro, deduplicación por hash y rechazo de bytes alterados al ejecutar. |
| Recuperación durable | POST 202 con Location/Retry-After, trabajo conservado tras reiniciar la API, reintento del mismo UUID y conflicto de intención. Un worker real muere después de reclamar; otro recupera el lease vencido y el token anterior no puede sobrescribir el resultado. |
| Persistencia y trazabilidad | Assignment y Scheduling reales, upstream correcto, aprobación idempotente con actor compartido, reemplazo de Assignment, Scheduling stale, paginación y resumen vigente fuera de la página, rechazo de reactivación histórica y outbox vaciado. |
| Navegador completo | Subir Orders/Fleet, crear el caso, ejecutar y aprobar ambos nodos, recargar una ejecución pendiente, configurar Scheduling sin conservar el run de Assignment, atrás/adelante, enlace en pestaña nueva, mapa sin consultas en reposo, historial móvil y CSV descargado con registros. |

Los cuatro tests agrupan estos recorridos; cada ejecución comprueba resultados
persistidos y estados observables. Las 27 regresiones de navegador anteriores
conservan sus escenarios de errores, cancelación de observación, borradores y
respuestas tardías. Las 27 pruebas SQL siguen cubriendo instalación/upgrade,
historial superior a 1.000 corridas y concurrencia transaccional.

Python descubre `test_*.py`; Node descubre `test_*.js` y `test_*.mjs`; navegador
y E2E tienen descubrimiento independiente con ese mismo patrón. Las 13 funciones
Python antes omitidas siguen integradas mediante `load_tests`. Node informa
19 unidades: las 18 pruebas existentes más el archivo de selectores del dashboard
que antes se ejecutaba como script independiente. No se añade cobertura ficticia.

## Entorno y ejecución

Desde `backend`, con Python 3.13, runtime instalado desde el lock, Docker disponible
y Playwright/Chromium del lock de navegador:

```bash
python -m unittest discover -s tests -v
node --test tests/test_*.js tests/test_*.mjs
.browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_*.py' -v
DATION_E2E_ARTIFACTS=/tmp/dation-e2e-artifacts python tests/e2e/run_suite.py
```

El runner E2E crea una red Docker, PostgreSQL 17 sin puerto publicado, una base
vacía con el baseline y todas las migraciones posteriores, y PostgREST oficial
v14.0 fijado por digest. Publica REST sólo en loopback. Inicia la API y el worker
como procesos separados, genera JWT efímeros y sustituye las credenciales y URLs
productivas. No requiere claves reales. Espera al servidor PostgreSQL definitivo
por TCP para evitar el servidor temporal de `initdb`.

Storage es una **fixture HTTP local**: conserva los bytes realmente subidos y
ejercita descarga, hash, autorización y objetos inmutables. Las respuestas SQL,
los resultados del motor y las respuestas API del navegador no se simulan. Esta
suite no acredita el servicio alojado de Supabase Storage, sus políticas de red,
IAM de Cloud Run ni llamadas a proveedores LLM. Las comprobaciones de producción
se registran por separado.

`DATION_BROWSER_PYTHON` puede señalar otro Python con Playwright;
`CHROMIUM_EXECUTABLE` puede señalar otro Chromium. La API y Storage usan puertos
loopback libres; el navegador rechaza una URL que no sea `127.0.0.1`. Cada suite
elimina exclusivamente sus contenedores, red, procesos y directorios, incluso
ante errores. Reinicios, corrupción de archivos y adelanto del vencimiento del
lease ocurren únicamente en ese entorno descartable.

CI impone 20 minutos al job; arranques y ejecuciones tienen esperas acotadas.
Un fallo de infraestructura o una suite vacía/omitida hacen fallar el gate. Los
artefactos sintéticos incluyen resultado JSON, traza Chromium y, ante fallo,
captura y logs de procesos; se conservan siete días. CI incluye el diagnóstico
en anotaciones y mantiene el código de salida del runner.

## Publicación

Esta fase modifica pruebas, CI y documentación; no cambia el runtime ni requiere
SQL productivo. Después de CI verde del commit exacto, el merge en `main` usa el
pipeline existente: imagen compartida → worker Ready → API. La verificación
posterior comprueba Cloud Build, salud, acceso privado, dependencias, assets y
lecturas de casos/historial. No se ejecutan reinicios, corrupción ni nuevas
escrituras de QA sobre los datos de operadores.

La matriz local de validación es 320 Python, 19 unidades Node, 27 recorridos de
Chromium con API sintética, 27 tests sobre PostgreSQL 17 y cuatro E2E completos.
Los identificadores finales de CI, commit y Cloud Build se registran en el PR de
publicación.
