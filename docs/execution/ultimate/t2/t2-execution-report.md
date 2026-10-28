# T2 — Schema + Compatible Readers + Result Artifact Metadata

## Baseline y checkpoint post-T1

Se ejecutó exclusivamente T2 bajo la [autorización del usuario](evidence/T2-user-request.txt), el [Final Master](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md) §7/§20/T2/§22 y el [reporte T1 aprobado](../t1/t1-execution-report.md). T0 se consultó para el catálogo/defaults de Supabase y la ruta de reconstrucción completa; no hubo una nueva auditoría de la plataforma.

- Branch: `main`; HEAD inicial y final: `ef997235a30251fbf7ae53690ed738092ee973d8`.
- Baseline inmediato: Python 444, Node 128 y U1 61 PASS; U1 incluido en Python. Baseline transversal T0-R2: Browser 251, SQL 46, E2E 86 y Focus 9, sin failures/errors/skips.
- Antes de modificar T2 se guardaron **343 archivos pendientes** —13,503,949 bytes— con hashes y copia local en `/workspace/work/dation-t2/post-t1/`, más el patch tracked post-T1. Los 66 entries del manifest T1 se verificaron al inicio. No había staging ni commit de checkpoint autorizado.
- Los 343 archivos post-T1 conservan sus bytes al cierre. El [manifest inicial](evidence/initial-state.json), [patch previo](evidence/post-t1-tracked.patch), [patch exclusivo T2](evidence/t2-changes.patch) y [scope diff](evidence/scope-diff.json) distinguen ambos estados.
- Los cambios anteriores de CSS, Browser/E2E y SQL que siguen en `git status` pertenecen al baseline. T2 no los alteró.

Fecha de ejecución: 26/10/2026, America/Buenos_Aires. Batch final requerido: 11:55–11:58; los logs conservan UTC original. No se realizó commit, push, merge, despliegue ni escritura remota. **T3 no se ejecutó.**

## Skills utilizadas

Se aplicó la Execution Skills Policy con estas tres Skills:

| Skill | Aplicación acotada | Verificación |
| --- | --- | --- |
| [supabase:supabase](evidence/supabase-skill.txt) | Defaults gestionados, RLS, ACLs explícitas, migraciones aditivas y CLI oficial | S2, catálogo/grants y negativos HTTP/SQL locales |
| [supabase:supabase-postgres-best-practices](evidence/postgres-skill.txt) | FKs compuestas, índices, membership y transacciones ordenadas | Matriz FK, diff de catálogo y tests de integridad |
| [cloud-environment:cloud-environment-runtime](evidence/runtime-skill.txt) | Readiness del entorno y sandbox Docker/PostgreSQL owned | Socket local explícito, label/major17 verificados, aislamiento de credenciales y cleanup |

Se leyeron además las referencias de índices FK/RLS y Docker/networking. El changelog público de Supabase solicitado por la Skill devolvió HTTP 403; se usó el MCP oficial `search_docs`, el snapshot administrativo T0 y la ayuda de la CLI 2.122.0. No se eludió la política de red. Los snippets de documentación no se ejecutaron como grants ni instalaciones de extensiones.

Los advisors remotos no se invocaron: T2 no autoriza una nueva auditoría ni escrituras del proyecto productivo. Las verificaciones de RLS, grants, PUBLIC EXECUTE y search_path se hicieron sobre los objetos nuevos en el sandbox. Skills UX/UI: N/A, sin frontend afectado. [Ledger con propósito y hashes](skills-ledger.json).

## Archivos y alcance

Cinco archivos nuevos de producto/tests:

| Archivo desde raíz | Propósito |
| --- | --- |
| `supabase/migrations/20261026143813_ultimate_foundation.sql` | Models/Versions, Case/Pack/Dataset/Run context, Definitions, constraints/ACLs y readers SQL compatibles |
| `supabase/migrations/20261026144259_ultimate_result_artifacts.sql` | Metadata de artifacts, binding diferido e IA provenance nullable |
| `backend/tests/integration/ultimate_sql_support.py` | Catálogo completo PostgreSQL17, defaults gestionados y rechazo de contenedor ajeno |
| `backend/tests/integration/test_ultimate_schema.py` | 26 escenarios S2 reales |
| `backend/tests/test_ultimate_readers.py` | 12 tests de proyección/readers y denegación de writes incompatibles |

Cinco archivos existentes modificados exclusivamente por T2:

- `backend/app/domain/decision_cases.py`: discriminator explícito, referencias NULL y proyección vacía segura.
- `backend/app/services/decision_case_service.py`: list/detail/history duales y rechazo de escrituras legacy sobre contexto Ultimate.
- `backend/app/platform/repository.py`: lectura de cinco relaciones nuevas tenant-scoped; ninguna escritura nueva ni admisión Ultimate habilitada.
- `backend/app/platform/home.py`: Case vacío visible, sin convertir NULL a string ni ofrecer configuración/Run inexistente.
- `backend/app/platform/decision_center.py`: misma proyección por cohorte y preservación del Case sin pair.

El código Python de Data Hub no necesitó cambios; sus funciones SQL de usage/reference se ampliaron en la migración foundation. No se cambió CI: los runners actuales descubren los tests nuevos. Documentación y evidencia nuevas quedan exclusivamente en esta carpeta T2. [Freeze de los diez archivos](evidence/source-freeze.json).

## Schema changes

### Estructuras nuevas

Se crearon exactamente las siete relaciones previstas:

1. `public.logistics_models`: identidad reusable, tenant, status/revision, creator y timestamps.
2. `public.logistics_model_versions`: snapshots publicados inmutables, config/contract descriptors y hashes, registry/graph y publisher.
3. `public.case_data_packs`: Pack estable único por Case, revision y current pointer del mismo Pack/Case.
4. `public.case_data_pack_versions`: versiones inmutables con hashes de manifest/contratos y provenance.
5. `public.case_data_pack_entries`: slots de T1, Dataset e interpretación exacta, hashes/raw/canonical/normalizer y referencia privada normalizada.
6. `dation_private.decision_definition_versions`: catálogo privado/versionado, append-only y release-only; sin editor ni sistema de plugins.
7. `public.decision_result_artifacts`: metadata de partes del resultado, sin evidencia pesada JSONB ni bytes publicados.

Las relaciones de dominio llevan workspace NOT NULL, claves compuestas y ON DELETE RESTRICT. Los publishers/creators referencian membership del mismo tenant. RLS está habilitado y forzado en las siete tablas. Las cinco tablas Model/Pack permiten sólo SELECT por membership a authenticated y lectura al backend; no se concedió INSERT/UPDATE/DELETE a clientes ni a service_role. Definitions es release-only. Artifacts expone SELECT únicamente al servidor, sin locators accesibles a authenticated.

### Extensiones compatibles

- Cases: `workflow_version` 1/2 independiente de `workflow_policy_version` 0/1; Model Version, planning dates, operating mode, Case Policy/schema/hash/freeze y graph version.
- La nullability global de Orders/Fleet/input_signature se sustituye por CHECK de cohorte: **v1 sigue requiriendo los tres**; v2 exige contexto nuevo y pair/signature NULL. No fake IDs, placeholders, backfill ni cambio de cohorte histórica.
- Case y Pack/primera versión deben confirmar juntos. El current pointer usa FK diferida al mismo workspace/Case/Pack; no puede quedar NULL al commit. Una versión vacía es válida.
- Datasets: tipos `transport_demand` y `transport_resources`, contract ID/hash, normalizer y canonical hash. El índice parcial legacy se conserva idéntico; el nuevo dedup incluye raw SHA y contract hash. La interpretación es inmutable, no se convierte Fleet a Resource.
- Runs: pinning nullable de Model/Pack/Graph/CasePolicy/NodePolicy/Contract/Transit/runtime/input context y schema version. Las Runs Ultimate requieren coherencia Case/Model/Pack/policy/graph; dataset_id sigue siendo el Demand raw del Pack, nunca un fake Fleet. Las columnas nuevas de historia legacy quedan NULL.
- Approval/invalidation: reason y Pack cause nullable, FKs del mismo Case y condición de supersession por cohorte. No se generaron eventos reales, actors, approvals o invalidaciones retrospectivas ni se implementó publish/read-set invalidation.
- Nuevos snapshots/entries/Definitions son inmutables. Un stamp interno `created_xid` de servidor impide agregar entries a una versión ya confirmada; es metadata técnica de integridad, no una entidad de dominio ni un workflow de publicación.

Los guards anteriores de ownership, aprobación, actor, lineage, result terminal e idempotencia permanecen. T2 prepara persistencia; admission, locks/CAS/publicación operacionales de T3/T4/T8 no se implementaron.

## Reader changes

Case list y Home pasan sus joins de datasets a LEFT JOIN; las proyecciones devuelven NULL real cuando falta el pair. Los guards/ACL/OID de las funciones existentes se conservan. Home mantiene su cálculo de atención por Owner aprobado en T0-R2.

