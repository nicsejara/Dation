# UX04 — diseño y gates de código

## G0: baseline y decisión

PR #118 integrado el 14/11/2026 22:38:58 UTC. Main inicial: `4b66044806f93535a363ad8829c8eb003644958e`. Rama única `feat/saga-ux04-unified-journey`. Inicio registrado 22:46:22 UTC (19:46:22 ART). Regresión inicial: 23 browser tests UX01/02/03 PASS (118,807 s).

No se crea un Case para obtener un ID de carga. La preparación es un journal privado separado, ligado al actor/workspace y a una Model Version publicada. Reutiliza compile_contract, normalize_input, hashes y el servicio canónico de Pack. No hay cambios en motores, normalizadores, Run ABI, aprobaciones de dominio ni infraestructura.

## G1: contratos y persistencia

Migración aditiva generada con CLI: `20261114225017_unified_decision_journey.sql`. Sólo sandbox local; producción pendiente de GO SQL separado.

- `dation_private.journey_preparations`: UUID, actor/workspace, Model Version, parent opcional, revisión, estado, expiración, intención congelada y Case consumido.
- `journey_uploads`: UUID estable, entidad, hash de intención, metadata privada verificada, estado y selección. No datasets ni Cases ficticios.
- `journey_case_events`: linaje y cierre auditado. El archivado administrativo anterior no equivale a cierre por finalización.
- RLS forzada, sin grants de tabla para anon/authenticated/service_role. Una RPC del servidor con search_path fijo, EXECUTE sólo service_role y comprobaciones de membresía, DDA, actor propietario y permisos en cada operación. Sigue el límite de confianza existente del backend: el navegador nunca recibe service_role.
- Lock de workspace y luego Case/preparación, compatible con admisión/Pack/contexto. Revisiones CAS e identidades únicas. El cierre reevalúa el Graph del servidor y compara un token de snapshot dentro del lock SQL; comprueba además trabajos/candidatos pendientes.
- La ruta guiada de publicación exige que no haya ninguna corrida admitida, dentro del mismo lock que la publicación. La API histórica de Pack conserva versionado y STALE.

API nueva (requiere ambos flags):

| Método/ruta | Contrato |
| --- | --- |
| GET/POST `/api/platform/data-preparations` | Lista privada / UUID + model_version_id + parent_case_id opcional |
| GET `/{preparation_id}` | Metadata, contratos exactos, candidatos y reportes; sin paths privados |
| POST `/{id}/validate/{entity}` | CSV + contract_hash; no guarda bytes inválidos |
| POST `/{id}/uploads/{entity}` | upload_id + revisión + contract_hash + CSV |
| POST `/{id}/uploads/{upload_id}/recover` | Recupera bytes del journal sin nueva identidad |
| PUT `/{id}/owner` | Intención de Data Owner con CAS y elegibilidad real |
| POST `/{id}/unselect/{entity}` | Retira selección, preserva bytes hasta limpieza |
| POST `/{id}/finalize` | revisión + DTO canónico de creación del Case |
| POST `/{id}/cleanup` | Sólo objetos de preparación expirada/consumida |
| GET `/api/platform/logistics-cases/{id}/journey` | Corridas existentes, elegibilidad de cierre, token, metadata de lifecycle |
| POST `/{id}/journey/publish` | Publicación guiada con guard anti-carrera; DTO Pack existente |
| POST `/{id}/close` | Token de snapshot; servidor revalida vigencia, permiso y trabajo pendiente |

Entidades exactas: `transport_demand` / `transport_resources`. Archivos CSV UTF-8, máximo 10 MiB; límite de filas/columnas del compilador y normalizador vigentes. Paths opacos generados por servidor, raw y JSON privados con hash/tamaño exactos, sin upsert ni URL pública. El cliente guarda IDs y borradores de configuración existentes, nunca bytes/filas de CSV.

## Recuperación e idempotencia

1. Verificar todos los candidatos seleccionados, bytes originales/normalizados y contrato antes de comenzar la creación.
2. Congelar DTO de creación y su hash en FINALIZING bajo CAS. UUID de creación único entre preparaciones.
3. Llamar al servicio canónico de creación: mismo UUID y cuerpo en cada reintento.
4. Materializar uploads del Case mediante UUID derivados de los candidatos; reutilizar normalización, deduplicación, Storage y journal existentes.
5. Publicación inicial con UUID derivado de preparation_id y revisión inicial 1, preservando replay antes de CAS mutable.
6. Asignar Data Owner sólo con permiso/elegibilidad vigentes. Una asignación parcial se reconcilia, no se simula.
7. Marcar CONSUMED y registrar linaje. Consultar Case, Pack y Graph antes de navegar.

Si la creación se confirmó y falló publicación/Owner, queda FINALIZING con la intención durable y el mismo ID dentro de creation_body. No compensar borrando Cases, Packs ni snapshots. Si se pierde respuesta después de publicar, replay reconoce la misma publicación. Si se pierde respuesta tras consumir, se lee el mismo Case sin reconstruir objetos limpiados. Una intención diferente falla cerrada.

## Flags, retención y costo

Dos cierres independientes: `DATION_UNIFIED_JOURNEY_ENABLED=false` por defecto en runtime y `platform_release.unified_journey_enabled=false` en SQL. Sin el flag runtime no se invoca la RPC nueva y el flujo anterior funciona aunque la migración aún no esté instalada. Con runtime ON pero schema/RPC ausente no se declara activación válida.

TTL de preparación no finalizada: 24 horas. Máximo 5 sesiones pendientes o con bytes sin limpiar por actor, 10 intentos por sesión y dos selecciones (una por entidad). Cada intento conserva raw/normalizado de hasta 10 MiB cada uno: cota conservadora de 200 MiB por sesión y 1.000 MiB por actor hasta limpiar. FINALIZING se conserva para reparar; no eliminarlo automáticamente. La cota evita nuevas cargas ilimitadas tras expirar sin limpieza.

La limpieza es explícita/bajo demanda y sólo borra paths exclusivos del stage, nunca objetos de Pack. Consumir copia mediante el servicio canónico a paths del Case verificados, por lo que la limpieza posterior del stage es segura. Fallos de limpieza conservan los objetos para reintentar. Sin Scheduler ni procesos residentes. No se promete borrado físico al cumplir TTL: el propietario debe ejecutar limpieza bajo demanda; Storage, requests y tráfico pueden generar cargos residuales según plan. Los journals/linaje/auditoría se conservan.

## Compatibilidad y rollback

- Feature OFF conserva el wizard UX01–03 y rutas históricas.
- Feature ON adapta rutas históricas de datos a Core02 del mismo Case; con corridas, sólo lectura y derivación explícita.
- Las APIs históricas de Pack y matemáticas no cambian su semántica.
- Rollback: flags OFF y revisión anterior por digest; conservar migración aditiva, datos, linaje y journals para recuperación. No DROP ni reset.
- GO_MERGE, GO_SQL, GO_PUBLISH_IMAGE, GO_CLOUD_RUN, GO_PROMOTE y GO_ENABLE_STAGING_FEATURE = NO.
