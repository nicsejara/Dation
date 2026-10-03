# Despliegue de Dispatch 2.2.0

API esperada: **1.0.0**. Motor Dispatch: **2.2.0**. Motor histórico: **0.2.0**. Runtime: Python **3.13**, OR-Tools **9.15.6755**.

## Activación manual en Supabase

**El código no aplica migraciones productivas automáticamente. El propietario las ejecuta en SQL Editor.**

Aplicar en este orden:

1. `supabase/migrations/20261001004934_dispatch_v1.sql`
2. `supabase/migrations/20261001193000_dataset_library.sql`
3. `supabase/migrations/20261002184751_dispatch_v2_integrity.sql`

Las tres son aditivas. La segunda agrega `datasets.archived_at`, `datasets.is_sample`, un índice parcial para la biblioteca y solicita recarga de PostgREST.

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

El 2 de octubre de 2026 se verificó en el proyecto productivo la migración `dispatch_v2_integrity`: el trigger acepta `dispatch_v1` y `dispatch_v2`, valida coherencia con `result_json.schema_version` y existe el índice por versión/fecha.

Con backend actualizado y autenticación válida, `GET /api/dispatch/status` debe responder `available: true`. Si las columnas existen en PostgreSQL pero el endpoint todavía las informa como no visibles, volver a ejecutar el `NOTIFY` y reintentar.

## Validación antes de activar almacenamiento

`POST /api/datasets/validate?dataset_type=orders|fleet` no depende de Supabase. Esto permite probar estructura, tipos y errores antes de aplicar las migraciones. Mientras `available=false`, la pantalla muestra “Activación pendiente”, mantiene visibles ambas cajas y bloquea guardar/continuar con una explicación.

## Logistics Data Pack V3

Phase 1 introduces `orders_v3` and `fleet_v3` without adding database columns. `datasets.schema_version` is already text and `profile_json` is JSONB, so no Supabase migration is required.

After deploy verify that `GET /api/dispatch/contracts` reports `orders_v3` and `fleet_v3`. The fleet template must contain `vehicle_id` and `base_site`, and must not expose `fleet_pool_id` or `units_available`. A new Fleet V3 row represents one real truck. Historical Fleet V1/V2 datasets remain readable through in-memory adapters.

Also verify Decision Readiness:
- a minimal valid Data Pack unlocks **Asignación de carga**;
- missing scheduling columns do not block Assignment;
- completing `estimated_dispatch_date`, speed/hours/status/availability marks Scheduling data-ready but it remains locked until the upstream decision is approved in Phase 2;
- completing `license_plate` marks Final Assignment data-ready.

The current Dispatch 2.2 temporal engine remains available through internal compatibility fields during this transition. Those internal fields must never appear in the V3 templates.

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
- Data Pack mínimo con Asignación disponible;
- Data Pack completo con Scheduling y Final Assignment marcados como data-ready;
- columnas opcionales vacías sin falsos errores;
- CTA Continuar habilitado sólo cuando Assignment está disponible.

El script `scripts/qa/dispatch-browser.cjs` mantiene mocks para el flujo completo y
comprueba que no haya overflow horizontal.


## Smoke test — Decision Chain Phase 2

No requiere migración adicional de Supabase.

Después del deploy verificar:

1. Cargar o seleccionar Orders V3 + Fleet V3 válidos.
2. El CTA de Cargar datos debe abrir **Mapa de decisiones**, no Configurar decisión.
3. Assignment debe aparecer `AVAILABLE`.
4. Scheduling y Final Assignment deben aparecer `LOCKED`.
5. Ejecutar Assignment:
   - el nodo pasa a `RUNNING`;
   - al completar, pasa a `REVIEW`;
   - la corrida conserva `decision_case.case_id` y `node_id=logistics_assignment`.
6. Aprobar la decisión:
   - Assignment pasa a `APPROVED`;
   - Scheduling pasa a `AVAILABLE` si su Data Readiness está completo;
   - o a `NEEDS_DATA` si faltan columnas.
7. Cambiar Orders o Fleet:
   - se crea un caso nuevo;
   - el caso previo se muestra como `STALE`;
   - la aprobación anterior no se reutiliza.
8. Abrir una corrida histórica sin `decision_case`:
   - puede visualizarse;
   - no debe ofrecer **Aprobar decisión** para el caso activo.
9. En móvil, el mapa debe apilar los tres nodos sin overflow horizontal.