Los readers Python resuelven por `workflow_version`; una versión desconocida/bool/string no cae a legacy. Detail/list/history no piden datasets con IDs `"None"`. La proyección vacía declara necesidad de datos, sin Runs/approvals ficticias. Home y Center no habilitan un resume de ejecución/configuración Ultimate todavía no implementado.

Data Hub reconoce uso de un Dataset por Pack entries para su Case count y para impedir eliminación de Storage de un input consumido. La lista de packs legacy continúa representando pairs Orders/Fleet; no inventa un pair para el Pack progresivo vacío ni introduce la UI de T4.

No se agregó endpoint. [OpenAPI idéntico a T0/T1](evidence/api-preservation.json): **91 paths, 98 operaciones**. Sin UI, Model library, Case Setup nuevo, compiler/normalizer, graph resolver, engines, assembler, chart ni Copilot v2.

## Legacy compatibility changes

Cambios aditivos y condicionados; no reinterpretación histórica. El upgrade del catálogo post-T1 se realiza aplicando solamente los dos archivos nuevos. Se compararon antes/después todas las columnas previas de cinco tablas con datos legacy sintéticos, incluidas Run/result JSON y approval event: **cinco filas idénticas**. También se insertó una interpretación legacy con provenance totalmente NULL tras la expansión.

Los 444 IDs de Python post-T1 y 46 IDs SQL del baseline se retienen completos; Node conserva exactamente sus 20 archivos/argv. Los 343 archivos pendientes anteriores y todos los contratos/vectores/metadata T1 permanecen idénticos. No se editaron migraciones previas, baseline SQL, schemas/serializers/date helpers/exports ni motores v1.

Las escrituras legacy no pueden cambiar un Case a v2, sustituir su Model/graph/freeze/policy, alterar su cache Ultimate ni admitir nuevos perfiles. Archivar/restaurar metadata permitida conserva el schema y contexto. Las rutas públicas de creación siguen requiriendo el contrato legacy; no hay una API Ultimate nueva activa.

## Result artifact preparation

La tabla describe workspace/Run, kind/part, schema/version cerrado, SHA256/tamaño/media, bucket/path privado content-addressed, assembler/core fingerprint, result fingerprint, estado, lookup keys acotadas y producer lease/generation/metadata.

- PREPARED exige result fingerprint NULL; tener metadata no significa READY.
- READY exige fingerprint, Run Ultimate completada/package version1, assembler/core coincidentes y descriptor exacto presente en el manifest del package. La FK `(workspace,run,result_fingerprint)` es diferida para una transacción futura de publicación.
- Identidad PREPARED no se reescribe; READY no se actualiza ni borra. Paths, tamaños, schemas, kinds y media inválidos se rechazan.
- La transición PREPARED→READY se probó sólo con fixtures sintéticos SQL y binding válido. No se produjo/publicó ningún resultado Ultimate ni se subió un objeto.

Este gate certifica metadata y binding de package/manifest. **No** prueba existencia/hash de bytes remotos, firma, verificación matemática ni lease fence operativo: T8 será la autoridad para esas verificaciones y el publisher real. El token/generation guardado no concede permisos al browser.

No se modificó bucket, MIME permitido ni política Storage productiva. Los paths de metadata fijan el namespace para el futuro publisher; T8 deberá validar el bucket privado y la disponibilidad JSON/JSONL antes de publicar. No se utilizó MIME falso.

## IA provenance preparation

`decision_interpretation_sources` agrega campos nullable: provenance version, result fingerprint, decision context schema/hash, mode, selected entity y evidence refs. La variante v2 exige Run publicada del mismo tenant/fingerprint y refs de artifacts READY de esa misma publicación. Selección usa `{type,id}` de T1; EXPLAIN/EXPLORE/COMPARE/REVIEW están cerrados por CHECK. La provenance persistida es inmutable.

Legacy continúa con NULL, probado por inserción real. No se invocó LLM, no se cambió la conversación/idempotencia actual y no se creó otra entidad de chat. Review/permission overlay de T1 conservan su separación.

## Migraciones, catálogo y grants

Ambos filenames se generaron mediante `supabase@2.122.0 migration new`, con timestamps reales, en orden. Cada migración usa transacción y lock/statement timeouts; sólo se aplicaron a bases descartables owned. No se conectó un proyecto CLI ni se hizo repair/listado remoto/replay de history.

El helper nuevo carga el baseline capturado sólo para una **base nueva** y todos los upgrades posteriores. Reproduce los seis default ACL gestionados reconocidos en T0 y las 18 diferencias de grants service_role documentadas. Las migraciones revocan explícitamente los defaults amplios únicamente sobre sus objetos nuevos; no cambian los defaults ni privilegios de tablas anteriores.

