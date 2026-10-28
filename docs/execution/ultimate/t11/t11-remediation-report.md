# T11-R — Targeted D1 performance remediation + Python failure closure

Fecha: 2026-10-28 UTC. Estado final: **GO**. Fuente: autorización T11-R, Master Plan y STOP T11 previos. [Autorización preservada](evidence/remediation/T11-R-user-request.txt).

Alcance: exclusivamente T11-R. No T12, push, deploy, cambios de producción ni infraestructura. El reporte T11 original y sus 311 evidencias se preservan como historia del STOP; esta remediación no los reemplaza retroactivamente.

## Baseline

HEAD real: `32b85681907a8d7b7811a9e16ae1988941b3d3d1`, branch `main`, un checkpoint local adelante de `origin/main`. Se recuperó el working tree T11, incluidas sus modificaciones pendientes, y se compararon los hashes de las 380 fuentes de aplicación y del dossier. No se hizo reset, clean, descarte ni un nuevo checkpoint. La autorización fuente y su SHA se conservaron con la evidencia.

## Python failures root cause

Un failure C (expectativa incorrecta del harness): se exigían constraints explícitas en TODOS los subproblemas CP-SAT. El subproblema de dominio con 128 variables y 0 constraints es válido y OPTIMAL dentro de su scope; el modelo principal sigue FEASIBLE y tiene variables/constraints reales. La reparación exige counts no negativos, modelo estructural real acorde al count declarado y ausencia de MODEL_INVALID; no concede optimalidad global ni omite el escenario.

Tres failures A (performance real): 100.113139 / 92.129708 / 98.006691 s sólo motor+assembler. No son fallos funcionales ni se atribuyen a infraestructura para aprobarlos. Los cuatro se clasificaron antes de las modificaciones. No apareció una regresión funcional B.

## Performance profile / Bottleneck

La primera ejecución instrumentada exacta dio 96.275614 s: 54.861446 motor y 41.413291 assembler. El solver nativo consumió 4.026 s (~4.2%); Evidence, canonicalización y validaciones duplicadas dominaban. Se midieron tiempos inclusivos, exclusivos, CPU y stacks; la tabla exclusiva evita sumar fases anidadas dos veces. Inputs de la probe ya son DTOs normalizados; la construcción inicial del fixture se registra aparte y queda incluida en el assert final. El job real mide también admission, inputs, RPC, artifacts, uploads, verificación y finish.


Medición diagnóstica antes/después: 96.276 → 65.125 s. Tiempos exclusivos, sin doble conteo; los porcentajes usan el subtotal motor+assembler de cada perfil. Los tiempos inclusivos/CPU/calls y stacks están en [los JSON](evidence/remediation/profile-after-6/profile.json). Los guards están incluidos; el snapshot de diagnóstico se identifica en el perfil y no altera la medición formal.

| Fase exclusiva | Antes s | Antes % | Después s | Después % |
|---|---:|---:|---:|---:|
| artifact_canonical_serialization | 7.720 | 8.0% | 8.138 | 12.5% |
| candidate_generation_and_optimization | 0.576 | 0.6% | 0.379 | 0.6% |
| complete_evidence_reassembly | 7.621 | 7.9% | 0.000 | 0.0% |
| dataset_artifact_preparation | 0.139 | 0.1% | 0.098 | 0.2% |
| evidence_partition_construction | 2.862 | 3.0% | 1.976 | 3.0% |
| independent_assembly_plan_certification | 7.059 | 7.3% | 2.760 | 4.2% |
| independent_bundle_certification | 14.972 | 15.6% | 13.539 | 20.8% |
| independent_policy_certification | 0.141 | 0.1% | 0.389 | 0.6% |
| independent_structural_certification | 19.699 | 20.5% | 8.418 | 12.9% |
| native_solver | 4.026 | 4.2% | 3.533 | 5.4% |
| optimization_formulation_and_solves | 0.247 | 0.3% | 0.153 | 0.2% |
| policy_candidate:MAXIMIZE_OWN_CAPACITY | 2.356 | 2.4% | 1.420 | 2.2% |
| policy_candidate:MAXIMIZE_SERVICE | 1.771 | 1.8% | 3.196 | 4.9% |
| policy_candidate:MINIMIZE_TRIPS | 2.010 | 2.1% | 2.013 | 3.1% |
| policy_candidate:RECOMMENDED | 2.354 | 2.4% | 1.336 | 2.1% |
| recommended_and_alternatives | 0.184 | 0.2% | 0.145 | 0.2% |
| result_assembly | 1.041 | 1.1% | 0.605 | 0.9% |
| structural_plan_evidence | 21.449 | 22.3% | 14.079 | 21.6% |
| temporal_kernel | 0.051 | 0.1% | 0.032 | 0.0% |
| whole_evidence_merge | 0.000 | 0.0% | 2.915 | 4.5% |

