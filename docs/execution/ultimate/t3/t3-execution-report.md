# T3 — Logistics Models + Decision Case Foundation

## Baseline utilizado

Se ejecutó exclusivamente la [autorización T3](evidence/T3-user-request.txt), siguiendo [Final Master §T3 y §22](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md) y el [reporte T2 aprobado](../t2/t2-execution-report.md). No hubo nueva auditoría transversal. Fecha: 26/10/2026, America/Buenos_Aires; los logs conservan UTC.

- Branch: `main`; HEAD inicial y final: `ef997235a30251fbf7ae53690ed738092ee973d8`.
- Baseline inmediato: Python 456, Node 128, SQL 72, incluidos S2 26, todos PASS. Las suites Browser/E2E completas se heredan del baseline aprobado y no se repitieron.
- Antes de editar se copiaron 392 archivos pendientes, 16.464.590 bytes, a `/workspace/work/dation-t3/post-t2/`, con hashes y patch tracked. No había staging.
- Al cierre, **391 archivos conservan sus bytes**. El único archivo pendiente de T2 extendido por T3 es `backend/app/platform/home.py`: agrega el destino del contexto recuperable. Su preimagen se conserva también [dentro de la evidencia](evidence/post-t2/backend/app/platform/home.py).
- Los 57 entries del manifest histórico T2 se verificaron contra el archivo actual o esa preimagen. No se reescribieron el manifest, reportes, migraciones ni contratos anteriores. [Preservation](preservation.json), [scope diff](scope-diff.json), [patch exclusivo T3](evidence/t3-changes.patch).

Hay 24 archivos de implementación/tests/migración exclusivos de T3: 16 nuevos y 8 modificados. Los cambios de CSS global y Browser/E2E anteriores que muestra Git son baseline, no modificaciones T3. El árbol queda pendiente de revisión, sin staging, commit, push ni despliegue. **T4 no fue ejecutado.**

## Skills utilizadas

El [Skills ledger](skills-ledger.json) distingue guía leída, aplicada y verificada, con path/snapshot/SHA256. Se aplicaron:

| Skill | Aplicación acotada | Verificación |
| --- | --- | --- |
| `design-system` | Composición de controles, cards, estados y tokens existentes; sin generador | Paridad de píxeles/estilos de componentes en cinco anchos |
| `emil-design-eng` | Feedback inmediato, diálogo nativo, foco/Escape/retorno y reduced motion | W3 01/02/06/08; tabla Before/After abajo |
| `ui-ux-pro-max` | Búsqueda focal de validación: resumen enfocable, links a campos, errores inline y blur | W3 02 y [resultado de la búsqueda](evidence/ui-skill-form-guidance.txt) |
| `break-ui` | Nombres de 120 caracteres, descripción de 1000, Unicode, estados vacío/uno/múltiples, 320px y zoom200% | W3 04/07; fixtures del harness, sin toggle productivo |
| `supabase:supabase` | Migración aditiva, RPC checked, ACL explícita, actor/tenant y flag cerrado | S3 y [schema boundary](evidence/schema-boundary.json) |
| `supabase:supabase-postgres-best-practices` | Locks ordenados, CAS, FKs compuestas y snapshots inmutables | Publicación concurrente y carrera admission/context en S3 |
| `cloud-environment:cloud-environment-runtime` | Docker local propio, runners sin credenciales productivas y cleanup | Label/version checks y runtime/cleanup evidence |

Las guías de paletas, fuentes, starters, React/Framer, rediseño o auditoría general de motion quedaron fuera por precedencia del pedido y §3.1.1. La regla de `break-ui` “Report before fixing… then stop” no abre otra aprobación: el usuario ya autorizó implementación T3 completa. No se invocó automáticamente `review-animations`, ni se agregaron dependencias de aplicación. Las guías cloud ya leídas en esta conversación se conservaron como snapshots; runtime se consultó al inicio de T3. No se inspeccionó producción.

## Files Created

Paths relativos al repositorio; hashes y preimágenes en [scope-diff.json](scope-diff.json).