| Catálogo de aplicación del sandbox | Post-T1 | Post-T2 |
| --- | ---: | ---: |
| Relaciones | 26 | 33 |
| Columnas | 269 | 384 |
| Constraints | 187 | 299 |
| Índices | 90 | 135 |
| Policies | 17 | 22 |
| Funciones | 101 | 111 |
| Triggers | 46 | 63 |
| Default ACL | 6 | 6 |

Sin relaciones, columnas, índices, policies o funciones eliminados. Cambian tres nullabilities de Case, dos CHECK existentes por expansión condicionada y cuatro funciones de lectura/reference. Los ACL de tablas existentes y de las cuatro funciones permanecen idénticos.

Fresh y upgrade coinciden **exactamente** en el catálogo comparado: columnas/defaults, constraints, índices, policies, RLS/ACL, funciones, triggers y default ACL. [Catalog diff](evidence/catalog-diff.json), [RLS/grants diff](evidence/rls-grants-diff.json), [matriz FK](evidence/sql/fk-constraint-matrix.json), [preservación del upgrade](evidence/sql/upgrade-preservation.json).

El sandbox es PostgreSQL **17.11**, mientras T0 observó producción 17.6. Se conserva esa diferencia: se prueba major17 con defaults reproducidos, no una clonación administrativa integral de Supabase. No hubo DDL remoto.

## Tests

Candidate de diez archivos congelado antes del batch final; sus hashes siguen iguales. Python 3.13.5, Node 24.19.0, PostgreSQL17.11 y dependencias existentes. Credenciales productivas anuladas en procesos hijos; Docker usa el socket local explícito. No se instalaron dependencias de aplicación.

| Suite | Estado | Tests | Failures | Errors | Skips | Wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B-PY | PASS | 456 | 0 | 0 | 0 | 21.591 s |
| B-NODE | PASS | 128 | 0 | 0 | 0 | 1.732 s |
| B-SQL | PASS | 72 | 0 | 0 | 0 | 81.688 s |
| S2 | PASS | 26 | 0 | 0 | 0 | 24.373 s |
| FOCAL-API legacy Home/Center/Hub | PASS | 3 | 0 | 0 | 0 | 62.373 s |
| FOCAL-EMPTY-API | PASS | 4 | 0 | 0 | 0 | 22.299 s |
| Browser completo | NOT RUN | 0 | N/A | N/A | N/A | N/A |
| E2E completo | NOT RUN | 0 | N/A | N/A | N/A | N/A |
| Focus completo | NOT RUN | 0 | N/A | N/A | N/A | N/A |

456 Python = 444 post-T1 + 12 readers. 72 SQL = 46 históricos + 26 S2; S2 también se ejecutó explícitamente por requerimiento, no son 26 casos únicos adicionales al total SQL. U1 conserva sus 61 tests incluidos en B-PY. El SQLSandbox histórico sigue con su alcance anterior; **S2 usa exclusivamente el helper completo nuevo**.

S2 demuestra fresh-install/upgrade, igualdad de catálogo, rows legacy/NULL compatibles, Case vacío+Pack atómicos, Model binding/freeze/inmutabilidad, current Pack/entries íntegros, dedup versionado, Run pinning, negativos cross-tenant, RLS/grants, READY válido/inválido, provenance y readers sin writes. Logs y matriz identifican los escenarios exactos.

Las siete pruebas HTTP focales usan PostgreSQL/PostgREST/API reales de fixtures owned. Verifican lectura legacy, archivo/preview y permisos; Case vacío legible en list/detail/history/Home/Center; viewer/otro tenant; ausencia de resultados/configuración ficticios y rechazo de escritura legacy/creación Ultimate no implementada. El Case vacío se siembra por SQL de prueba: no implementa T3.

Se conservaron los primeros logs verdes de 24 S2 y 12 readers, además de los finales de 26 S2. No hubo failures/errors/skips en estos ensayos. No se borraron tests ni se redujeron asserts o permisos para lograr PASS.

No se repitieron Browser/E2E/Focus completos: no hay frontend nuevo y las fronteras de readers se cubrieron primero por tests focales y después por SQL/HTTP reales. Sus PASS T0-R2 251/86/9 son evidencia heredada, **no PASS nuevos de T2**.

[Test ledger](test-ledger.json), [command ledger](command-ledger.json), [runtime](evidence/runtime.json), [preservación de IDs/archivos](evidence/preservation.json). Los logs y scripts reproducibles se guardan en `evidence/`.

## Rollback readiness