Los tres objetivos alternativos se exploran bajo los presupuestos originales; sus tiempos inclusivos por objetivo se registran en cada perfil y no se suman nuevamente a esta tabla. `complete_evidence_reassembly` corresponde al adapter de filas sin tipar del baseline; después el merge de las particiones ya tipadas aparece como `whole_evidence_merge`, con validación del proof completo preservada. No hubo pruning, hints, concurrencia, timeouts nuevos ni cambio de estado de alternativas para acelerar.

## Changes

1. Reutilizar, dentro de una sola validación de bundle, las particiones de EngineEvidence ya verificadas por hash/canonicalización/schema. Se conservan los checks de delivery, cardinalidad, header, conflictos y validación del proof completo. No hay cache global ni entre tenants/Run/requests.
2. Congelar los mismos campos validados de ContractModel mediante su diccionario de campos, sin descriptor reads/setattr repetidos. No cambian freeze, exact numeric guards, frozen/extra-forbid/revalidate-always ni schemas.
3. Resolver una sola vez el import de canonical_tree para facts, conservando la función pura y sus guards.
4. Separar el constructor privado T6 de su runner. T6 público mantiene su certifier. T7 mantiene el certifier independiente económico, que incluye TODAS las comprobaciones estructurales; se evita ejecutar el mismo certifier T6 dos veces por propuesta.
5. Assembler conserva su validación independiente obligatoria final para cada plan y artefacto antes de retornar bytes. Reutiliza el EngineOutput y Package ya validados para ejecutar exactamente el mismo predicado de binding, en lugar de reconstruir otro ResultContractBundle. El constructor público ResultContractBundle conserva sus validadores. No se adelanta ninguna publicación.
6. Construir los resúmenes de candidatos y entidades una sola vez en las fronteras tipadas finales. Indexar los pares Order/Resource seleccionados para consultar pertenencia, en lugar de recorrer todos los Trips para cada par. Se conserva el conjunto, orden, IDs, facts, status y campos.

El delta T11-R frente al baseline tiene siete archivos de aplicación. No cambia solver/formulación/seed/budgets/alternatives, Transit, D2, dominio, contratos de datos, legacy, persistencia, ownership, approvals, invalidación, lineage, UI ni infraestructura. ContractModel es compartido por Ultimate: por eso se repiten contratos, U6/U7/U9 y B-PY.

## Correctness equivalence

El golden se capturó ANTES de la remediación, no se regeneró para acomodar una salida distinta. Compara package completo y los 83 IDs/hashes/sizes de artefactos. Fingerprint D1 esperado: `6de1eeb6b9c20c9a4c9ac5bd07db035bbebed972cba7ef3bb84e34848f858014`. Incluye assignments, Trips, costos, cobertura, métricas, reasons, Evidence completa y alternativas. También se preservan los vectores post-T10 de serialización y los 18 schemas JSON completos, comparando también los contratos originales previos al refactor. La cobertura parcial sigue siendo honesta: 128 Trips, 128 candidate slots, 2816 variables declaradas, hasta 6735 constraints del modelo principal, una alternativa material de tres objetivos explorados.

