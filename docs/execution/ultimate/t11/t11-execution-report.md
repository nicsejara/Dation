# T11 — Certificación transversal Ultimate MVP

Fecha: 2026-10-28. Alcance autorizado: exclusivamente T11. Fuente: `DATION_FINAL_MASTER_EXECUTION_PLAN.md` y aprobación formal de T10. **No se ejecutó T12, no hubo push ni despliegue.**

## Baseline T10 y checkpoint

Baseline previo al checkpoint: `ef997235a30251fbf7ae53690ed738092ee973d8`. Se verificaron los 28 archivos del manifest T10 y se preservaron los 15 Execution Reports identificados, sin cambiar sus hashes.

Checkpoint local autorizado: **`32b85681907a8d7b7811a9e16ae1988941b3d3d1`**, `Checkpoint Ultimate MVP functional candidate through T10`; árbol `7ff3c67da91a3a9f266db1cd3838c472aa85d2a0`. Incorporó el estado acumulado de T0–T10 sin cambiar su contenido. No se publicó. El working tree quedó limpio tras ese checkpoint; los cambios posteriores son fixes y evidencia T11.

Se archivaron 1.835 archivos / 81.457.552 bytes. Manifest SHA256 `b180c8b1258f728ef5473f0e913ffadea6d17e35bacd5cf4588399cc4df5d7f2`; tar SHA256 `1908cb3b0fd03e55a8140ac432460bc62f12742405ea729167118f3e11d703aa`. Archivo de recuperación: `/workspace/work/dation-t11/post-t10-worktree.tar.gz`. El tar permanece fuera del repositorio. [Inventario](evidence/post-t10-file-manifest.json), [checkpoint](evidence/checkpoint.json), [preservación](evidence/scope-preservation.json).

## Skills utilizadas

[Ledger](skills-ledger.json): `design-system`, `emil-design-eng`, `ui-ux-pro-max`, `break-ui`, Supabase, Supabase Postgres y cloud runtime. Se conservaron las guías y hashes locales de T10; se revalidaron las fuentes vigentes de runtime/Supabase/Postgres. Aplicación acotada a preservación, permisos, migración/restore, responsive y teclado. No se generaron tokens, paletas, componentes de otra biblioteca ni animaciones. No se inició una auditoría general ni se invocaron `review-animations`/`improve-animations`.

## Fixes de certificación y fronteras productoras

| Frontera | Falla demostrada | Corrección |
|---|---|---|
| T8 Config → admission | El CTA seguía inactivo pese a estar habilitado el runtime real; la capability antigua del graph no representaba admission D1 | Consulta del `run-context` autorizado; CTA según `admission_available`; POST al endpoint existente, con contexto/Pack/Model/policy exactos y source D1 exacto para D2. Sin nueva autoridad en frontend |
| T8 retry/accessibility | Perder la respuesta de un POST ya aceptado dejaba sin foco el control deshabilitado | Conserva UUID/cuerpo por intención; evita doble submit; status/alert y retorno de foco tras error si el usuario no lo movió a otro control |
| T6 envolvente privada | DTO de 100 órdenes/40 recursos y guard de 40 recursos rechazaban la envolvente de 500/50 indicada en el plan | DTO acotado a 500/50 y guard a 50; rechazo 501/51. No aumentaron slots, variables, tiempo nativo ni presupuestos determinísticos |
| T6/T7 construcción/validación | Revalidaciones redundantes de la misma evidencia y serialización repetida del chunk creciente | Validación final tipada y certifiers conservados; filas canonicalizadas una vez, tamaño incremental, árbol canónico escalar optimizado y cuerpos verificados reutilizados únicamente durante una validación local |
| Harness S3/S5 | Labels incompatibles con el sandbox compartido T11 y fixtures previos al admission T8 | Ownership explícito; admission checked real para los escenarios afectados; se sigue comprobando historia y frescura |
| Harness E2E/browser | Imports directos sin backend en path; comparación legacy que incluía columnas nuevas; locator estricto; expectativas de navegación anteriores a T5/T10 | Paths explícitos; preservación exacta de todas las columnas originales; locator del control real; Dashboard con packages publicados por worker real; espera del estado listo de formulario/status |