| Archivo | Función |
| --- | --- |
| `backend/app/models/ultimate_foundation.py` | DTOs de configuración, Model, Case, Owner CAS y Planning Context |
| `backend/app/services/logistics_model_service.py` | Snapshots/hashes, intents y llamadas a la RPC checked |
| `backend/app/platform/ultimate_routes.py` | APIs de capabilities, Models/Versions y Case context |
| `backend/app/static/css/ultimate-foundation.css` | Layout scoped de las superficies nuevas |
| `backend/app/static/js/dispatch/models/entry.mjs` | Entrada bajo el Hero DDA, gobernada por capabilities |
| `backend/app/static/js/dispatch/models/forms.mjs` | Composición DOM de controles nativos, dirty/draft/errores/CAS |
| `backend/app/static/js/dispatch/models/index.mjs` | Library, editor y publicación de Model |
| `backend/app/static/js/dispatch/models/policy.mjs` | Goal, hard guardrails y preferencias separadas |
| `backend/app/static/js/dispatch/models/setup-values.mjs` | Conversión decimal exacta y fechas concretas de presets |
| `backend/app/static/js/dispatch/cases/ultimate-case-setup.mjs` | Creación/recuperación/edición permitida del Case |
| `backend/tests/test_ultimate_case_models.py` | U3: 17 pruebas de dominio/servicio |
| `backend/tests/test_ultimate_case_navigation.mjs` | Cuatro pruebas Node de URL, horizonte, porcentajes y dirty signatures |
| `backend/tests/integration/test_ultimate_case_models.py` | S3: 25 pruebas SQL reales |
| `backend/tests/browser/test_ultimate_case_setup.py` | W3: nueve escenarios sobre backend y SQL reales |
| `backend/tests/e2e/ultimate_setup_fixture.py` | Fixture local Auth/API/PostgREST/SQL, sin worker Ultimate |
| `supabase/migrations/20261026161050_ultimate_case_models.sql` | RPC, borrador/versioning, CAS, freeze y flag default false |

Este reporte, ledgers, manifiesto y evidencias se crean bajo `docs/execution/ultimate/t3/`; no son cambios funcionales adicionales.

## Files Modified

| Archivo | Cambio exclusivo T3 |
| --- | --- |
| `backend/app/platform/routes.py` | Incluye el router dedicado |
| `backend/app/platform/identity.py` | Mensaje de validación para la RPC nueva |
| `backend/app/platform/decision_routes.py` | Rechaza readiness/reemplazo legacy sobre Case Ultimate antes de dereferenciar el pair nulo |
| `backend/app/platform/home.py` | Resume el Case T3 hacia setup/context; T2 fixture sin contexto sigue sin destino ejecutable |
| `backend/app/static/js/dispatch/navigation/resource.mjs` | Dos vistas, Model ID y Case ID en deep links |
| `backend/app/static/js/dispatch/workspace.mjs` | Mount/lifecycle lazy, dirty guard y recuperación del contexto sin pair |
| `backend/app/static/js/platform/dda-navigation.mjs` | Breadcrumb de Model/Case context, sin graph resolver |
| `backend/app/templates/app.html` | Dos paneles vacíos y reconocimiento de las vistas logísticas |

## Logistics Model implementation

Un Model es una configuración reusable de operación, independiente de semana, CSV o Run. Se persisten nombre/descripción, estado, revisión CAS y borrador validado. Configuración v1 cerrada:

- Roles `SHIPPER`, `LOGISTICS_PROVIDER`, `HYBRID`; patrón `DIRECT`.
- Fuentes `OWN`/`EXTERNAL`, dimensiones `pallets`/`weight_kg`/`volume_m3`/`units` y dimensión principal activa.
- Split y declaración explícita de cargas homogéneas. Sin homogeneidad, no se presume compatibilidad universal; no se agrega multiparada.
- Moneda ISO de tres letras, minor units 0–6 y `ROUND_HALF_UP` de T1.
- Costo propio `OWN_OPERATING_CYCLE`, tarifas externas `PER_TRIP`/`PER_KM` y billing `ONE_WAY`/`ROUND_TRIP`.

Role sólo describe la operación en el contexto/copy. No concede permisos ni selecciona runtime, solver o engine. No se calcula ningún costo o plan en setup. Los hashes usan la canonicalización T1; no hay defaults financieros inferidos de datos live ni conversión FX.