D2 se mide por separado con su parent D1 real certificado de 100 Trips, sin fabricar un parent de 1000 Trips. El stress de 1000 filas sólo certifica chunking del serializer. No se cambia el oracle ni se inventa cobertura completa.

## Before / After — formal PERF11 y job completo

Fixture exacto preservado: 500 Orders / 50 Resources / 31 días; `max_slots=128`, `max_variables=20000`, `deterministic_budget=5`, `kernel_budget=2`, seed 0. Candidate model limitado/honesto: 128 slots, 2816 variables declaradas, hasta 6735 constraints. Recommended FEASIBLE, cobertura parcial de 128 Trips; una alternativa material, tres objetivos explorados. Subproblemas nativos FEASIBLE/OPTIMAL, sin MODEL_INVALID.

| Muestra fría | Fixture/contract s | Motor s | Assembler s | Total s | CPU motor+assembler s | Peak RSS KiB |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0.025 | 38.358 | 23.688 | 62.072 | 61.383 | 755476 |
| 2 | 0.021 | 34.766 | 25.782 | 60.570 | 60.385 | 755336 |
| 3 | 0.021 | 33.537 | 26.166 | 59.724 | 59.331 | 755404 |
| 4 | 0.028 | 31.729 | 29.875 | 61.632 | 61.576 | 755668 |
| 5 | 0.022 | 36.111 | 28.108 | 64.241 | 64.193 | 755756 |

Antes (n=3): p50 **98.007 s**, p95 nearest rank/máximo **100.113 s**. Después (n=5, sumando además fixture/contract): p50 **61.632 s**, p95 nearest rank/máximo **64.241 s**, mínimo **59.724 s**. Delta p50 **−36.374 s / −37.11%**; máximo baja **35.872 s / 35.83%**. Ninguna muestra se descartó. [Samples completos](evidence/remediation/performance-opt6/engine-assembler.json), [resumen](evidence/remediation/final-performance-summary.json).

El golden completo coincide en 5/5 muestras: package 343055 B, visual 45693 B, 83 artifacts / 43500169 B, máximo chunk 1047272 B / 100 filas. D2 conserva fingerprint `ffab2ab4189c27c643e11f80a0a8cb0cf6eef7fcd199735433b5d9091b7b0040`. Serializer de 1000 filas: 10 chunks / 770470 B, sin pérdida de filas. No se presenta ese stress como 1000 Trips reales del engine.

Las dos primeras Runs de procesos API+worker nuevos usan la imagen final real y CSVs/Model/Case/Pack creados por APIs en un sandbox owned. El reloj comienza ANTES del POST /api/runs y termina al observar COMPLETED; abarca admission, validación/carga de inputs, cola, motor, assembler, preparación, 83 uploads, recuperación/verificación de todos los objetos y finish. No hay negocio precalculado ni cache entre muestras. El arranque del servicio/health anterior a la admisión se registra separado; la envolvente de 90 s es de ejecución de la Run, no un SLO de aprovisionamiento del servicio.

| Primera Run fría | Admission→COMPLETED s | Worker completo s | Worker CPU s | Peak cgroup MiB | Startup previo s |
|---|---:|---:|---:|---:|---:|
| 1 | 88.174 | 86.069 | 82.212 | 727.27 | 5.440 |
| 2 | 86.798 | 84.605 | 81.655 | 727.43 | 12.356 |

Job completo: p50 **87.486 s**, p95 nearest rank/máximo **88.174 s**; 2/2 PASS bajo **90 s**. Son las dos muestras predefinidas, sin repetir hasta obtener una favorable. Ensayos de versiones intermedias fallidos permanecen en el dossier. El test conserva timeout de observación 180 s sólo para registrar un exceso; el assert de aprobación sigue en 90 s.