Archivos de producto: `domain` no se rediseñó; cambian `engines/assignment/{transport_contracts,transport_plan,transport_policy_result}.py`, `engines/common/day_resource_feasibility.py`, `results/{assembler,validation,canonical}.py` y `static/js/dispatch/cases/ultimate-decision-map.mjs`. El resto de los cambios son tests/harness/documentación. No hubo cambios de CSS, assets, migraciones, configuración funcional de producción, Docker del proyecto ni infraestructura.

Los vectores de serialización se obtuvieron del `ArtifactBuilder` post-T10 congelado. Comprueban bytes/hashes/IDs/cardinalidad para vacío, Unicode/Decimal/NULL, frontera de 100 filas, chunks grandes UTF-8 y binding D2. No se cambió matemática para coincidir con snapshots. Rechecks focales: 106 tests de productores/serialización y 92 de contratos/canonical/consumers, PASS.

## Full Test Matrix

Los conteos siguientes son **casos activos únicos**. Los aliases ALL-U/PERF/RESTORE/CONSISTENCY no se suman por segunda vez. El ledger relaciona discovery actual con los IDs de las ejecuciones completas y sus rechecks; las primeras fallas permanecen en los logs.

| Gate | Resultado final | Evidencia |
|---|---|---|
| B-PY | **FAIL — 687 tests / 4 failures en 2 métodos; 0 errors/skips**, 366,575 s | `evidence/logs/b-py-final.log` |
| B-NODE | PASS — 153; cero fallos/skips/cancelados | `evidence/logs/b-node-final.log` |
| B-BROWSER | PASS — 290/290; cero casos pendientes/skips | [Coverage](evidence/browser-coverage.json); pasada completa inicial, 42 rechecks PASS, últimos 3 PASS y 2 tests nuevos T11 PASS |
| B-SQL | PASS — 162/162; cero pendientes/skips | [Coverage](evidence/sql-coverage.json); 133 PASS iniciales, S3/S5 44 PASS y RESTORE11 PASS; unión sin duplicados |
| B-E2E | PASS — 115/115; cero pendientes/skips | [Coverage](evidence/e2e-coverage.json); 85 PASS iniciales, 33 focales y CONSISTENCY11 4 PASS; unión sin duplicados |
| ALL-U | **FAIL** — módulos funcionales cubiertos; PERF11 incluido en la unión falla | Unión de módulos entregados T1–T11 en los gates anteriores, sin ejecutar aliases redundantes |
| CONSISTENCY11 | PASS — 4 tests | `evidence/logs/consistency-certified.log` y matriz por consumer |
| RESTORE11 | PASS — 1 drill, 133,039 s | `evidence/logs/restore-final.log` |
| PERF11 | **FAIL — 3 excesos del presupuesto + 1 assertion de harness** | `evidence/performance-final/engine-assembler.json` |

Comandos desde `backend/`: `python -B -m unittest discover -s tests -v`; `node --experimental-test-isolation=none --test tests/test_*.js tests/test_*.mjs`; browser con `PYTHONPATH=tests/browser` y Chromium; SQL con `DATION_SQL_TEST_CONTAINER` owned; E2E `python -B tests/e2e/run_suite.py`. El runner E2E conserva modo full por defecto y marca explícitamente `FOCUSED_RECHECK` si recibe `--module`. Node sin aislamiento cuenta las assertions reales, según el baseline del entorno.

La primera pasada browser registró 3 failures/23 errors. Se reprodujeron y repararon los casos concretos; no se subieron timeouts globales ni se omitieron asserts. Los últimos tres rechecks pasaron. El caso ASGI que se bloqueó en el sandbox restringido pasó aislado en 0,069 s con las condiciones del baseline; el intento bloqueado se conserva, sin contarlo como PASS. La ejecución final Python usa esas condiciones.

