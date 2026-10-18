# Modelo de seguridad · propuesta Fase 0

## Evidencia actual

`backend/app/auth.py` compara usuario fijo `dation` y password compartida mediante HTTP Basic. Las rutas de `backend/main.py` y el router de Dispatch exigen esa dependencia; no hay un middleware de identidad SaaS. No hay usuario Supabase validado, membresía, RBAC ni `workspace_id` en tablas públicas. No considerar el workspace privado actual una plataforma multiempresa.

Catálogo real: RLS activo en 12/12 tablas; cero policies públicas y cero grants anon/authenticated. Bucket `dda-inputs` privado, sin policies de Storage. Esto cierra acceso directo de clientes, pero **service role bypassa RLS**. Los servicios hacen REST/RPC y Storage con esa credencial. El inventario completo de superficies y mutaciones está en [API](api-inventory.md); incluye rutas legacy, IA, jobs, historial y exportación en cliente.

Se inspeccionaron en lectura el JWKS público y un subconjunto permitido de configuración Auth: [auth-readiness.json](schema/auth-readiness.json). Existe una clave EC/ES256, JWT de 3.600 segundos, signup/email habilitados y confirmación de email requerida. `site_url` es `http://localhost:3000`, la allowlist de redirects está vacía y no hay SMTP personalizado configurado. Antes del login comercial hay que configurar destinos HTTPS exactos de producción/recuperación y validar entrega de emails con el proveedor autorizado. No se crearon usuarios, enviaron emails ni probaron login/recovery en esta fase. Esta metadata no acredita funcionamiento de esos flujos.

## Autenticación propuesta para Fase 2

- Supabase Auth administra registro email/password, recuperación, logout y refresh; no password custom ni HTTP Basic como login de producto.
- Cliente de Auth oficial o implementación soportada/pinneada; sólo publishable key pública, nunca service key. Verificar configuración de confirmación de email, redirect allowlist, SMTP y expiraciones antes de afirmar signup/recovery operativos.
- Backend verifica firma mediante JWKS soportado, algoritmo permitido explícito (ES256 observado), issuer exacto del proyecto, audience cuando aplique, expiración y subject UUID. Cache de claves con TTL/rotación y un refresh acotado ante `kid` desconocido; no aceptar `alg=none` ni elegir algoritmo desde input sin restricción. Definir librería y lockfiles en Fase 2, sin introducir criptografía propia ahora.
- Frontend envía `Authorization: Bearer`. Persistencia/refresh de sesión no concede permisos: la firma y la membresía activa se validan en servidor. Decidir protección de refresh token/XSS/CSP en el diseño concreto de Auth; no introducir dos implementaciones de sesión paralelas.
- JWT inválido/vencido: 401; membership disabled: acceso denegado; no sesión privada renderizada antes de resolver identidad. Ningún dato de cliente en mensajes de error.

## Contexto y acceso a objetos

Contexto inmutable por request: `user_id`, `workspace_id`, `access_role`, responsabilidad opcional. Se deriva de JWT validado y membership activa. El cliente no puede elegir actor ni role. Si propone workspace, debe validarse igual; fallback de múltiples membresías en [arquitectura](01-target-architecture.md).

Resolver todos los IDs con `(workspace_id,id)`, no sólo comprobar la propiedad del primer objeto de una cadena. Ejemplo: run propio con `upstream_run_id`, Orders/Fleet o evidence ajenos debe fallar. Primero ownership, luego leer resultado, descargar Storage, aprobar, exportar, generar IA o ejecutar. Una lookup genérica sin workspace no queda disponible para rutas productivas, aunque un call-site actual la use correctamente.

Las queries de deduplicación, flota default, casos por firma, historial, summaries, explain/chat cache, comparativas, cancel/retry y settings también se filtran. FKs compuestas y constraints evitan corrupción cruzada desde servicio/RPC. Nunca usar un resultado cacheado antes de autorizar su run.

## Matriz de roles MVP