| Etapa del worker/job | Run 1 s | Run 2 s |
|---|---:|---:|
| artifact_retrieval_index_preparation | 0.653 | 1.136 |
| checked_rpc_finish | 0.320 | 0.426 |
| checked_rpc_prepare | 0.426 | 0.632 |
| checked_rpc_prepared | 0.016 | 0.014 |
| input_snapshot_loading_verification | 0.017 | 0.009 |
| recommended_and_alternatives | 37.127 | 39.646 |
| result_assembly | 36.367 | 29.679 |
| storage_retrieval_verification | 5.344 | 6.170 |
| storage_upload | 5.537 | 6.674 |
| Other input contract/context + orchestration | 0.263 | 0.219 |
| Admission + queue + completion observation | 2.105 | 2.193 |

Input/context loading y contract validation están incluidos en el reloj total, el evento de verificación y el residual de orquestación, además de los checks internos del motor. La normalización de uploads pertenece a la preparación del Pack, anterior a solicitar una Run; no se mueve ninguna etapa de ejecución fuera del reloj.

Worker real acotado: **2 CPU / 1 GiB**; pico **762765312 B (727.43 MiB)**, margen **28.96%**, sin OOM y por debajo del assert de 90% de su límite. Probe RSS final máximo **755756 KiB (~738.04 MiB)**; baseline máximo 723364 KiB (~706.41 MiB). No se declara una reducción de memoria comparando RSS y cgroup. [Imagen](evidence/remediation/image-runtime.json): Python **3.13.16**, OR-Tools **9.15.6755**, Pydantic **2.14.0**; B-PY/probe host Python **3.13.5**, runtime exterior **2 CPU / 8 GiB**. La prueba completa acotada complementa la probe host; no se extrapola su tiempo.

HTTP de escala mide por separado cinco lecturas reales de result/primary-visual/details-plan después de completar cada Run, incluidos bytes y p50/p95. No se usa esa lectura posterior para descontar trabajo de publicación. [Run 1](evidence/remediation/full-worker-opt6/complete-cold-job-1.json), [Run 2](evidence/remediation/full-worker-opt6/complete-cold-job-2.json).

## Tests / Re-executed gates

Resultados finales:

| Gate reejecutado | Resultado |
|---|---|
| B-PY | **688 ejecuciones PASS**, 393.054 s, 0 failures/errors/skips; **680 IDs únicos** |
| PERF11 | Incluido en B-PY: seis métodos, cinco procesos fríos; payload/scale/bytes/budget PASS |
| Job completo de escala en imagen | **1 test / 2 escenarios fríos PASS**, 276.521 s totales incluidos setup/cleanup |
| CONSISTENCY11 | **4 PASS**, D1/D2 entre Dashboard, Details, CSV, JSON, IA, Review y Entity, incluidos negativos |
| E8 / T8 publicación | **8 PASS**, crashes/partial uploads/lost responses/lease/replay/history/Pack/permisos/integridad |
| U6/U7/U9 y serialización/contratos | **200 focales PASS** sobre la fuente final, más B-PY completo |
| Schema/correctness | **18 schemas idénticos**, 5/5 golden completo, vectores post-T10 PASS |

Los 12 rechecks CONSISTENCY11+E8 terminaron en 132.641 s, sin fallos/errors/skips. [Ledger](evidence/remediation/e2e-final/suite-report.json). El discovery actual E2E tiene **116 IDs**, todos cubiertos por 115 certificados previos, los rechecks afectados y el nuevo test de escala; cero missing/extra. No se cuentan aliases o rechecks como casos nuevos. [Coverage E2E](evidence/remediation/e2e-coverage-final.json).