## D1 Certification

Capacidad vectorial garantizada, split/non-split, cupos EXTERNAL finitos, unidades/reuso OWN, consolidación, prioridad, cobertura parcial, costos conocidos/NULL, estados de alternativas, reasons con evidencia, Sankey y Review conservados. Oracles pequeños independientes y certifiers permanecen activos; no se eliminó validación para acelerar.

El costo consolidado se reconoce una vez por Trip en CSV, la utilización sigue siendo ponderada y cada corte del Sankey conserva assigned sin sumar ambas capas como demanda adicional. Abrir Compare no ejecuta el engine. FEASIBLE/UNKNOWN no se convierten en óptimo ni en inevitable infeasibility.

## D2 Certification

D2 consume únicamente el D1 aprobado exacto por Run/fingerprint. No reasigna órdenes ni recursos. Dispatch/arrival/margin/status/OWN occupancy son hechos del producer. EXTERNAL conserva semántica sin retorno. PRE_HORIZON, AT_RISK, LATE y UNSCHEDULED no desaparecen para mejorar métricas; las fechas fuera de horizonte no se recortan.

Se preservaron expected compliance frente a strict ON_TIME, intervalos OWN de fin exclusivo, viajes de un día y witness para múltiples unidades. Gantt, Service, export y contexto conservan fechas certificadas.

## Cross-consumer consistency — R1–R18

CONSISTENCY11 ejercita endpoints y artifacts reales del mismo Run/FP: Dashboard, Details completos/paginados, CSV, JSON completo, IA, Review y Entity. D1 y D2; D2 drawer verifica además el parent original.

| Criterios | Resultado / evidencia |
|---|---|
| R1–R3 | PASS funcional: costo consolidado una vez, utilización ponderada y cortes Sankey conservados; oracles T7 + consumers reales |
| R4–R8 | PASS funcional: NULL no se convierte en cero, capacidades/tipos/alternativas/reasons/bytes/bindings validados y artifact íntegro obligatorio |
| R9–R13 | PASS funcional: fechas, estados, compliance y OWN/EXTERNAL entre D2 Core/Gantt/Service/CSV/context; conservación de IDs y witness |
| R14–R16 | PASS: late response descartada, binding exacto de selección/turn, adversarios IA, permisos/Pack/upstream revalidados antes de approve |
| R17 | Payloads/lazy/paging PASS; **certificación de escala/tiempo completa depende de PERF11**, ver limitaciones |
| R18 | PASS: crash/upload/finish, lease loss, retries y Pack concurrente ejercitados con SQL/worker/API reales; no publicación parcial |

## Lineage y routing — L-A–L-F

| Escenario | Resultado |
|---|---|
| L-A | PASS: Nueva D1 → Config D1, mismo Case/nodo, nueva intención; no crea Decision ni Branch |
| L-B | PASS: Nueva D2 → Config D2; parent D1 A exacto, su aprobación upstream se conserva |
| L-C | PASS: abrir/cancelar Config no invalida; admission de D1 B aplica supersession/downstream bajo checks, preservando A y sus approvals |
| L-D | PASS: History/reload/Back/Forward mantienen Run/contexto y preferencia por aprobación vigente frente a candidata posterior |
| L-E | PASS: D2 A/B siguen D1 A después de aprobar D1 B; D2 C usa B. Drawer histórico sigue leyendo A |
| L-F | PASS: replay antiguo sin efectos nuevos; enrichment sólo afecta consumers; inputs consumidos invalidan closure; metadata/Owner no reescriben matemática/actor |

Evidencia: módulos `test_ultimate_graph`, `test_ultimate_d1_result`, `test_ultimate_d2_lineage`, `test_ultimate_consumers`, W5/W10 y las regresiones legacy de lineage. No se agregó entidad Branch ni lógica “latest” para sustituir provenance.