PASS para la estrategia **expand + readers compatibles + Ultimate cerrado**: se verificó que la aplicación mantiene el contrato v1 y lee estructuras v2 vacías sobre el schema expandido. No se necesita revertir datos o retirar columnas para continuar atendiendo legacy.

Un rollback debe mantener esta compatibilidad de readers y la expansión. El binario anterior que exige pair en todos los Cases **no es un destino válido si ya existen Cases v2**. No restaurar NOT NULL global, borrar Versions/Entries/Artifacts ni revertir a una imagen que pierda lectura de v2. Para un incidente de readers, conservar schema/metadata y volver al candidato compatible ensayado; cualquier corrección adicional requiere su fase autorizada.

El checkpoint post-T1 permite comparar/revisar el código, no autoriza un downgrade destructivo de DB. Restore integral y rollback de release productivo con artifacts/bytes permanecen en T11/T12; no se les asigna PASS en T2. Ninguna recuperación o release se ejecutó en remoto.

El contenedor `dation-t2-20261026-ultimate` se verificó por label, sin red ni puertos publicados. Todos los databases de suites se eliminaron; quedaba sólo `postgres`. Después del QA se detuvo/retiró únicamente ese contenedor. Los sandboxes HTTP también efectuaron su cleanup. [Evidencia](evidence/sandbox-cleanup.json).

## Deviations y riesgos residuales

- No se alteró F01–F23 ni se adelantó T3–T10. El módulo adicional de tests de readers y scripts focales de evidencia responden a los callers afectados, no a una auditoría general.
- Data Hub se adaptó en SQL; no fue necesario modificar su módulo Python ni CI. Se conservaron los nombres finales de T1 para slots, runtime y selección.
- La CLI es tooling temporal, no dependencia nueva del producto. El changelog inaccesible se documenta; no bloqueó el trabajo SQL sobre el catálogo ya capturado y la documentación oficial disponible.
- RLS/grants probados reproducen los defaults observados, sin afirmar igualdad total de administración Supabase ni de patch17.6/17.11.
- Hash/descriptor/metadata no prueban bytes ni certificado matemático. Models/Pack publicación, admission, CAS/lease/fence operativo, invalidación por read sets y retrieval siguen en sus fases. Ambos runtimes Ultimate de T1 continúan no implementados/no disponibles.
- No hay UI Ultimate habilitada ni nuevas capabilities públicas. El futuro release debe preparar readers/worker compatibles antes de abrir cohortes.

No quedó una incompatibilidad real ni una STOP CONDITION sin resolver en el alcance T2.

## STOP / GO gates

| Gate | Resultado T2 | Evidencia y límites |
| --- | --- | --- |
| G-A | PASS | Fase exclusiva, checkpoint preservado, diez archivos scoped; sin auditoría nueva, commit/push/deploy/T3 |
| G-C | PASS | Expansión versionada, no reinterpretación legacy; DTOs T1 preservados; OpenAPI idéntico |
| G-D | PASS | Fresh/upgrade iguales, FKs/immutability/default ACL/grants y legacy rows probados; sin repair/backfill/destructive rewrite |
| G-B | PASS | 444 IDs Python y 46 SQL retenidos; Node intacto; cero failures/errors/skips |
| G-L | PASS, preparación | Context pins y metadata causales; legacy history intacta; publicación/races/read sets Ultimate aún T8 |
| G-S | PASS, T2 | Tenancy por FK además de RLS, permiso mínimo y APIs focales; no certifica retrieval/Storage futuros |
| G-R | PASS, metadata | Binding READY diferido y exacto con Run/manifest; no certifica bytes ni consumers de T8/T10 |
| G-ENV | PASS | PostgreSQL17 owned completo y runners reales, >0 tests, sin skips; cleanup verificado |
| G-E | N/A | Ningún engine o matemática nueva |
| G-P | N/A operacional | Sin publicación nueva; budgets T1 conservados; performance de resultado real corresponde a T11 |
| G-UI | N/A | Ningún cambio de UI, CSS, assets o tokens en T2 |
| G-REL | N/A | Sin release ni escritura productiva autorizada |

Las STOP CONDITIONS se probaron mediante negativos: no se aceptan cruces tenant/Case, opens de grants, READY sin binding o pérdida de lectura de Cases vacíos. Ningún paso requirió producción, baseline replay, rewrite de historia ni implementación de T3.

## FINAL T2 DECISION

**GO — T2 completado. T3 puede ser solicitado.**

Se finaliza con el diff revisable y la evidencia. T3 no fue ejecutado; no hubo commit, push ni despliegue.
