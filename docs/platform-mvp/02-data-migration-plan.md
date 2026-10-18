# Plan de migración no destructiva

**Diseñado en Fase 0; no ejecutado.** Esquema real y preflight: [auditoría Supabase](07-supabase-storage-audit.md), [catálogo](schema/live-catalog.json), [lineage](schema/lineage-preflight.json).

Hay 6 datasets, 8 cases y 23 runs existentes en la captura; no se consideran desechables. El workspace privado actual se convierte en un workspace legacy/default explícito. Se conservan todos los IDs, resultados, aprobaciones, filenames y referencias de Storage. No se ejecuta reset ni se mueven objetos en esta fase.

## Preparación del cambio de Fase 2

1. Releer HEAD y capturar nuevamente catálogo y conteos en una carpeta nueva. Comparar con el esquema revisado; abortar ante drift no comprendido.
2. Preparar backup de datos y Storage mediante herramientas autorizadas; comprobar restauración en entorno aislado. Los JSON de esta auditoría contienen DDL/estadísticas y **no son un backup**.
3. Ensayar la migración completa sobre baseline reconstruido + migraciones posteriores, con casos históricos, aprobaciones reemplazadas y jobs pendientes. Incluir datos de dos workspaces de prueba.
4. Ensayar rollback de imagen y compatibilidad de API/worker. Programar una ventana para detener admisiones y drenar trabajos/reconciliaciones antes del cutover; no permitir escrituras simultáneas desde una API antigua sin tenancy mientras se reciben nuevos clientes.

## Secuencia expandir → rellenar → validar → exigir

### A. Tablas de plataforma y workspace legacy

Crear `profiles`, `workspaces`, `workspace_members`, `workspace_ddas` y contrato mínimo de auditoría. RLS y permisos cerrados desde su creación. Dar un ID estable al workspace legacy, guardar ese mapeo para reanudación idempotente y vincular sólo usuarios explícitamente autorizados. Los registros históricos con actor compartido no se atribuyen retroactivamente a una persona.

### B. Columnas opcionales y backfill por dependencias

| Tabla actual | Cómo obtener workspace | Invariantes |
|---|---|---|
| `datasets` | asignación explícita de datos legacy al workspace custodio | parent y dataset mismo workspace; nombre/path/hash originales intactos |
| `decision_cases` | desde Orders y Fleet | ambos inputs del mismo workspace; IDs/nodos/state_json intactos |
| `decision_runs` | desde case o dataset legacy si no existe case | datasets, upstream y superseded run del mismo workspace |
| `dispatch_run_jobs` | desde run | request_json sólo referencia objetos de ese workspace; no fiarse de JSON recibido |
| `decision_case_reconciliations` | desde case | versión/outbox y reconciliación limitadas a ese workspace |
| `decision_approval_events` | desde run/case | append-only, actor histórico intacto |
| `decision_comparative_analyses` | desde base run | fingerprints, leases, resultado y evidencia del mismo workspace |
| `decision_explanations`, `decision_messages`, `decision_chat_turns` | desde run | caché/turn IDs nunca devuelven datos de otro workspace |
| `decision_interpretation_sources` | desde run + cada referencia de evidencia | explanation/chat/comparative coherentes con run y workspace |
| `dispatch_worker_instances` | infraestructura interna global | no tenant de cliente; nunca exponer snapshot global a usuarios |

Son 11 tablas con datos tenant y una de infraestructura global. Añadir `workspace_id` explícito a las 11 para filtros directos, auditoría y constraints. Un actor de creación futuro puede ser nullable para legado; no inventar usuarios históricos.

El trigger `protect_persistence_identity` y la inmutabilidad de approval events requieren una migración deliberada: preservar la protección de identidad/resultado y habilitar sólo el backfill técnico controlado de la columna nueva. Inspeccionar las funciones exactas antes del ALTER; no desactivar triggers indiscriminadamente ni permitir actualizaciones de eventos desde el producto.

### C. Relaciones, unicidad e índices

- Crear claves únicas `(workspace_id,id)` en tablas referenciadas y FKs compuestas para datasets, parent, case, run, upstream, supersession y evidencia. Una FK sólo por UUID no impide referencias cruzadas.
- Validar constraints por etapas y luego exigir `workspace_id NOT NULL`. No activar NOT NULL con filas sin resolver. Revisar locks y volumen antes de `VALIDATE CONSTRAINT`/creación de índices.
- Sustituir de forma segura `datasets_dispatch_hash_key (dataset_type,sha256)` por la variante `(workspace_id,dataset_type,sha256)` con el mismo predicado. La deduplicación legacy por hash también añade workspace.
- Sustituir `datasets_one_default_per_type` global por `(workspace_id,dataset_type) WHERE is_default`; `set_default_fleet` recibe contexto y sólo cambia filas propias. No dejar ambas unicidades global y tenant activas al incorporar el segundo workspace.
- Mantener unicidad de aprobación actual por `(case_id,node_id)` y verificarla junto con workspace; no reiniciar histórico ni reemplazar resultados.
- Índices de listas por `(workspace_id,created_at DESC,id DESC)`, estado/tipo según consultas reales. Las colas internas conservan sus índices de scheduling/lease; limitar vistas operativas de producto por workspace.
- No convertir `input_signature` en identidad global de un Data Pack: es un índice no único actual. Los caches/reutilización deben incluir workspace sin alterar fingerprints históricos de resultados.

