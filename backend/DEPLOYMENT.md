# Despliegue de Dispatch 1.0.0

API esperada: **1.0.0**. Motor nuevo: **1.0.0**, esquema `dispatch_v1`. Motor histórico: **0.2.0**. Python **3.13**, OR-Tools **9.15.6755** fijado en `requirements.txt`.

## Activación manual en Supabase (propietario)

**Esta entrega no aplica migraciones productivas.** La puerta de la fase 2 del prompt reserva esa acción y su confirmación al usuario.

1. Verificar proyecto y respaldo. Revisar `supabase/migrations/20261001004934_dispatch_v1.sql` desde la raíz del repositorio.
2. Ejecutar el archivo completo en SQL Editor del proyecto correspondiente. Está encapsulado en una transacción y es aditivo/idempotente; no borra registros ni altera las políticas RLS existentes.
3. Confirmar las columnas nuevas en `datasets` y `decision_runs`, los índices y `set_default_fleet`. Actualizar la caché de esquema PostgREST si fuera necesario (`NOTIFY pgrst, 'reload schema';`).
4. Con backend actualizado y autenticación válida, consultar `/api/dispatch/status`; debe responder `available: true`.
5. Subir `sample_data/v1/fleet.csv`, marcarla vigente y subir `orders.csv`. Ejecutar los casos de la guía `sample_data/v1/README.md`.

La inspección previa fue de solo lectura. Se observó `dataset_id NOT NULL`, índices SHA no únicos y RLS activado sin políticas; por eso se preserva el acceso del servidor con service role y no se expone una API de base de datos al navegador. No se ejecutó la migración en el proyecto del usuario ni se afirma una validación SQL productiva.

## Backend / Cloud Run

Instalar `pip install -r backend/requirements.txt`. El despliegue automático de Cloud Run usa el buildpack `latest` (stack google-24 / Ubuntu 24), por lo que el runtime del repositorio se mantiene en Python 3.13, soportado por ese builder. Si el directorio de build es `backend`, respetar su `.python-version` y Procfile:

```bash
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
```

Variables existentes: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_INPUT_BUCKET`, `DATION_ACCESS_PASSWORD`, configuración `LLM_*`. No incluir credenciales en GitHub. Conservar el bucket privado y los secretos actuales.

Revisar timeout del request, memoria y concurrencia reales antes de activar. Se recomienda empezar con concurrencia 1 para tareas CPU y timeout de al menos 300 s, sujeto a medición real. El POST mantiene la petición abierta, mientras el polling consulta progreso. No se lanzan procesos en paralelo: la configuración vCPU del Cloud Run real no fue accesible para comprobarla. `DATION_STALE_RUN_SECONDS` vale 600 por defecto. El presupuesto global del motor incluye callbacks de progreso y puede fallar si Supabase responde muy lentamente; se informa como error sin publicar resultado parcial.

La publicación en GitHub no demuestra por sí misma un despliegue correcto en Cloud Run. Verificar logs de build, `/health`, `/app`, `/upload`, endpoint autenticado de estado, y una ejecución persistida antes de considerar activado el MVP.

## Verificación local y CI

Desde `backend`:

```bash
python -m unittest discover -s tests -v
node tests/test_dashboard_selectors.js
node --test tests/test_dispatch_selectors.mjs
```

Desde raíz: `PYTHONPATH=backend python scripts/benchmark_dispatch.py`. Ver `docs/validation-dispatch-v1.md` para alcance de pruebas y resultados medidos. CI ejecuta Python 3.13, Node 22, compilación, sintaxis JavaScript y tests.

## Rollback sin pérdida

Replegar la versión anterior de la aplicación manteniendo columnas, índices, funciones y datos nuevos. Las corridas `dispatch_v1` seguirán almacenadas aunque esa interfaz anterior no sepa abrirlas; volver a la versión nueva para visualizarlas. No borrar columnas con corridas existentes. Antes de migrar, el fallback legacy y sus endpoints permanecen disponibles. No hay downgrade SQL destructivo automático.