Precisión del conteo B-PY: el discovery ya repetía ocho SchedulingEngineTests en T11; también están duplicados en la ejecución actual. Se conservaron, sin quitar cobertura ni reescribir tests ajenos. Los 688 son ejecuciones, 680 IDs únicos (baseline 687/679). Se verificó igualdad exacta entre IDs actuales descubiertos y ejecutados, con multiplicidades; cero missing/extra. [Coverage Python](evidence/remediation/b-py-coverage-final.json).

Comandos finales, desde backend/ y con variables Supabase/GCP/LLM productivas vacías:

```sh
python -B -m unittest discover -s tests -v
PYTHONPATH=tests/e2e python -B -m unittest test_ultimate_scale -v
python -B tests/e2e/run_suite.py --module test_ultimate_consistency --module test_ultimate_d1_result
```

Python host: `/workspace/Dation/.venv/bin/python`. Las variables de salida DATION_T11_* sólo ubican evidencias. Docker usa el socket local verificado; API y worker reciben credenciales sintéticas loopback del sandbox. El launcher observacional se monta read-only y no forma parte de la imagen de aplicación. No hace matemática ni cambia productores/validadores.



Focales tras cada optimización: 106, 200, 200, 200, 200 y 200 PASS. No se suman como tests únicos. La pasada B-PY final cubre PERF11, por lo que no se repite por alias. Su test del budget ahora suma fixture/contract + engine + assembler; timeout de observación 180 s y budget de aprobación 90 s sin cambios. Cinco subprocess fríos independientes, sin descartar muestras. Una assertion nueva compara publicación completa contra el golden previo: 688 ejecuciones, frente a 687 del baseline; IDs únicos y duplicados heredados se detallan en el ledger anterior.

Se conservaron la pasada B-PY intermedia fallida, todos los perfiles, el outlier instrumentado de 145.972 s, los ensayos completos opt4 105.773/95.869 s y opt5 79.489/103.574 s. El outlier sin datos CPU no demuestra infraestructura; queda registrado. Los errores iniciales del launcher fueron permisos 0600 incompatibles con UID65532 y WORKDIR asumido erróneamente: se corrigió a 0644 y Path.cwd(), no se tocaron permisos de producción ni el Dockerfile del proyecto.

## Previously-certified unaffected gates

B-NODE153, B-BROWSER290, B-SQL162 y la parte no afectada de B-E2E115 conservan su evidencia T11. No se ejecuta otra auditoría ni se repiten suites de UI/SQL sin cambios. Se repiten CONSISTENCY11 y E8/T8 porque la frontera de ensamblado afecta la publicación. Byte/schema equivalence y regresiones D2/legacy cubren los consumers; UI, CSS/assets/tokens, schema/migrations/RPC/RLS y ownership/approval/invalidation no cambian.

RESTORE11 previo conserva DB+objetos/hashes/catálogo/ACL/historia y reader/worker dual-compatible. Errata de alcance de esa evidencia: el overlay Config del Dockerfile temporal antiguo usó /app/app en una imagen cuyo WORKDIR es /app/backend; no prueba que se sirviera la Config anterior. Sí prueba los readers/worker/backend duales ensayados. No se atribuye a esa imagen una reversión visual que no realizó. T11-R no modifica UI; el rollback operativo sigue requiriendo cerrar admissions y drenar/recuperar los jobs antes de volver al runtime compatible, sin downgrade de schema ni reescritura de artifacts.

## Risks

- El margen temporal del peor job final es 1.826 s frente a90 s; la certificación aplica al fixture/runtime medidos, sin promesa de latencia bajo otras cargas.
- p95 empírico nearest rank de n=5 (probe) o n=2 (job completo) equivale al máximo; no permite inferir un SLO poblacional. Preservar todos los intentos y registrar CPU/memoria/env.
- Memoria probada en el worker local acotado a 1 GiB y 2 CPU; no afirma conocer los límites de producción (consulta anterior 401). No se alteran recursos para pasar el gate. T12 requiere autorización propia y validar las precondiciones del destino.
- Las imágenes y fuentes de QA quedan locales. HEAD identifica el checkpoint; las modificaciones T11/T11-R necesitan su manifest de working tree, no deben presentarse como si fueran contenido del commit HEAD.
- Persisten los dos WARN históricos de Advisors, sin findings nuevos atribuibles a esta remediación. Restore presupone roles/Auth preparados; no reconstruye el proveedor cloud completo.

