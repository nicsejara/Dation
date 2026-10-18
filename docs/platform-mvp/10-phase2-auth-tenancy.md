# Fase 2 · Auth, identidad y aislamiento

Implementación autorizada el 18 de octubre de 2026. Conserva los motores y los datos existentes. La autorización posterior de Fase 3 incluye el cierre de esta frontera antes de desplegar ambas.

## Contrato de acceso

Supabase Auth administra contraseñas, confirmación de email, ingreso, refresh y recuperación. El BFF `/auth/*` entrega sólo el access token de Supabase a JavaScript; el refresh queda en cookie HttpOnly, SameSite y Secure en hosts públicos. Signup/recovery usan PKCE y callbacks del mismo navegador. Mutaciones de cookies exigen Origin coincidente. El frontend mantiene el token de acceso en memoria y añade `Authorization: Bearer` a `/api/*`; cookies solas no autorizan operaciones de negocio. HTTP Basic deja de aceptar solicitudes.

`app/platform/jwt.py` verifica firma ES256/RS256, issuer, audience `authenticated`, exp, iat y subject UUID mediante PyJWT/cryptography. JWKS se cachea cinco minutos; un kid nuevo puede refrescar las claves con límite de cinco segundos. Un fallo de verificación nunca recurre a Basic ni a un workspace predeterminado. La revocación de refresh no invalida retrospectivamente un JWT aún vigente; la configuración productiva usa 15 minutos para access tokens y cada request revalida la membresía.

`platform_identity` crea el profile, resuelve membresía activa y comprueba estado del workspace. Una membresía se selecciona automáticamente. Con varias, exige una preferencia previamente validada; no toma la primera. Sin membresía aparece Workspace Setup; una membresía invitada/deshabilitada no autoriza crear un workspace alternativo para eludir su estado. No hay switcher. La asignación de invitaciones queda preparada en el modelo para la fase de colaboración.

El workspace heredado tiene un ID fijo. Su propietario se vincula mediante el email autorizado en `dation_private.legacy_owners`; sólo un usuario de Auth con ese email confirmado puede reclamarlo. Ningún primer signup recibe datos históricos. El script no crea contraseñas ni envía mensajes. El usuario debe registrarse y confirmar su correo para su primer acceso.

## Datos, API, RPC y Storage

La migración añade profiles, workspaces, workspace_members, workspace_ddas y audit_events. La creación del workspace inserta perfil/membresía admin/entitlements/audit en una transacción. Logística se habilita y los demás DDAs quedan `coming_soon`; la gestión comercial de entitlements corresponde a su fase posterior.

Once tablas de cliente reciben workspace_id, FK, índices, NOT NULL y referencias compuestas. Datasets deduplica por workspace/tipo/hash y permite una flota predeterminada por workspace/tipo. Ownership queda inmutable. Las nuevas aprobaciones guardan `user:<uuid>` y FK al usuario; las aprobaciones anteriores conservan actor y fecha. La excepción de backfill de eventos/comparativos sólo existe dentro de la transacción de migración y se elimina antes del commit.

Todas las operaciones de negocio con la clave service pasan por `app/platform/repository.py`, que añade filtros/payload de workspace. No existe un contexto predeterminado. Las RPC privilegiadas heredadas se trasladan a `dation_private`; no quedan disponibles directamente por REST. `platform_rpc` revalida membresía, rol y ownership de los IDs dentro de la transacción antes de llamar la función permitida. Listas, defaults y snapshots operativos se filtran por workspace. Constraints verifican relaciones entre datasets, casos, corridas, parent/upstream/supersession, turnos y evidencia. El estado JSON del caso también valida referencias.

RLS habilita lecturas autorizadas por membresía en las relaciones públicas pertinentes y no concede escrituras directas a usuarios. Policies y ACL bloquean acceso cruzado; las intenciones/leases de jobs, outbox y comparativos permanecen internas. Las pruebas prueban RLS con JWT asimétrico contra PostgREST real. Admin/Operator pueden operar; Viewer consulta y exporta, sin subir, ejecutar, aprobar, generar IA o comparativos. El perfil propio sólo permite cambiar nombres. Disabled no accede. Objetos de otro workspace devuelven 404; capacidades prohibidas, 403.

Los archivos nuevos usan `workspace_id/dataset_id/canonical_filename`. El backend no acepta claves arbitrarias y SQL valida el namespace. Los archivos anteriores conservan sus rutas. Antes de descargar bytes, el repositorio busca una fila autorizada por workspace, bucket y path. Storage sigue privado y sin acceso directo de navegador. Si falla el guardado de metadata se intenta la compensación del upload, sin borrar datasets existentes.

Los jobs y el outbox persisten workspace_id. El worker obtiene contexto desde la fila, nunca desde request_json. Claim/report son infraestructura global fuera de las rutas de producto; heartbeat/finish están limitados a la operación y lease existentes. La conciliación vuelve a vincular el contexto para cada caso. Los fingerprints anteriores de intenciones terminadas conservan compatibilidad de replay; no se recalculan resultados históricos.

## Verificación y publicación

`tests/e2e/test_tenancy.py` comprueba dos workspaces/usuarios: dedup/defaults, listas, archivos, casos, corridas, parent y JSON IDs, lectura REST/RLS, RPC retiradas, Storage privado, viewer/disabled, JWT vencido/algoritmo/firma/issuer/audience, workers y cookies/CSRF/refresh/logout. Se ejecuta sobre el esquema final, con API y worker reales. La Auth fixture de loopback firma JWT ES256 y reproduce el contrato HTTP; no certifica entrega de correo real. Las pruebas unitarias adicionales verifican JWKS/rotación, contexto concurrente, PKCE y fallos cerrados.

`backup_platform_identity.py` capturó 12 tablas, 91 registros y seis archivos existentes en un directorio privado fuera del repo. Restauró en PostgreSQL propio, validó las FK y aplicó ambas migraciones; los hashes de la evidencia anterior y de los archivos se conservaron. La restauración local difiere constraints de FK y desactiva sólo triggers USER durante la carga histórica, luego valida/rearma antes de migrar. No se desactivan triggers para cargar datos en producción.

Cutover con `release_platform_identity.py`: congelar escrituras tras drenar jobs/outbox, capturar/restaurar backup fresco, aplicar ambas migraciones y propietario en transacción, configurar callbacks HTTPS, desplegar worker y API, comprobar revisiones exactas y abrir admissions. El acceso nuevo queda cerrado hasta el último paso. Los reportes de worker pueden seguir cambiando; no se incluyen en la comparación de evidencia de negocio al cortar. Una vez admitidos otros workspaces, no se permite rollback a una API sin tenancy.

No se ejecutan migraciones ni QA productivo al arrancar el entorno. El backup contiene datos de negocio: no subirlo al repo ni adjuntarlo al PR. Los resultados de CI/release se registran en el PR y en el estado de implementación.
