# Despliegue de Dispatch 1.0.0

API esperada: **1.0.0**. Motor Dispatch: **1.0.0**. Motor histórico: **0.2.0**. Runtime: Python **3.13**, OR-Tools **9.15.6755**.

## Activación manual en Supabase

**El código no aplica migraciones productivas automáticamente. El propietario las ejecuta en SQL Editor.**

Aplicar en este orden:

1. `supabase/migrations/20261001004934_dispatch_v1.sql`
2. `supabase/migrations/20261001193000_dataset_library.sql`

Ambas son aditivas. La segunda agrega `datasets.archived_at`, `datasets.is_sample`, un índice parcial para la biblioteca y solicita recarga de PostgREST.

Después ejecutar:

```sql
notify pgrst, 'reload schema';
```

Verificación:

```sql
select table_name, column_name
from information_schema.columns
where table_schema = 'public'
  and (
    (
      table_name = 'datasets'
      and column_name in (
        'dataset_type',
        'schema_version',
        'label',
        'is_default',
        'parent_dataset_id',
        'profile_json',
        'archived_at',
        'is_sample'
      )
    )
    or (
      table_name = 'decision_runs'
      and column_name in (
        'schema_version',
        'orders_dataset_id',
        'fleet_dataset_id',
        'input_fingerprint',
        'result_fingerprint',
        'summary_json',
        'progress_json'
      )
    )
  )
order by 1, 2;

select proname
from pg_proc
where proname in ('set_default_fleet', 'validate_dispatch_run');

select id, public
from storage.buckets
where id = 'dda-inputs';
```

El 1 de octubre de 2026 el propietario confirmó por SQL que el bucket `dda-inputs` existe y tiene `public = false`. Esa comprobación no confirma por sí sola que las columnas y funciones de ambas migraciones estén instaladas.

Con backend actualizado y autenticación válida, `GET /api/dispatch/status` debe responder `available: true`. Si las columnas existen en PostgreSQL pero el endpoint todavía las informa como no visibles, volver a ejecutar el `NOTIFY` y reintentar.

## Validación antes de activar almacenamiento

`POST /api/datasets/validate?dataset_type=orders|fleet` no depende de Supabase. Esto permite probar estructura, tipos y errores antes de aplicar las migraciones. Mientras `available=false`, la pantalla muestra “Activación pendiente”, mantiene visibles ambas cajas y bloquea guardar/continuar con una explicación.

## Cloud Run

El despliegue automático usa el buildpack actual de Google Cloud sobre Ubuntu 24; el repo está alineado con Python 3.13. El proceso de aplicación sigue siendo:

```bash
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
```

Variables existentes: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_INPUT_BUCKET`, `DATION_ACCESS_PASSWORD` y `LLM_*`. No guardar credenciales en GitHub.

Antes de uso intensivo revisar timeout, memoria y concurrencia. El POST de corrida mantiene la petición abierta; el polling consulta progreso. `DATION_STALE_RUN_SECONDS` vale 600 por defecto.

## Verificación

Desde `backend`:

```bash
python -m unittest discover -s tests -v
node tests/test_dashboard_selectors.js
node --test tests/test_dispatch_selectors.mjs
node --test tests/test_dispatch_upload_selectors.mjs
```

En despliegue verificar `/health`, `/app`, `/upload`, `/api/dispatch/status`, una validación de cada tipo, una persistencia de ambos archivos y una corrida completa.

## Baseline SQL pendiente

El repositorio aún no dispone del DDL original completo de `datasets` y `decision_runs`. No se genera un `baseline.sql` por inferencia: primero debe capturarse el esquema real mediante `information_schema`/catálogo. Esto evita versionar una reconstrucción incorrecta.

## Rollback

Replegar la aplicación anterior sin borrar columnas ni datos nuevos. No eliminar columnas de Dispatch si ya existen corridas `dispatch_v1`. No hay downgrade destructivo automático.


## Smoke test de ingesta UX

Después del deploy validar en 1440 px y 390 px:
- primera vez y datos de ejemplo;
- flota vigente + nuevas órdenes;
- archivo con errores múltiples;
- formato anterior;
- duplicado;
- error de guardado;
- activación pendiente;
- listo con avisos y botón Configurar decisión habilitado.

El script `scripts/qa/dispatch-browser.cjs` mantiene mocks para el flujo completo y
comprueba que no haya overflow horizontal.
