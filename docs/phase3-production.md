# Fase 3: ejecución recuperable y publicación

Destino: Cloud Run `dation-core`, región `us-west1`, proyecto `dation-510100` (número `469052310590`), Supabase `gijiinufjjurgfeehufj`. El usuario autorizó publicación directa en producción. Los cambios de las Fases 0–2 se publican primero por el Cloud Build ya conectado a GitHub `main`; no requieren la migración siguiente.

## Comportamiento

`POST /api/runs?run_id=<uuid>` devuelve `202`, `Location` y `Retry-After`, una vez confirmados la corrida y el trabajo en una transacción. Repetir el UUID con la misma intención devuelve esa corrida incluso si el upstream cambió después. Una configuración diferente devuelve `409`; la cola llena devuelve `429`. La capacidad predeterminada es 32, ajustable mediante `DATION_MAX_QUEUED_RUNS`.

El worker `python worker.py` trabaja fuera de Uvicorn, una corrida por proceso. Claims con `FOR UPDATE SKIP LOCKED`, leases de 120 segundos y heartbeat evitan propietarios simultáneos. Un reinicio recupera el mismo UUID; un worker con lease anterior no puede guardar. Tres intentos y treinta minutos acotan recuperación y espera. El progreso se agrupa sin bloquear el solver. Los archivos se verifican contra SHA256 y el trabajo conserva motor, versión, configuración y upstream. No cambian los motores ni sus cálculos.

Resultado terminal y outbox de reconciliación se confirman juntos. Un fallo al sincronizar el mapa no cambia `completed` a `error` ni invalida una aprobación ya guardada. El worker reintenta la proyección con backoff; el acknowledgment por versión conserva un cambio concurrente. GET de corridas y perfiles no persiste, expira ni recalcula estados. La renovación explícita de perfiles usa POST. El diagnóstico consulta el catálogo autorizado de PostgREST y nunca ejecuta `set_default_fleet` ni interpreta 401/403 como éxito.

`POST /api/runs/<uuid>/cancel` es un comando explícito y bloquea resultados tardíos. Navegar a otra pantalla cancela observación local; el trabajo durable continúa y puede recuperarse mediante su enlace.

## Orden de publicación

1. CI del commit exacto debe estar verde: unittest, Node, navegador sintético, auditorías y PostgreSQL real. Antes de cambiar tráfico registrar la revisión productiva actual. Esperar que terminen las ejecuciones antiguas en vuelo: las anteriores al cambio no tienen trabajo recuperable.
2. Configurar `SUPABASE_ACCESS_TOKEN` y `GCP_ACCESS_TOKEN` en el entorno seguro. La clave de datos de Supabase no permite DDL. Google requiere acceso a proyecto, Cloud Build, Artifact Registry, Cloud Run y uso de la cuenta de servicio y los secretos existentes. No incluir valores en GitHub ni argumentos de comandos.
3. Ejecutar `python scripts/apply_production_queue.py`: aplica sólo `20261010100000_dispatch_durable_jobs.sql` sobre las siete migraciones históricas, en una transacción, y verifica tablas, RPCs, triggers y RLS. No ejecutar `tests/integration/base_schema.sql` en producción: es exclusivamente el fixture descartable de QA. La migración no convierte ni reescribe corridas históricas.
4. En la rama de Fase 3 validada y limpia, ejecutar `python scripts/deploy_production_phase3.py`. El script valida proyecto, CI y catálogo, construye una imagen con el SHA en el repositorio Artifact Registry existente, reutiliza la configuración y referencias Secret Manager de la API, y crea primero `dation-core-worker`. Usa mínimo 1, máximo 2, CPU permanente, una ejecución por proceso y 2 GiB. Conserva IAM y variables de la API cuando actualiza su imagen. Cloud Run usa la API oficial global `run.googleapis.com/v1/projects/.../locations/...`, compatible con el secreto del proxy; la ruta regional de gcloud no está habilitada en este entorno. Espera generación y revisión nuevas, retirando el nombre inmutable de la revisión anterior.
5. Comprobar Ready del worker y API, revisión e imagen exactas, `/health`, autenticación de `/app`, módulos servidos y `GET /api/dispatch/status` con `available=true`. Verificar lectura de histórico, navegación y Assignment → aprobación → Scheduling con un caso controlado; simular reinicio en un entorno aislado, como en las pruebas SQL, sin interrumpir decisiones de operadores.
6. Incorporar la misma revisión en GitHub `main`. Su despliegue automático sólo debe activarse después de migración y worker. Registrar también el Cloud Build disparado por `main` y verificar otra vez la revisión que recibe tráfico.

## Validación y rollback

CI integra 12 pruebas SQL de transacciones reales sobre PostgreSQL 16, incluyendo admisión concurrente, fencing, replay, capacidad, deadline, cancelación y outbox. El fixture histórico es mínimo y no representa un baseline completo de Supabase. Las pruebas Python incluyen ejecución real de Assignment con writer leased, conflictos, fallos de proveedor, aprobación con proyección pendiente y pureza de GET; el navegador usa API sintética, no prueba persistencia productiva.

Rollback: devolver el tráfico de `dation-core` a la revisión registrada con `gcloud run services update-traffic dation-core --project=dation-510100 --region=us-west1 --to-revisions=<revision>=100` desde Cloud Shell u otro entorno que habilite el endpoint regional. En este entorno usar la ruta global indicada arriba y actualizar únicamente `spec.traffic` a la revisión registrada. Conservar la migración aditiva y permitir que el worker termine los trabajos ya aceptados; no eliminar tablas o historial. Antes de activar una API anterior, esperar los trabajos en vuelo y mantener el límite operacional de una ejecución por worker.

La implementación y CI no equivalen a una publicación. La activación productiva del 10 de octubre de 2026, con revisión, imagen, migración, worker y prueba de persistencia real, está registrada en [production-release-status.md](production-release-status.md).