| Operación | Admin | Operator | Viewer |
|---|---:|---:|---:|
| Leer DDA/datos/cases/runs/export autorizado | Sí | Sí | Sí |
| Upload, validar, crear/ejecutar decisión | Sí | Sí | No |
| Generar resumen/chat/comparativa con persistencia o coste | Sí | Sí | No |
| Aprobar antes de asignaciones de Fase 8 | Sí | Sí, política explícita | No |
| Aprobar con approver asignado | Política de override auditada | Sólo asignado/autorizado | No |
| Equipo/settings/entitlements | Sí | No | No |
| Archive/delete | Sí, con invariantes | Archive permitido por política; no hard delete inicial | No |

Leer interpretación ya persistida es lectura; generarla es mutación/coste. Reconfigurar navegación no equivale a ejecutar motor. Distinguir ambos en permisos y tests. Los botones disabled ayudan a UX pero no autorizan.

## RLS, RPC y credenciales

Estrategia: navegador accede a Auth; el negocio pasa por API. Mantener escrituras directas de tablas/RPC denegadas a clientes. Si se habilitan lecturas REST autenticadas, añadir únicamente SELECT para membership activa del mismo workspace y probar A/B; no conceder grants globales como atajo. Profiles limita lectura/edición del perfil propio, membresías no pueden autoelevar roles.

Las policies de membresía deben evitar recursión; cualquier helper SECURITY DEFINER tendrá esquema/search_path fijos y permisos mínimos. RPC de servicio requiere contexto validado en backend y ownership SQL; el hecho de recibir `workspace_id` no autentica. No dar EXECUTE a roles de cliente sobre las 33 funciones legacy sin revisar argumentos/cuerpo/grants. Inventario DDL completo incluye seguridad y grants de funciones.

Claves: Auth publishable sólo para capacidades públicas previstas; service key y administración sólo backend/entorno seguro. No copiar valores a docs, URLs, bundles, screenshots ni logs. Worker/instrumentación internos separados de rutas de usuarios; no exponer snapshots globales de colas como vista de un workspace.

## Jobs, estado y IA

Job guarda workspace/actor a partir del contexto autorizado, no del payload. Worker revalida coherencia run/case/datasets y devuelve resultados al mismo namespace. Claims y heartbeat son infraestructura global autenticada como servicio. Definir cancelación ante desactivación de miembro sin invalidar runs históricos ya terminados.

Frontend vacía estados/caches de otra identidad al logout, expirar sesión y resolver workspace. Abort/dispose evita pintar resultados atrasados; caches del servidor incluyen workspace y objeto autorizado. No incrustar token en deep links.

IA no modifica resultados determinísticos. Resumen, chat, evidencia y su replay se autorizan por run; proveedor recibe sólo contexto necesario. Failure del LLM mantiene disponible resultado/export. El baseline local usa proveedor HTTP sintético y no valida credenciales ni disponibilidad del proveedor comercial.

## Release blockers de Fase 2

1. JWT ausente, inválido, vencido, issuer/audience incorrectos y `kid` desconocido: fail closed.
2. A intenta IDs de dataset/case/run/job/IA/comparativa de B, incluidos upstream, parent y evidencia: 404 uniforme, sin revelar existencia.
3. CSV igual en A/B no deduplica entre empresas; defaults, colas visibles y Storage no se mezclan.
4. Viewer no muta ni genera IA; disabled no accede. Operator no cambia equipo/settings.
5. REST/RPC/Storage directos no sortean API; URL/path suministrados por cliente no permiten leer objetos arbitrarios.
6. Legacy `/api/datasets`, `/api/runs/{dataset_id}` y resto de rutas pasan por contexto o se retiran con migración; HTTP Basic deja de ser el flujo de producto.
7. Dos cuentas de una empresa continúan D1/D2 y recuperan aprobaciones; otra empresa no ve nada. Console, logs y assets no contienen claves privadas.

No se puede ejecutar aislamiento A/B hoy porque el modelo aún no existe. Es un gate futuro explícito, no un test aprobado ni un fallo nuevo introducido por esta Fase 0.