### D. API, RPC y worker coordinados

Introducir contexto obligatorio en todos los repositorios/servicios y variantes tenant-aware de RPC antes de retirar contratos legacy. Las 33 funciones se clasifican en dominio, infraestructura y trigger; ninguna función con datos de negocio expuesta al cliente puede aceptar un ID sin ownership. Atención especial a `approve_decision_run_version`, `set_default_fleet`, listas/history, admission/finish/cancel, IA/evidencia y reconciliación. Consultas agregadas de colas y capacidad global sólo son internas.

El worker reclama globalmente como servicio, obtiene workspace del run/job persistido y valida la igualdad de todas las referencias. Reintentos, leases, cancelación, outbox y admisión deben conservar idempotencia. Desplegar API y worker coordinadamente; una imagen previa a tenancy no es compatible con una base que ya contiene clientes distintos.

### E. Atribución sin falsificar el pasado

Hoy `decision_runs_approved_by_check` sólo permite `shared_workspace:dation`; también existen validadores y RPC que fijan ese actor. En Fase 2 adaptar el contrato a un actor de usuario autenticado verificable manteniendo el valor histórico. En Fase 8 agregar owner/approver y asignaciones. Conservar `approved_by` como snapshot histórico y sumar una referencia nullable al actor Auth, o formalizar un tipo de actor; elegir una sola fuente coherente y migrar checks/RPC/tests juntos. No cambiar aprobaciones históricas ni escribir UUIDs sobre un CHECK incompatible.

### F. RLS y permisos

Las 12 tablas actuales ya tienen RLS sin policies y sin grants anon/authenticated. La API usa service role y lo bypassa. Mantener deny-by-default; añadir policies/grants mínimos según [modelo de seguridad](03-security-model.md). Validar tanto API como acceso REST directo con JWT A/B. No dar EXECUTE a `authenticated` sobre funciones históricas que aún ignoren workspace.

## Storage: transición sin mover archivos históricos

Nuevos uploads: `workspace_id/dataset_id/canonical_filename`, generado por servidor. Mantener `storage_bucket`/`storage_path` existentes para lecturas históricas; autorizarlas por dataset antes de descargar el objeto. No deducir ownership exclusivamente del primer segmento de un path legacy.

No hace falta migrar los seis objetos actuales para aislarlos desde backend. Si en otra fase se decide moverlos: manifest privado de origen/destino + checksum, copiar primero, verificar bytes, actualizar metadata transaccionalmente, mantener origen durante ventana de rollback y borrar sólo tras verificar ausencia de referencias. Nunca mover masivamente desde SQL sin procedimiento de compensación.

Archive mantiene objetos. Hard delete futuro requiere comprobar uso por case/run/parent/evidencia; si está referenciado, rechazar y ofrecer archive. DB + Storage no forman una única transacción: registrar intención/reintento y compensar fallos. No existe actualmente una ruta de borrado funcional de datasets que deba mantenerse.

## Gate antes de abrir múltiples empresas

- Cero `workspace_id` null; cero relaciones cruzadas; conteos y hashes históricos preservados.
- Cero huérfanos DB/Storage, lineage y referencias de state_json correctos; snapshots históricos y resultados idénticos.
- Dos workspaces con CSV idénticos no comparten registros, flota default, casos, IA, export ni deduplicación.
- User A/B, viewer, disabled y JWT vencido: aislamiento API + REST + RPC + Storage. Rutas legacy incluidas.
- Carga → case → D1 → aprobación → D2 → aprobación → logout/login → restore → export, más worker/retry/outbox.
- Restore/rollback ensayados, observabilidad sin secretos, despliegue con credenciales operativas.

## Rollback

Antes de nuevos tenants: volver a imagen validada, manteniendo columnas/tablas aditivas y los paths originales. Después de nuevos tenants: **no volver a una API sin tenancy**. Usar una versión anterior que preserve autorización o mantenimiento bloqueado; corregir hacia adelante. No retirar NOT NULL/RLS ni eliminar tablas para que una imagen antigua arranque. Un reset limpio queda fuera de este plan y requeriría una instrucción explícita independiente.
