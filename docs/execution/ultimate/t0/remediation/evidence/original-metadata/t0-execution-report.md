# T0 EXECUTION REPORT

## Baseline

- HEAD: `ef997235a30251fbf7ae53690ed738092ee973d8`; branch `main`.
- `origin/main`: `ef997235a30251fbf7ae53690ed738092ee973d8` tras fetch; ahead/behind `0	0`. No se sincronizó/reescribió código.
- Estado inicial: dos documentos untracked preexistentes; tracked/staged limpios. Estado final: esos documentos preservados y entregables T0 sin commit.
- 839 archivos tracked idénticos al snapshot inicial y al manifest de la auditoría previa. Fuentes normativas disponibles y hashes registrados.
- Entorno: Linux x86_64; Python de suites3.13.5; Node24.19.0; Docker28.4; PostgreSQL sandbox17.11/producción17.6; Playwright1.63.0 y Chromium 151.0.7922.173 built on Debian GNU/Linux 13 (trixie).
- Credenciales productivas vacías en procesos de test. API/Auth/Storage/worker E2E locales y sintéticos. No instalación de paquetes/Skills ni reinicio de daemon.

```text
## main...origin/main
?? DATION_FINAL_MASTER_EXECUTION_PLAN.md
?? docs/execution/
?? docs/ultimate-mvp-implementation-master-plan.md
```

## Skills utilizadas

- `supabase:supabase`: Inspección de catálogo/RLS/grants/RPC/Storage y reconciliation, sólo lectura; changelog intentado y bloqueado por proxy. Versión `0.1.2`; recurso/hash en [ledger](evidence/skills-used.json).
- `supabase:supabase-postgres-best-practices`: Verificación de RLS/aislamiento, privilegios y lectura del catálogo; comparación controlada con schema Git, sin optimizar ni cambiar SQL productivo. Versión `1.1.1`; recurso/hash en [ledger](evidence/skills-used.json).
- `cloud-environment:cloud-environment-runtime`: Diagnóstico de sandbox/proxy, runtime readiness, Docker local y ejecución de tests sólo en recursos owned. Versión `sin versión declarada`; recurso/hash en [ledger](evidence/skills-used.json).

No se activaron Skills UX/UI/motion, no hubo redesign ni instalación. Se respetaron F01–F23 y la precedencia aprobada; ejemplos genéricos de RLS no reemplazaron membership/checked RPC actuales.

## Archivos creados

- [Source manifest](../source-manifest.json):839 hashes, fuentes normativas/Skills y preflight Git.
- [ABI/compatibility matrix](abi-compatibility-matrix.md).
- [Test ledger](baseline-test-ledger.json) y [command ledger](command-ledger.json).
- [Deuda individual legible](debt-register.md) y [detalle completo/tracebacks](debt-register.json).
- [SQL/catalog findings](sql-catalog-findings.md).
- Este reporte y `evidence/`: logs originales, snapshots SQL/API/runtime, goldens, scripts de reproducción documentales, verificación de preservación y manifiesto de artifacts. Inventario exacto en artifact-integrity.json.

## Archivos modificados

Ningún archivo productivo, fixture/test existente, Master Plan ni documento previo. Las actualizaciones de archivos creados durante T0 pertenecen exclusivamente a sus entregables/evidencia.

## Archivos preexistentes preservados

- `DATION_FINAL_MASTER_EXECUTION_PLAN.md`: SHA256 `c7543ffa1ef26c79d9142797863fc8ba83613f6cb426cf1621eb0c11b5a27823`.
- `docs/ultimate-mvp-implementation-master-plan.md`: SHA256 `ff824a2fae9566cfb4e1f77ae81e8806d0b76d179b208660b29e9bd00e9ab6d6`.
- 839 tracked files, ambos planes y attachments normativos intactos. Los4 contenedores Docker preexistentes también se conservaron.

## Comandos ejecutados

Los argv/cwd/env de cada suite están en el [command ledger](command-ledger.json). Incluye fetch/status/log/hash reads,6 suites exactas del plan, diagnóstico aislado, reconstrucción SQL owned y GET/SELECT remotos. Las consultas y scripts reproducibles se preservan como evidencia; no se ejecutó script de despliegue/repair.

## Test Results

