# Esquema real, Storage y preflight

## Procedencia

Captura administrativa del proyecto Supabase `gijiinufjjurgfeehufj` realizada con la configuración segura existente, exclusivamente mediante transacciones `BEGIN READ ONLY`, SELECT de catálogo y conteos agregados. Código baseline `22f1187451429c8e98dfcb9874f89b974500cb35`.

- [Catálogo real completo](schema/live-catalog.json): timestamp UTC, PostgreSQL 17.6, columnas/tipos/defaults/nullability, PK/FK/CHECK/UNIQUE, índices, triggers, funciones y grants, RLS, policies, views/secuencias, metadata administrada Auth/Storage y buckets.
- [Integridad del snapshot](schema/SHA256SUMS): SHA-256 `4849ada3acd60156118ec77a71696df712b4c3fce41693ec0018398902bd0a2f`.
- [Preflight de relaciones](schema/lineage-preflight.json): sólo conteos, sin filas de clientes.
- [Equivalencia reconstruida](schema/catalog-comparison.json): 12 tablas y 33 funciones equivalentes al baseline + migraciones posteriores, sin diferencias normalizadas en el catálogo público. Se excluyen datos y esquemas administrados de esa comparación.
- [Índice legible del catálogo](schema/README.md): nombres, columnas, constraints y referencias al JSON exacto.
- [Configuración Auth observada](schema/auth-readiness.json): subconjunto sin secretos y JWKS público; [HTTP/runtime](schema/runtime-readiness.json): estados observados y límites de acceso.

No se consultaron emails, contraseñas, tokens, filas Auth, CSV ni contenido de resultados para esta auditoría de base. El snapshot no reemplaza un backup. La configuración Auth se consultó por separado y sólo se retuvieron campos permitidos, nunca credenciales SMTP ni material privado.

## Tablas públicas y volumen observado

| Tabla | Filas | Tenancy futura |
|---|---:|---|
| `datasets` | 6 | Workspace propio; parent/default/dedup coherentes |
| `decision_cases` | 8 | Desde Orders/Fleet |
| `decision_runs` | 23 | Desde case/datasets; upstream/supersession coherentes |
| `decision_approval_events` | 16 | Desde run/case; append-only |
| `decision_case_reconciliations` | 0 | Desde case |
| `dispatch_run_jobs` | 23 | Desde run |
| `decision_comparative_analyses` | 3 | Desde base run |
| `decision_explanations` | 4 | Desde run |
| `decision_interpretation_sources` | 4 | Desde run y evidencia |
| `decision_messages` | 0 | Desde run |
| `decision_chat_turns` | 0 | Desde run |
| `dispatch_worker_instances` | 4 | Infraestructura global interna |

Los conteos son una observación puntual, no invariantes a exigir a una base que sigue operativa. Ninguna tabla pública tiene `workspace_id`. RLS habilitado en las doce; no hay FORCE RLS ni policies públicas. Sin privilegios de tabla para `anon`/`authenticated`; el acceso de aplicación es de servicio. No hay views públicas o de Storage ni secuencias públicas en esta captura. Los grants y seguridad de cada función se conservan en `catalog.functions` y `catalog.function_security`.

## Invariantes actuales relevantes

- `datasets.storage_path` único. Dedup Orders/Fleet global por `(dataset_type,sha256)` y flota default única global por tipo; ambos índices deben hacerse tenant-aware antes del segundo workspace.
- Cases referencian ambos datasets con DELETE RESTRICT; `status` distingue active/completed/archived. `input_signature` está indexada, no es una clave única de Data Pack.
- Runs tienen FK a case, dataset(s), upstream y supersession; unicidad de aprobación vigente por case/nodo. Aprobación actual sólo acepta el actor `shared_workspace:dation` en su CHECK.
- Triggers validan admisión/lineage, identidad persistente, fingerprints y evidencia; eventos de aprobación son inmutables. No desactivar estas garantías durante backfill.
- Los RPC de cola/admisión/aprobación/IA y lecturas se incluyen por firma y definición exacta, no por inferencia desde OpenAPI. Inventario de uso: [arquitectura](00-architecture-audit.md) y [API](api-inventory.md).

## Storage real

Un bucket: `dda-inputs`, privado. Límite 10.485.760 bytes; MIME admitidos: `text/csv`, `application/csv`, `application/vnd.ms-excel`, `text/plain`. No policies en esquema Storage. Los seis objetos tienen dos componentes de path y prefijo UUID; no se versionan sus nombres ni bytes.