## Model Versioning

Admin edita el borrador mediante `expected_revision` y publica una **fila nueva append-only**. La revisión avanza; se conservan `config_jsonb`, config hash, contract descriptor/hash, registry, autor, fecha y revisión fuente. UPDATE/DELETE de Version publicada siguen bloqueados por los guards T2.

El descriptor referencia los schemas estáticos T1 de Demand/Resource y el config hash. **No es el compiler de CSV ni genera templates de T4.** La referencia estructural privada `ULTIMATE_FOUNDATION_V1` declara D1/D2, dominio v1 y ejecución cerrada; no resuelve estados ni reemplaza el graph T5.

Dos Cases reutilizan la misma Version. Publicar v2 no modifica v1 ni rebinds históricos. La identidad de publicación permite replay de la misma intención después de editar el borrador; otra publicación con revisión obsoleta obtiene conflicto. La prueba concurrente tiene un ganador CAS y un rechazo, no dos versiones del mismo intento.

## Decision Case implementation

El Case Ultimate durable se crea antes de cargar archivos. Se guardan ID, nombre/descripción, Version publicada, modo, horizonte DATE, policy/hash, creador e intención de creación. No se aceptan Orders/Fleet, IDs fake ni campos de ejecución en el DTO de setup.

La Version queda ligada **desde la creación**, incluso antes de admission. DTO y SQL impiden cambiarla. `PlanningContextV1` devuelve los UUIDs/versiones, horizonte, modo, snapshot T1 de Model, moneda, policy y hashes, Pack/version/manifest y referencia estructural. Es serializable/hashable y declara `admission_available=false`. Nombre/descripción/Owners y reloj de freeze quedan fuera del hash matemático; permanecen en la respuesta de metadata/responsabilidades.

Las rutas nuevas son `/api/platform/ultimate-foundation/capabilities`, `/api/platform/logistics-models`, `/api/platform/logistics-models/{id}`, `.../{id}/versions`, `/api/platform/logistics-cases` y `.../{id}/context`, con sus métodos GET/POST/PUT/PATCH pertinentes. No se agregaron endpoints de Run, ingestión, resultados ni LLM.

## Case Policy / Horizon

Se soportan `DAILY`, `WEEKLY`, `MONTHLY`, `CUSTOM`, siempre con `planning_start` y `planning_end` DATE concretos e inclusivos, y `start <= end`. Los presets sólo proponen fechas; las fechas guardadas son la autoridad. Se prueban límites de mes y año bisiesto, fechas sin hora y edición inválida con rollback.

`OPERATIONAL`/`SIMULATION` se persisten como contexto; no hay motor Simulation nuevo. Los seis goals de T1 se conservan. Hard guardrails y preferences son colecciones separadas, con enums/ratios validados. CUSTOM exige preferencias; sus pesos suman exactamente 1. La UI convierte porcentajes a strings decimales de hasta cuatro lugares, sin floats en el wire contract. T3 no implementa la matemática T7.

## Owner / Permissions

Se reutilizan membership, responsabilidades y `platform_assign_decision` vigentes. No se reconstruye actor histórico, no se altera Data Owner/Apply ni aparece una entidad Approver nueva.

- Admin crea/publica Models y asigna Owners. Al crear Case debe elegir una persona activa/elegible con responsabilidad `decision_owner`; se asigna atómicamente a D1 y D2.
- Operator puede usar una Version publicada y crear Case con Owner pendiente; no se le otorga una autoridad de asignación que antes pertenecía a Admin. Admin completa después las asignaciones. La UI lo explica y no permite autoasignación encubierta.
- En contexto existente se muestran Owners D1 y D2 por separado, cada uno con su timestamp CAS. Sólo Admin los cambia; una asignación obsoleta revierte también los cambios de contexto del mismo request.
- Viewer lee, con controles deshabilitados y escritura rechazada por backend/SQL. Miembro disabled y actor ajeno al workspace se rechazan.

La RPC checked recibe el tenant/actor del contexto verificado del backend y vuelve a validar membresía, DDA y permiso bajo el lock de escritura. La función pública sólo es ejecutable por `service_role`; no se abren escrituras directas a tablas nuevas ni helpers privados.