| Suite | Estado | Tests | Duración reportada | Skips | Resultado |
|---|---|---:|---:|---:|---|
| B-PY | PASS | 383 | 32.483s | 0 | sin fallos |
| B-NODE | PASS | 20 | 1.541s | 0 | sin fallos |
| B-BROWSER | FAIL | 251 | 2030.925s | 0 | failures=48, errors=68 |
| B-SQL | PASS | 46 | 101.015s | 0 | sin fallos |
| B-E2E | FAIL | 83 | 1191.493s | 0 | failures=28, errors=1 |
| B-FOCUS | PASS | 9 | 112.756s | 0 | sin fallos |

La cuenta de failures/errors browser incluye subtests; el registro conserva cada entrada y el ID base, sin restar incorrectamente subtests para inferir PASS. Los logs completos y sus SHA256 están en el ledger. Las6 suites se ejecutaron; no se sustituyeron por los conteos históricos.

Diagnóstico adicional:2 tests; saludo PASS aislado tras ERROR de suite amplia; navegación a Config D2 vuelve a ERROR por timeout6000ms. No elimina fallos del baseline. B-FOCUS9 PASS y el E2E de lineage A–F PASS son evidencia focal, no un PASS global.

## SQL / Catalog Findings

19 tablas públicas con RLS;7 privadas;269 columnas;187 constraints;90 índices;17 policies;101 funciones;46 triggers. Objetos/funciones/triggers coinciden con rebuild actual Git. History remoto:10 filas hasta5/10; Git31 migraciones, con baseline10/10+23 upgrades reproducidos sólo en DB owned. No repair/replay remoto.

Diferencias registradas:18 grants adicionales de service_role en producción;6 default ACL administrados frente a0 en Postgres genérico; ACL pública contiene USAGE explícito adicional de postgres. No implican nuevos grants a anon/authenticated en la diferencia de tablas. Storage privado10MiB todavía sin JSON/JSONL. Ver [hallazgos y adaptación mínima](sql-catalog-findings.md).

## ABI / Compatibility Findings

91 paths/98 operaciones; OpenAPI local=auditoría previa=OpenAPI productivo. Engines actuales: Assignment1.0.0/assignment_v1, Scheduling1.0.0/scheduling_v1, Dispatch2.2.0/dispatch_v2. Estado SQL error se mantiene, distinto de FAILED del contrato futuro. Handoffs scheduling_input_v1/final_assignment_input_v1 intactos.

La [matriz](abi-compatibility-matrix.md) registra requests, idempotencia/lease, context/freshness, actores/approvals, CSV/unknown schema, legacy KPIs/IA, calendario/costos y adapters futuros aprobados. Ningún DTO/profile/registry nuevo se implementó.

## Pre-existing Debt

Los3 IDs WorkflowContext documentados se identifican individualmente al reproducirse. Otras discrepancias demostrables pertenecen a fixtures/expectativas anteriores al contrato actual: roles de escritura, alias data_steward, bridge de migración, atributos aplicados y conteos/semántica de supersession.

No se asume que todos los timeouts o fallos visuales tengan esa causa. Los restantes quedan como hallazgos nuevos del baseline con atribución pendiente. Cada entrada del [registro](debt-register.json) indica ID, componente, assertion, esperado/observado, evidencia, clasificación y bloqueo T1.

## New Issues

- Las suites amplias revelan más fallos que la deuda previamente documentada. Ninguno se oculta por un PASS focal o por mantener el mismo HEAD.
- Existen fallos de render/journeys/selectores/estados que aún no tienen causa inequívoca; el saludo ilustra una diferencia entre suite e aislamiento.
- Algunas fixtures de aprobación esperan controles disabled y observan controles habilitados; las verificaciones backend/Owner no se dan por satisfechas a partir de esa UI. Conciliar el modelo actual de roles y los escenarios pendientes antes de certificar permisos de extremo a extremo.
- Metadata de privilegios/defaults Supabase no es idéntica al sandbox genérico. Antes de expansión futura debe contemplarse ese contexto efectivo.
- Cloud Run GET administrativo401; no se recertifica SHA de imagen/worker/IAM. Health y contrato público sí observados. Changelog Supabase bloqueado por proxy403; no se eludió la política.