## Gate evaluation

| Gate | Resultado | Evidencia / alcance |
|---|---|---|
| G-A alcance | PASS | Siete archivos de aplicación; sin auditoría nueva, features, UI, infraestructura o producción |
| G-C contrato | PASS | 18 schemas y bytes del package + 83 artifacts idénticos; validadores conservados |
| G-D datos | PASS preservado | SQL/restore/hashes/ACL anteriores, cero cambios de schema/migraciones/Storage protocol |
| G-E engine | PASS | U6/U7/U9/oracles e invariantes; solver/policies/Transit inalterados |
| G-R resultado | PASS | CONSISTENCY11/E8 reejecutados; R17 escala verificado con el job completo |
| G-L lineage | PASS | E8 historial/replay/Pack concurrente; fuentes y snapshots/approval sin cambios |
| G-S seguridad | PASS | Negativos de tenant/FP/Storage/integridad reejecutados; WARN históricos explícitos |
| G-P performance | PASS en entorno medido | 5/5 subtotales ≤64.241 s y 2/2 jobs completos ≤88.174 s; límite 90 s |
| G-UI preservación | PASS preservado | Frontend/CSS/assets/tokens idénticos a T11; ninguna Skill UI aplicada en T11-R |
| G-ENV QA | PASS | Python/Docker/SQL/API/worker reales disponibles; versiones y límites registrados |
| G-B suites | PASS | B-PY688/680 únicos; affected12+new1 y matriz previa no afectada con coverage completo |
| G-REL candidato local | PASS | Fuentes/imagen/versions/migrations y evidencia congeladas para revisión; **T12 no autorizado** |

La remediación cierra los cuatro failures originales: una expectativa inválida del harness y tres excesos reales de tiempo. No hay regresiones funcionales nuevas demostradas por los gates afectados. No se reabren T0–T10 ni la auditoría general.

## Release Candidate Manifest

Candidato **local de working tree**, HEAD checkpoint `32b85681907a8d7b7811a9e16ae1988941b3d3d1`, branch `main`. SHA256 del paquete de 380 fuentes **`fe9944b73f6a5b9f189d57477f1205fd73ca485ff9b92a7cf2fd272565e92138`**. Imagen local API/worker **`sha256:b26cfedb7e7a70927171801dd89b44429b568b719528328cc5b99e78cf781ddb`**; 327 archivos backend/assets comparados por hash. Las fuentes T11/T11-R siguen pendientes de commit; HEAD por sí solo NO contiene estos fixes. [Manifest de candidato](release-candidate-status-t11-r.json), [fuentes](evidence/remediation/source-frozen.json), [scope](evidence/remediation/scope-preservation.json), [diff T11-R exclusivo](evidence/remediation/application-remediation-only.patch), [patch completo de aplicación contra HEAD](evidence/remediation/application-candidate-vs-head.patch) y [fuentes del harness](evidence/remediation/harness-source-manifest.json).

Los 311 archivos del dossier original permanecen byte a byte iguales. [Índice de remediación](T11-R-index.md) incorpora este resultado sin borrar el STOP histórico. El manifest nuevo enumera la evidencia de esta remediación. Ninguna imagen se publicó, no hubo commit/push/deploy, ni cambios de infraestructura, credenciales, triggers o configuración productiva. El pipeline de producción no se disparó desde esta tarea.

**GO — T11 completado. T12 puede ser solicitado.**