## Migration rehearsal / Fresh install / Upgrade

S2 aplica baseline y el conjunto completo de migraciones en bases owned. Fresh y upgrade conservan catálogo, constraints, índices, RLS/grants/functions y datos legacy de comparación. La comparación legacy preserva exactamente cada columna preexistente y verifica explícitamente la cohorte v1; las columnas Ultimate aditivas no se confunden con pérdida de historia.

No se aplicó migración nueva T11 ni se ejecutó migration-history repair o baseline replay sobre una base existente de producto. [Coverage SQL](evidence/sql-coverage.json).

## Restore y rollback compatibility

[Restore](evidence/restore-final/), incluyendo inventario de hashes en `backup-*/restore.json`, catálogo efectivo, reset, journey y smokes. Backup PostgreSQL `pg_dump -Fc` con ACL + copia independiente de todos los objetos privados; `pg_restore --exit-on-error` a otra DB owned y nuevos procesos API/gateway. Se comparan todos los datos públicos/privados/auth, hashes de objetos y catálogo.

Se normaliza únicamente la representación de CHECK equivalente tras deparse; se conservan flags de validación y se comparan privilegios efectivos para roles, tablas, secuencias, schemas y funciones, incluida la herencia de PUBLIC. No se elimina una comprobación de grants para ocultar diferencias ACL.

Roles del cluster y claves del proveedor de autenticación del fixture son prerrequisitos preservados: este es un restore de **DB + objetos a un entorno aislado**, no un ensayo de reconstrucción de todo el proveedor cloud. El gateway privado del harness T8 maneja bytes reales de objetos; no se presenta como una restauración de la infraestructura Supabase productiva.

Lecturas después del restore: fingerprints/bindings/approvals/history/IA persistida/JSON completo idénticos. La imagen preparada dual-compatible leyó `assignment_v1`, `transport_plan_v1`, `day_scheduling_v1` y procesó un job legacy y un D2 nuevo. Smokes CLI read-only y pilot-write PASS; este último crea una cadena sintética nueva con APIs reales, sin tocar datos comerciales.

Imagen local bajo prueba: `sha256:9620e2bbbba26c429809bf40dbfbd55838a01c08b18dc5fcd79e65fd0f8ab7d4`. Rollback ensayado: `sha256:610a317cbde6fe000d034bdb9dce28ad9f7309a948b13eb804d4483e6dd48041`. Conserva backend compatible y Config anterior. No usa downgrade de schema ni reescritura de artifacts. Ninguna imagen fue publicada/desplegada.

## Security y privacidad

PASS: positivos del propio tenant antes de negativos foreign para Case/Model/Pack/Run/artifact/entity/export/context/review/history; wrong fingerprint 409; requests no autorizados 403/404 sin filtrar el fingerprint. RLS, grants, FKs compuestas, checked RPCs, Owner/Admin/Viewer/service role y múltiples conexiones cubiertos por SQL/E2E. Path arbitrario, prepared/missing/corrupt/rehashed artifacts y lease/replay no evaden los guards.

Storage privado del harness rechaza acceso directo sin service token; la API reautoriza cada lectura. No se emiten signed URLs para artifacts de resultado: el escenario de URL expirada se registra **N/A para esta superficie**, sin fabricar un PASS consultando una ruta inexistente.

Supabase Advisors se ejecutó sólo sobre un catálogo efímero owned. Resultado idéntico al baseline T8: WARN `public.profiles.tenant_read` y `dation_private.workspace_id`; cero hallazgos nuevos. [Resultado](evidence/advisors/advisors.json). Los WARN históricos siguen visibles, sin ampliar el alcance para rediseñarlos.

El contexto real no contiene customer identity/CUIT/SKU/invoice/revenue/margin/raw CSV comercial. El normalizador rechaza columnas extra según contrato. No hay service key en frontend. No se consumieron credenciales productivas en las pruebas; los procesos QA vacían variables Supabase/GCP/LLM heredadas.