No hubo cambios productivos T0; no se afirma que una causa desconocida sea deuda histórica exenta.

## Deviations from Master Plan

Ninguna desviación de implementación: T0 solamente; T1 no iniciado. Las observaciones nuevas invalidan una lectura de baseline globalmente verde, que el plan tampoco había certificado. Se registran los fallos amplios y la diferencia administrativa de grants sin modificar el Master Plan.

Adaptaciones operativas: recuperación autorizada del sandbox de red/socket; Node24 usó reporter spec y se corrigió el parser de evidencia, no la suite; segundo rebuild local amplió verificación de triggers/ACL. Sin cambio de tests, asserts, fixtures o reglas.

## Risks discovered

- Continuar sobre suites amplias en rojo puede ocultar regresiones futuras o legitimar expectations incompatibles.
- No confundir fallo de setup por enum422 con prueba de autorización/aprobación efectivamente completada.
- No restaurar approvals/eventos viejos para cumplir tests previos a supersession actual.
- No usar migration history incompleto ni defaults del sandbox para inferir el estado efectivo Supabase.
- No inferir imagen/revisión productiva a partir de health/OpenAPI. Fuentes aprobadas siguen untracked por instrucción; hashes pinneados en manifest.

## Rollback status

No hay código/datos productivos que revertir. No reset, commit, push, migration productiva, cambio de RLS/grants/secrets/Cloud Run o deploy. Bases de rebuild eliminadas; contenedor SQL T0 eliminado; harness E2E terminó y sus recursos fueron limpiados;4 contenedores preexistentes preservados. Entregables documentales quedan para revisión.

## Gate Evaluation

| Gate | Estado T0 | Evidencia / alcance |
|---|---|---|
| G-A | PASS | Sólo documentación/evidencia/tests T0;839 hashes y fuentes preservados; ningún T1. |
| G-B | FAIL | Deuda amplia supera los3 IDs históricos; fallos nuevos del baseline y casos sin causa aislada. No se admite exención global. |
| G-C | PASS con findings | ABI real registrada. Divergencias de fixtures frente a roles/gates/history actuales quedan explícitas, sin cambiar semántica. |
| G-D | PASS con findings | Catálogo de aplicación reconstruido; history incompleto/defaults/grants administrativos reconocidos; cero escrituras remotas. |
| G-E | PASS limitado T0 | 383 unit PASS y golden legacy idéntico; ningún engine modificado. No certifica motores Ultimate inexistentes. |
| G-R | BLOCKED | Golden/cross-surface E2E no termina verde. CSV/probes/OpenAPI preservados no sustituyen ese gate. |
| G-L | BLOCKED | Lineage real A–F y focales pasan; suite amplia contiene expectativas incompatibles de approval/history/Home sin conciliación cerrada. |
| G-S | BLOCKED en cobertura amplia | RLS/grants y negativos SQL/tenant pasan en su alcance; casos de permisos/approval detenidos por setup422 o expectations UI no certifican el escenario amplio. No se afirma bypass ni se acepta un PASS global. |
| G-P | PASS limitado T0 | Suites actuales verifican payloads/listados acotados. SLOs/escala Ultimate quedan fuera de T0 y NOT RUN. |
| G-ENV | PASS | Seis suites ejecutadas sin skips y con runners/DB owned. Bloqueos iniciales del sandbox recuperados; Cloud Run admin401 y changelog403 son límites de observación registrados. |

G-UI y G-REL no se activaron como cambios de producto/release: no hubo frontend modificado ni despliegue. Las regresiones observadas del baseline no quedan aprobadas por esa ausencia de cambios.

## FINAL T0 DECISION

**STOP — T0 no cumple las condiciones para autorizar T1.**

Se ejecutó y preservó el baseline completo, pero B-BROWSER y B-E2E fallan con deuda/hallazgos que exceden la excepción histórica documentada. G-B no pasa; cobertura amplia de resultados/lineage queda bloqueada hasta conciliar individualmente expectativas actuales y reproducir causas pendientes. No corresponde declarar GO ni corregir silenciosamente backend/UX/approvals para hacer pasar tests.

T1 no se ejecutó ni queda autorizada por este reporte. La siguiente acción deberá resolver/revalidar los bloqueos del baseline dentro del alcance que se autorice, sin avanzar automáticamente.