## Freeze behavior

Antes de la primera admission pueden editarse horizonte, modo, tipo y policy permitidos, con CAS. En el primer INSERT de Run workflow 2, un trigger toma locks **workspace → Case**, registra el freeze y deja que los guards T2 validen el pinning. Un INSERT inválido revierte también ese freeze.

Después se rechazan cambios matemáticos por SQL, incluso si se evita la UI o se intenta un UPDATE directo. Nombre, descripción y Owner conservan sus reglas; no reescriben Run, creador, aprobador, snapshots ni historial. La carrera multi-connection prueba que una edición espera al lock de admission y luego falla por CAS, preservando el horizonte admitido.

Los Runs de esta prueba son **fixtures sintéticos de metadata**: un Pack/version de fixture y una entrada Demand sólo satisfacen los guards T2 para observar el freeze. No hay publisher T4, admisión Ultimate pública ni ejecución de engine Ultimate.

## Empty Data Pack

Una transacción crea Case + Pack estable + Version inicial 1 vacía + Owners, cuando corresponden. Pack y Version usan UUIDs deterministas derivados del Case, con manifiesto vacío y hashes canonicalizados; no hay datasets placeholder. El current pointer queda coherente al commit y entry count es 0.

S3 prueba tenant/case binding, recarga, reuse de Model Version, rollback cuando falla el Pack y rechazo de un Case sin Pack coherente mediante las restricciones T2. El reemplazo legacy del pair se rechaza con 409 sobre Ultimate. No se implementó la publicación ni ingestión progresiva de T4.

## UI integration

La entrada T3 se muestra **debajo del Hero existente de DDA Logística** sólo con capability habilitada. Se conservan sus dos CTAs legacy. Nuevas vistas: library/editor/version history de Model y creación/contexto de Case. Home/Center recuperan el Case por contexto, sin forzar Upload ni simular readiness de Map/T5. Enlaces legacy a Map de un Case Ultimate se recuperan hacia setup.

La UI compone `.d-platform`, `.d-card`, `.d-field`, `.d-input`, `.d-select`, `.d-textarea`, `.d-button`, `.d-page-header` y `mountDialog`/loading existentes. `forms.mjs` agrega la composición funcional para drafts/CAS, no otro sistema visual. El único CSS nuevo está scoped y usa `--space-*`, colores/radios y typography actuales. No hay nuevas animaciones, fuentes, tokens o assets.

| Before | After | Why |
| --- | --- | --- |
| Controles/cards/diálogos nativos aprobados | Mismos componentes y tokens en Model/Case; 100 % de paridad de píxeles/estilos en la galería comparativa | Agregar setup sin deriva estética |
| Hero DDA y CTAs aprobados | Misma geometría/estilos; entrada nueva ubicada debajo | Mantener el contexto visual existente |
| No existía setup Ultimate recuperable sin pair | URL durable de Case/Model, sin archivo obligatorio | Cumplir Case antes del CSV |
| Revisión guardada y borrador local pueden divergir | Error CAS conserva borrador y ofrece descarte confirmado/recarga | Evitar pérdida u overwrite silencioso |
| Validación de campos individuales | Errores inline más resumen enfocable y links al campo | Acceso equivalente por teclado |

Evidencia real:

- [Galería before/after](evidence/visual-parity/parity.json): mismos datos/tema, 1440/1280/1024/768/390; **PNG y estilos calculados idénticos** con el CSS T3 cargado. Se capturaron además referencias al inicio de la fase.
- [Hero DDA real](evidence/dda-parity/parity.json): geometría y estilos calculados de todos sus descendientes idénticos a 1440/390. Desktop tiene paridad exacta de píxeles; mobile difiere en **4 de 172.840 píxeles**, confinados a una esquina antialiasada: 99,997686 % idénticos. Se conservan capturas y coordenadas; no se declara igualdad byte a byte móvil. No hay cambio de contenido/layout/tokens del Hero.
- [Responsive](evidence/browser/responsive-measurements.json): 1440/1280/1024/768/390 y estrés adicional 320, sin overflow del documento ni controles fuera del ancho. Capturas de los valores máximos y zoom200%.
- [Teclado](evidence/browser/keyboard-focus.json): Tab real en desktop/mobile, foco visible/alcanzable, labels; W3 prueba Escape/retorno del diálogo y resumen de errores.
- [Contraste](evidence/browser/case-contrast.json): 56 elementos de texto/controles, mínimo **6,1618878:1**, cero fallos. Reduced motion y tap real en contexto touch también verificados.