## Dation IA adversarial testing

Provider stub determinístico y fallback: inventar métrica/reason/alternative, modificar/aprobar plan, mezclar Run/tenant, fake what-if o completar información ausente no produce nuevos hechos ni mutaciones. Contexto/turn/entity/evidence hashes quedan ligados a la misma publicación. La pregunta inyectada se trata como datos; requiere nueva corrida cuando corresponde. No se usó un LLM live para certificar matemática.

## Artifact integrity

PASS: ausencia/modificación de byte/hash/Run/workspace/fingerprint, PREPARED o manifest parcial bloquea el acceso/publicación/approve/export correspondiente. No hay sustitución por `[]`, cero o “sin alternativas”. JSON completo comprueba todas las refs; CSV conserva el driver certificado completo. Los vectores post-T10 verifican compatibilidad byte a byte del builder optimizado.

## Clean Slate reset y full journey

Reset sólo admite `CertificationSandbox` con labels owner/execution T11, DB/prefijo propios y workspace marcado con nonce. No acepta URL de producción ni un workspace arbitrario. Elimina datos de negocio y prefijos de objetos únicamente del tenant marcado; segunda ejecución idempotente; marker ajeno rechazado. Preserva schema, migraciones, Functions/RLS/registries/Definitions, usuarios/system configuration y el workspace B con su historia legacy aprobada. La supresión de triggers se limita a la transacción de limpieza del sandbox explícitamente marcado.

Tras reset: cero Models/Cases/datasets/Runs; Model → versión → Case → Map DATA_REQUIRED → Data Owner → templates/upload Demand+Resources → Pack → D1 READY → Config/execute → Dashboard/Details/IA/Review/approve → D2 READY → Config/execute → Dashboard/Details/IA/Review/approve. API/SQL/worker reales, sin inserts SQL de negocio para completar el journey.

Un segundo recorrido lo hace enteramente la UI desde un sandbox inicialmente vacío. Captura la pérdida de una respuesta 202 y retry con el mismo UUID/body, un único Run por nodo, exacto upstream y approvals actuales. No depende de Orders/Fleet legacy, seed comercial, caché previa ni aprobación oculta.

## UI Preservation / responsive / accessibility

PASS: 13 superficies × 5 viewports = **65 comprobaciones/capturas**, más 10 capturas Config before T10 con los mismos datos/estado. Incluye IA/Review para ambos nodos. Tamaños 1440×900, 1024×768, 768×1024, 375×812 y 320×640; ancho del documento ≤ viewport+1; tablas/charts usan los scrollers existentes.

| Before | After | Why |
|---|---|---|
| Config con CTA inactivo y mensaje fijo aun con admission habilitado | Mismo shell y CTA; estado del endpoint autorizado y ejecución idempotente | Completar el flujo funcional ya definido, sin otro diseño |
| Al perder respuesta, deshabilitar el CTA perdía foco | Vuelve al CTA habilitado si no hubo cambio de foco del usuario | Retry por teclado accesible, conservando intención |

Se revisaron capturas comparables, incluidos Config y Dashboard a 320 px. CSS/assets/tokens/global shells conservan hashes. No nuevos componentes paralelos, framework, iconos, Hero art ni motion. Teclado, foco visible/retorno/trap, Escape, dropdown/disclosures/tabs/labels/selected states, contraste, reduced motion y zoom200% cubiertos por W3/W4/W5/W10 y regresiones browser. El estado error/retry de Config se prueba contra una respuesta de admission efectivamente perdida, no con un fake runtime.

UI-P1 referencia, UI-P2 integración nativa, UI-P3 reuse/tokens, UI-P4 comparación responsive, UI-P5 interacción/a11y y UI-P6 Skills trazables: PASS de preservación. [Matriz](evidence/browser-certification/responsive-matrix.json).