El código genera `<dataset_id>/input.csv` para upload legacy y `<dataset_id>/<Orders|Fleet>_YYYYMMDD_HHMMSS.csv` para Dispatch, con timezone `America/Argentina/Cordoba`. `original_filename` preserva la carga; `canonical_filename` es el nombre generado; `label` es editable. Reutilizar un duplicado no crea objeto nuevo. Archive no borra objetos.

No hay API de hard delete de datasets; sí hay DELETE compensatorio cuando falla el alta de metadatos tras upload. Esa compensación no comprueba explícitamente el status; una incidencia puede dejar huérfanos. En la captura hay **cero** objetos no referenciados y cero datasets sin objeto.

Nuevas cargas con tenancy usarán `<workspace_id>/<dataset_id>/<canonical_filename>`. Lecturas legacy se autorizan por fila y conservan el path. El trigger de identidad impide modificar path/bucket de datasets existentes: una migración física requeriría una adaptación revisada, copia/verificación y rollback; no un PATCH directo. Estrategia completa: [migración](02-data-migration-plan.md).

## Resultado del preflight

Conteos cero en: dataset sin objeto, objeto no referenciado, case sin input, Data Pack de run distinto del case, upstream de otro case, referencias run/approved_run del state_json inválidas, runs sin case, jobs pendientes y outbox pendiente. `public_workspace_columns = 0` confirma ausencia de tenancy; **no es un test de aislamiento aprobado**.

Estas comprobaciones no ejercen motores ni RPC mutantes, no generan IA y no cambian el estado del sistema. Se repetirán inmediatamente antes del cutover; cero pendientes hoy no garantiza una cola vacía en una fecha futura.

Consulta exacta para repetir sobre el esquema actual: [lineage-preflight.sql](schema/lineage-preflight.sql). Sus campos se corresponden con el reporte JSON; no es una migración ni un reset.

## Captura reproducible

Desde la raíz, con `SUPABASE_ACCESS_TOKEN` configurado de forma segura:

```bash
python scripts/audit_platform_schema.py --output /tmp/dation-platform-schema-next
```

El helper fija el proyecto autorizado, hace SELECT en transacciones de sólo lectura con timeout, guarda metadata y agregados y rechaza sobrescribir un snapshot previo. No recibe SQL arbitrario, no aplica migraciones y no usa una service key como token administrativo. No usar `scripts/capture_public_schema.py` para sobrescribir el baseline histórico: ese script se limita intencionalmente al esquema de una saga anterior.

## Auth real: prerequisitos para Fase 2

GET de JWKS público y configuración administrativa Auth respondió 200. Una clave EC/ES256; access token expira en 3.600 segundos. Registro/email habilitados, confirmación requerida, password mínimo configurado en seis caracteres, captcha deshabilitado. URL de sitio actual `http://localhost:3000`, allowlist vacía y SMTP personalizado no configurado. Preparar destinos HTTPS exactos de la futura UI y validación de entrega de email antes de activar signup/recovery comercial. No se ejercieron flujos ni se modificaron settings; la configuración observada es un prerequisito identificado, no una promesa de entrega de emails.

## Infraestructura y límites de observación

La CI del SHA base confirma build y despliegue anteriores; la última entrega D1/D2 se verificó como revisión `dation-core-00506-67v`. Para esta Fase 0 sólo se hizo HTTP de lectura: `/health` 200; `/app` 401 anónimo y 200 con Basic; `/ready` 401 anónimo; `/openapi.json` 200 anónimo.

La consulta administrativa actual a Cloud Run devolvió 401, por lo que **no se recertifican aquí** env vars, IAM, min/max instances ni configuración efectiva actual. La consulta al host del worker fue bloqueada por el proxy de red: no demuestra si el worker es público o privado. El código expone health/ready/metrics sin auth propia en el worker; verificar IAM y red al renovar acceso administrativo antes de futuros despliegues. No se pidió ni cambió configuración para esta fase documental.

No se desplegó una revisión nueva, no se modificaron secrets, tablas, objetos, políticas o Auth. Disponibilidad/calidad del LLM externo y el Golden Dataset externo quedan fuera de la evidencia obtenida; detalles en [baseline](05-baseline-and-ci.md).