## Database / RPC y rollback

La migración `20261026161050_ultimate_case_models.sql` fue creada con CLI Supabase 2.122.0 y aplicada **sólo a bases locales desechables**. Agrega siete columnas: flag privado, borrador/hash/intención de Model, revisión fuente de Version y tipo/intención del Case. Agrega validadores/RPC/guards y la referencia estructural; extiende exclusivamente el reader Home existente con un booleano de contexto recuperable.

[Schema boundary](evidence/schema-boundary.json) confirma: default flag **false**, cinco filas legacy de datasets/Case/Run/aprobación intactas, ACLs de relaciones y funciones existentes intactas, default ACLs y RLS policies intactos. SQL usa `SECURITY DEFINER` checked y `search_path=pg_catalog`; no hay nuevo grant directo de escritura. Los tests afirman PostgreSQL 17 y ownership del contenedor T3.

Rollback funcional: mantener/desactivar `ultimate_foundation_enabled` por el futuro procedimiento autorizado de release; se cierran escrituras nuevas y continúan lectores de contexto. No borrar Versions, Cases, Pack ni historia. Aquí no se aplicó ningún cambio remoto ni se activó una cohorte productiva.

## Tests executed

Candidato de 24 archivos registrado en [candidate.json](evidence/candidate.json). Python/SQL/API conservan exactamente los archivos sobre los que pasaron sus gates. Se ajustó primero el wait explícito de readiness de W3 y después el dirty state de los formularios T3: comparación independiente del orden de claves JSON, baseline explícito de policy y descarte del draft si los valores no cambiaron. Este último ajuste volvió a ejecutar B-NODE y W3 completos, con una regresión nueva para el no-op/reload. [QA reuse](evidence/qa-reuse.json) y [reuse del ajuste dirty](evidence/qa-reuse-dirty-fix.json) documentan consumers y hashes. Comandos, runners, timestamps, logs y hashes están en [command ledger](command-ledger.json) y [test ledger](test-ledger.json).

| Suite | Estado final | Tests | Failures | Errors | Skips | Wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B-PY | PASS | 473 | 0 | 0 | 0 | 18,780 s |
| B-NODE | PASS | 132 | 0 | 0 | 0 | 1,952 s |
| U3, incluido en B-PY | PASS | 17 | 0 | 0 | 0 | incluido |
| S3 | PASS | 25 | 0 | 0 | 0 | 34,836 s |
| W3 | PASS | 9 | 0 | 0 | 0 | 80,506 s |
| Focal legacy API | PASS | 3 | 0 | 0 | 0 | 67,825 s |
| Focal legacy Browser | PASS | 3 | 0 | 0 | 0 | 17,204 s |

Python 473 = baseline 456 + U3 17; Node 132 = baseline 128 + cuatro casos nuevos. U3 no se suma otra vez al total ni se repite sólo por su alias. No se usó una suite vacía o skip como PASS. No se repitieron Browser/E2E/SQL históricos completos.

Intentos previos se conservan en `evidence/attempts/`: fixture SQL sin admissions de identidad habilitadas; deduplicación correcta de datasets con raw hash inicialmente repetido; usuario Viewer ausente del fixture de login; foco medido antes de terminar scroll; timeout de carga inicial de 12s del octavo W3; y un ECONNRESET al refrescar la sesión del fixture desde el helper de inspección. Se corrigieron fixtures/esperas, manteniendo assertions funcionales. El helper permite un retry de Playwright sólo para ECONNRESET del refresh local, nunca respuestas HTTP de negocio ni escrituras de Model/Case. Se redactaron headers efímeros del log de transporte y se registraron ambos hashes. El primer comparador PNG estricto del Hero falló por los cuatro píxeles de esquina móviles; se documenta la medición completa, sin cambiar producto para ese rasterizado. Ninguno queda como fallo abierto del candidato.