## Performance

**FAIL — presupuesto de ejecución completa de 90 s excedido en las tres muestras aisladas.** No se subió el límite ni se redujo la prueba para declarar PASS.

Benchmark: 500 órdenes, 50 recursos EXTERNAL, 31 días; presupuesto de alternativas 3, una alternativa material publicada; 128 Trips, 2.816 variables declaradas, máximo nativo observado 6.735 constraints. Estado FEASIBLE y cobertura parcial, con `CANDIDATE_MODEL_BUDGET` explícito. Tres procesos nuevos, sin browser/SQL/builds compitiendo por CPU; runtime QA de 2 CPU / 8 GiB compartidos. No es una promesa de rendimiento productivo.

| Muestra | Motor D1 (s) | Assembler D1 (s) | Subtotal (s) | Peak RSS (KiB) |
|---|---:|---:|---:|---:|
| 1 | 67.612 | 32.501 | 100.113 | 722732 |
| 2 | 53.097 | 39.032 | 92.130 | 723040 |
| 3 | 56.422 | 41.584 | 98.007 | 723364 |

p50 del subtotal **98.007 s**; p95 nearest-rank con n=3 **100.113 s**. Es un **límite inferior**: excluye admission, verificación de inputs, uploads, Storage y finish/publicación. Ya falla antes de agregarlos. No se certificó la ejecución completa en escala.

Payload D1: package 343.055 B, primary visual 45.693 B, 83 artifacts / 43.500.169 B, máximo chunk 1.047.272 B / 100 filas. Respeta los presupuestos de bytes; no compensa el exceso de tiempo. Los tres resultados tienen el mismo fingerprint `6de1eeb6b9c20c9a4c9ac5bd07db035bbebed972cba7ef3bb84e34848f858014` en este runtime.

D2 se midió sobre **otro D1 real y certificado de 100 Trips**, con 50 recursos y 31 días; no se fabricó un upstream de 1.000 Trips ni se sustituyó el parent del caso parcial. Motor D2 0,989–1,414 s; assembler 0,503–0,560 s. El escenario que necesitaría 1.000 Trips para cobertura completa sólo publicó sus 128 Trips acotados. El test separado de 1.000 filas prueba serialización/chunking (10 chunks / 770.470 B), **no** capacidad del engine para generar/programar 1.000 Trips.

El cuarto failure es del harness nuevo: exige `constraints>0` en todas las llamadas nativas, pero el trace incluye subproblemas válidos con 128 variables y cero constraints. No demuestra falsa optimalidad del resultado principal (que sigue FEASIBLE), ni sustituye los tres fallos reales del presupuesto. Queda registrado como reparación pendiente del harness; no se lo elimina para presentar una suite verde.

HTTP real (fixture pequeño, n=7 por ruta) midió resultado, visual, página de Details y entity, incluyendo la recuperación privada subyacente. p50 D1 0,150–0,216 s; p95 0,176–0,311 s. p50 D2 0,160–0,348 s; p95 0,297–1,045 s. [Mediciones completas](evidence/consistency-certified/http-performance.json). No se extrapolan a la carga de 500/50.

Dashboard inicial no pidió Details/entity/IA/context completo; tabs y selección son lazy, con paging explícito. Peak RSS de probes hasta 723.364 KiB (~706,4 MiB), sin certificar margen de un worker productivo. La consulta read-only de límites Cloud Run devolvió 401; no se cambiaron recursos. Tras comprobar el exceso del límite inferior no se ejecutó otro job de escala ni se declaró PASS para publicación/Storage/memoria completos.

Los intentos de optimización se limitaron a construcción/validación/serialización; los guards y oracles permanecieron. El resultado final sigue sin cumplir. El perfil diagnóstico interrumpido y las probes con browser concurrente son diagnósticos, excluidos de los tres samples finales.

## Legacy compatibility

PASS: coexistencia real y regresiones de Orders/Fleet, Case legacy, assignment_v1, scheduling_v1, dispatch_v2, Home, Decision Center, approvals, exports, IA legacy e historia. El restore conserva un workspace legacy aprobado mientras resetea el tenant Ultimate. No se borraron rutas/tablas/readers legacy.

## Remaining risks / deferred issues

1. **Bloqueante:** el subtotal motor+assembler D1 excede 90 s en 3/3 muestras. Requiere remediación T11 en los productores T6/T7 y revalidación de consumers antes de certificar el job completo; no autoriza cambiar matemática, elevar timeouts o avanzar a T12.
2. **Pendiente:** corregir la assertion del harness sobre subproblemas sin constraints y reejecutar el gate afectado. B-PY/ALL-U no están verdes; no existe exención.
3. **No certificado:** tiempo completo de publicación/Storage a escala y margen contra el límite real del worker destino. Memoria observada de un subprocess no equivale al límite/peak del contenedor productivo.
4. La prueba de 1.000 filas es del serializer; el modelo acotado conserva cobertura parcial. No se promete capacidad comercial de 1.000 Trips.
5. Permanecen los dos WARN históricos de advisors. Restore requiere roles/auth del entorno destino preparados; no certifica reconstruir el proveedor cloud entero.
6. Los cambios T11 y el dossier quedan locales, pendientes de commit. El único commit creado fue el checkpoint post-T10 autorizado, sin push.

No se agregaron features: nodos/algoritmos/métricas/charts/IA nueva/conectores/Redis/XLSX/infra siguen fuera de alcance. No se rebajó el gate para declarar GO. Los logs iniciales fallidos se conservan para trazabilidad; sus fixes y rechecks están separados de la deuda no resuelta.

## Release Candidate Manifest

**No se congeló un release candidate.** [Estado bloqueado, versiones, migraciones, knowledge y rollback](release-candidate-status.json). HEAD local `32b85681907a8d7b7811a9e16ae1988941b3d3d1`; contenido de aplicación bajo prueba SHA256 `c56346625e436755bda53d45aec829162f31e8e2079ff24a469eafcfa8023918` (380 archivos, alcance explícito en [manifest](evidence/source-under-test.json)). Este hash no se presenta como certificación ni como hash de un candidato publicado. Las imágenes sólo existen localmente.

## Gate Evaluation

| Gate | Estado | Motivo |
|---|---|---|
| G-A alcance | PASS | Sólo T11/fixes demostrados; sin infraestructura/producción/nueva auditoría |
| G-C contrato | PASS | ABI/typed guards/gold bytes y los 28 archivos T10 preservados |
| G-D datos | PASS | Fresh/upgrade/mixed/restore y hashes/catálogo/ACL; 162 casos SQL cubiertos |
| G-E engine | PASS funcional | Oracles/conservación/timing/reasons; límites honestos; ningún cambio matemático |
| G-R resultado | PASS funcional / R17 escala BLOCKED | Consumers e integridad consistentes; rendimiento completo de escala no certificado |
| G-L lineage | PASS | L-A–L-F/races/replay/lease/history |
| G-S seguridad | PASS de negativos | Aislamiento/roles/RLS/grants/paths/cache; WARN históricos explícitos |
| G-P performance | **FAIL** | 92,130–100,113 s sólo motor+assembler frente a 90 s completos |
| G-UI preservación | PASS | 65 comprobaciones + before/after; sin CSS/assets/tokens alterados |
| G-ENV entorno | PASS para QA local | Suites/DB/worker/browser disponibles; bloqueo ASGI del sandbox identificado y resuelto para ejecutar |
| G-B suites completas | **FAIL** | 687 tests Python, 4 failures en 2 métodos; cero errors/skips; no se concede excepción |
| G-REL release | **BLOCKED** | T11 STOP; candidato sin congelar; T12 no autorizado, sin push/deploy |

**STOP — T11 no cumple condiciones para autorizar T12.**