## Legacy regression assessment

Además de Python/Node, los focales API validan library/metadata/CAS/tenant, Data Owner + Apply, Owners independientes, aprobación real y atribución creador/aprobador, archive/restore e historial. Los tres focales Browser cubren nuevo Case legacy hacia Data, continuación D1 aprobado → Config D2 y selector de Case/URL/foco.

Se conserva workflow 1 y su pair Orders/Fleet. No se convierten Cases existentes, no se reescriben Runs/aprobaciones y no se cambia invalidación downstream. Los guards nuevos se aplican a workflow 2 y las rutas nuevas no reemplazan las anteriores. T1 dominio/engines/result contracts y T2 schema/reportes conservan sus bytes.

## Deviations

1. `PlanningContextV1` tipa la fase pre-admission. El `FrozenCaseContext` T1 exige un read set no vacío: reutilizarlo para un Pack vacío introduciría IDs/lecturas ficticias. El DTO T1 sigue intacto; T3 no fabrica ese read set.
2. El Owner inicial es una asignación de negocio por nodo, no una columna/entidad Case Owner nueva. Admin asigna D1/D2; Operator conserva la posibilidad de crear pendiente sin recibir permiso de Admin.
3. La referencia estructural privada de foundation es versionada e inmutable, distinta de los fixtures T1/T2; execution permanece false. No se implementó resolver/graph de T5.
4. Los límites y esperas de W3 pertenecen al harness nuevo: espera `DOMContentLoaded` y readiness real, acotada a 30s; el helper de inspección tolera un único ECONNRESET de refresh. No se bajaron checks de negocio, contraste o foco; el runtime de aplicación no cambió por estos ajustes.

Estas adaptaciones están dentro del alcance T3 y no requieren rediseño contractual de T2.

## Risks

- La foundation queda cerrada por defecto. No está habilitada en producción y no constituye una admission Ultimate usable; apertura/release y fases posteriores requieren su autorización correspondiente.
- El descriptor Model referencia el ABI estático; el compiler, ingestión/publicación de Pack, graph y ejecución siguen pendientes de sus fases. La UI no promete que estén implementados.
- La library de Models y los candidatos del Equipo están paginados; el detalle de un Model entrega su historial de Versions completo. Un volumen muy alto de publicaciones necesitará paginar ese historial en una fase autorizada.
- Los tests usan Auth/Storage contract fixtures locales con API/PostgREST/PostgreSQL reales. No equivalen a deploy/piloto productivo; no se observó ni disparó un pipeline.

No hay regresión nueva abierta ni STOP CONDITION T3 observada.

## Gate Evaluation

| Gate T3 | Estado | Evidencia |
| --- | --- | --- |
| Scope/baseline/Skills | PASS | Checkpoint 392, scope 24, 57 entradas T2 verificadas y Skills ledger |
| Model reusable + append-only + reuse histórico | PASS | U3; S3 01–03/16–17; W3 01/07/08 |
| Case durable antes del CSV + Pack atómico | PASS | S3 04/06/10/23; W3 01/05 |
| Role, permisos y tenant | PASS | S3 10–15/18/24; W3 03 |
| Binding inmutable + CAS + freeze SQL | PASS | S3 05/08–09/20–22; W3 02/08 |
| Contexto reproducible/goal/horizonte | PASS | U3; Node; S3 04/07–08/19; W3 reload |
| Preservación de metadata/Owner/historia | PASS | S3 20/25; focales legacy API |
| UI Preservation / responsive / a11y | PASS | W3, cinco anchos comparables, estrés 320/zoom200/touch, contraste y foco |
| Legacy regression | PASS | B-PY/B-NODE y seis focales API/Browser |
| Sin ejecución Ultimate nueva ni T4 | PASS | Capabilities false, readiness/reemplazo legacy 409 y scope diff |
| Sin producción/push/infra | PASS | Runners locales, flag default false, HEAD sin cambios y staging vacío |

## FINAL DECISION

**GO — T3 completado. T4 puede ser solicitado.**

La ejecución termina en T3. No se ejecutó T4, ni commit, push, deploy o modificación de producción.
