# Saga 10 — evidencia por gate

La saga no está terminada. Este registro se actualiza al completar gates; los flags de esquema/UI/optimización se crean OFF y no se han aplicado a producción.

| Gate | Estado actual | Evidencia |
|---|---|---|
| G0 | PASS | G0_BASELINE.md; 125 unit tests + Journey UX09 + benchmark |
| G1 | PASS focal | Dominio inmutable, SQL aditivo; seis escenarios de persistencia con último resultado PASS |
| G2 | PASS focal | 29 pruebas dominio + compatibilidad v1; ejemplos A/B y 100 propiedades con semilla |
| G3 | PASS focal | 67 unit tests, ocho escenarios de catálogo y 24 regresiones Journey v1 |
| G4 | PASS focal | 13 pruebas D1 v2 + oracle, 147 regresiones, SQL/worker y benchmark |
| G5 | PASS focal | Dos pruebas de handoff/artifacts + ciclo API/worker/aprobación/D2 |
| G6 | PENDIENTE | Wizard cinco bloques y navegador |
| G7 | PENDIENTE | Studio/exports compatibles |
| G8 | PENDIENTE | Matriz industria y regresión integrada |
| G9 | PENDIENTE | CI requerida, PR y plan de activación/rollback |

## G1

Archivos: `domain/logistics/cargo.py`, DTOs `models/ultimate_foundation.py`, servicio de modelos, migración `20261117234035_saga10_logistics_model_v2.sql`, fixtures/tests Saga10. El catálogo es parte del JSONB inmutable de cada publicación. IDs y referencias sólo resuelven dentro de ese snapshot; no hay FK a otro tenant ni catálogo mutable global.

La migración conserva el validador v1 y el cuerpo vigente de los RPC detrás de fachadas comprobadas. Agrega validación SQL de estructura/referencias y tres flags false. Publicar mantiene hashes/versiones/CAS; no cambia filas históricas. Reaplicación local probada. El downgrade implícito se rechaza. Se preservan RLS, grants y autorización por actor/workspace; anon/authenticated no acceden al release ni ejecutan los RPC. Schema OFF impide crear v2; optimization OFF bloquea admisión v2 también en SQL y cierra su disponibilidad reportada.

Pruebas: `tests.integration.test_saga10_persistence`. Primera tanda: 4/5 PASS; se corrigió la expectativa del test de downgrade al HTTP409 vigente y se comprobó borrador/revisión intactos. Segunda tanda con guard de optimización: 5/6 PASS; la nueva fixture omitía Decision Owner obligatorio. Se corrigió la fixture sin modificar ese contrato; T06 PASS en 13,256 s. T03 focal PASS en 13,687 s. Últimos resultados únicos de los seis escenarios: PASS.

CLI fijado 3.2.0, instalado sólo en caché temporal, `SUPABASE_HOME` temporal y telemetría desactivada. El archivo fue generado por `supabase migration new` (target local only). Documentación vigente de Database Migrations consultada con search_docs. El changelog web devolvió 403 desde este entorno; no se inventó una revisión de ese recurso. No se cambiaron APIs Supabase ni extensiones; la sintaxis PostgreSQL se verificó en el servidor 17 aislado.

## G2

`domain/logistics/physical.py`: Decimal, cm→m, t→kg, l→m³, producto por bulto, tara explícita, bruto declarado/derivado, volumen exterior cargado y densidad sólo explícita. Rechaza contradicciones, referencias desconocidas, duplicados, NaN/Infinity/floats, negativos y precisión inválida. El volumen del producto o de la unidad vacía no reemplaza el volumen exterior cargado.

Proveniencia y ROUND_HALF_UP quedan en el snapshot normalizado. Se deriva y declara un incremento de asignación representable en todas las dimensiones; no se redondea cada fracción perdiendo carga. Unidades discretas siempre enteras. Un límite estructural declarado exige peso bruto conocido; no implica certificación de geometría, temperatura, ejes o hazmat.

Comando: `DATION_EXECUTION_MODE=legacy python -m unittest -v tests.test_saga10_domain_physical tests.test_ultimate_case_models` desde backend — **29 PASS**, 0,104 s. Incluye 12 pruebas Saga10 con 100 propiedades de conservación/escalado/permutación, catálogo compartido y snapshots anteriores intactos. Ejemplos: 12 pallets = 13.140 kg / 27,24 m³; 20 pallets de jugo = 19.700 kg / 19.200 unidades / 43,2 m³.

Los gates PASS focales se revalidarán por las regresiones y la CI final. Ninguna declaración aquí equivale a un despliegue o habilitación productiva.


## G3

Nuevo compiler/normalizer v2, aislados del camino v1, con entidades dinámicas: v1/directo conserva transport_demand + transport_resources; catálogo agrega order_lines. Templates, campos, enums, condiciones, catálogo físico y preview provienen del mismo descriptor. Sin cuarto Products.csv ni overrides ambiguos. El paquete conceptual usa Orders/Fleet: se mantienen los nombres semánticos y headers reales del repositorio, incluida distance_km necesaria para costos/ciclos.

IDs de línea deterministas por publicación/orden/presentación. Se rechazan referencias desconocidas, pares semánticos duplicados, fracciones discretas y mezcla de cantidades directas/líneas. Lectura CSV incremental, hasta 10 MB y 10.000 filas; límite de admisión separado de 500 órdenes/500 líneas. Granel conserva su incremento físico representable.

SQL aditivo `20261117235546_saga10_catalog_data_contracts.sql` amplía checks de tipos/slots transaccionalmente y agrega un índice parcial sólo para líneas. Conserva el índice anterior y las reglas RLS/CAS/immutability. Los RPC preservados se extienden con anclas exactas y fallan si diverge el baseline; las fachadas restringen OrderLines a modelos catálogo v2 y mantienen esquema/optimización cerrados. Reaplicación local probada sin cambiar flags.

La validación de filas es distinta de la de relaciones: validate-bundle lee snapshots privados verificados y devuelve una prueba ligada a revisión/IDs/hashes; no escribe nada. Finalize vuelve a verificar antes de congelar/crear, y publication revalida antes de mover el Pack. Órdenes y líneas son atómicas; un Case vacío o sólo Flota sigue incompleto y permitido, con requisitos explícitos. Recuperación publica los tres archivos una sola vez. El frontend se conectará a este resultado en G6; el estado SQL VALIDATED por sí solo no autoriza una comprobación cruzada ficticia.

Comandos desde backend:
- `python -m unittest -v tests.test_saga10_domain_physical tests.test_saga10_data_contracts tests.test_ultimate_data_contracts tests.test_ultimate_case_models`: **67 PASS**, 0,667 s.
- `python -m unittest -v tests.integration.test_saga10_catalog_pack`: **8 PASS**, 21,190 s; incluye v1 sin tercer slot, snapshot incompatible, no creación ante huérfanas, publicación/recovery/idempotencia y flags cerrados.
- `python -m unittest -v tests.integration.test_decision_journey`: **24 PASS**, 30,141 s.

Se evitó revalidar el catálogo entero una vez por cada presentación: normalize_catalog valida una vez y normaliza sus presentaciones ya comprobadas. El wrapper público individual sigue validando que la presentación pertenezca al catálogo. La procedencia distingue valores declarados de fuentes derivadas. Sin efectos en v1.


## G4 y G5

Perfil exacto D1 `transport_plan/3.0.0 — transport_plan_cargo_v2`, registro público inactivo. CP-SAT asigna quanta enteros por línea/presentación, con suma primaria para la jerarquía de objetivos vigente; capacidades de todas las dimensiones, costos, guardrails, fechas y ciclos OWN conservados. Una orden indivisible lleva todas sus líneas completas a un Trip o ninguna. Consolidación y compatibilidad de co-carga son controles independientes. Los límites de 500 líneas, candidatos, variables y restricciones rechazan el exceso explícitamente; no se truncan candidatos para afirmar OPTIMAL. La precisión histórica de la fracción primaria puede excluir asignaciones diminutas: se informa `CARGO_FRACTION_DISPLAY_LIMIT` y se retira la certificación de óptimo completo. El detalle físico nunca se reconstruye de esa fracción.

Extensión opcional `cargo_assignment_v2` tipada: asignaciones, productos y resolución requested/assigned/unserved por línea, fijadas por hash de catálogo. None se omite: los bytes históricos y sus golden fingerprints siguen iguales. El certificador independiente no importa generador CP ni extracción; reconcilia física, líneas, enteros, conservación, co-carga y agregados. Las comparaciones económicas consideran las líneas realmente transportadas. La metadata estática JSON de contratos se regeneró para exponer la extensión aditiva, sin modificar el ABI anterior.

Admisión, hash, read-set y worker se atan al snapshot completo y al tercer slot; SQL conserva las identidades v1 y admite exactamente el perfil nuevo. El primer ciclo local detectó `ultimate_run_context` limitado a 2.0.0; el constraint aditivo mantiene todos sus controles y agrega la identidad 3.0.0 sólo para D1. La fachada conserva el contrato de worker sin actor mediante su lease; los flags v2 se vuelven a comprobar antes de producir/preparar. No hay cambios de leases, cancelación, replays ni activación productiva.

D2 conserva el certificado cargo exacto de D1 aprobado, Trip IDs, recursos y cantidades. El hash SQL de Core coincide con Python para la extensión. Se verificaron publicación real privada, aprobación humana, ausencia de modificación del padre y resultado D2.

Resultados:
- `tests.test_saga10_assignment` **13 PASS**, incluyendo nueve combinaciones de oracle exhaustivo independiente, todas las metas, ejemplos A/B, discrete/direct/bulk, capacidad de peso y mutantes re-firmados.
- Regresión `tests.test_transport_plan_core tests.test_transport_plan_policies tests.test_ultimate_contracts tests.test_day_scheduling_core` más las primeras once de Saga10: **147 PASS**, 4,036 s.
- `tests.test_saga10_assignment tests.test_saga10_scheduling tests.test_transport_result_package tests.test_day_result_package`: **53 PASS**, 3,081 s.
- `tests.integration.test_saga10_persistence tests.integration.test_saga10_catalog_pack`: **14 PASS**, 36,301 s con la migración G4 incluida.
- `tests.integration.test_saga10_execution`: **3 PASS**, 18,969 s, PostgreSQL/PostgREST/Storage y worker exclusivamente locales; sólo esa base efímera habilita los flags para comprobar ejecución.
- Benchmark local con tracemalloc: 1/10/100/250 órdenes/líneas, todas OPTIMAL, 0,0899/0,2358/2,6241/8,8894 s; 6/420/4.824/12.024 variables; RSS máximo acumulado 182.336 KiB. Referencia G0 no equivalente en física: 250 órdenes proporcionales, 6,8462 s/6.024 variables/140.784 KiB. El incremento corresponde a variables de integridad por línea y certificados; no se declara paridad exacta ni costo productivo medido.

La migración G4 fue generada con CLI y validada/reaplicada localmente. Ninguna migración se aplicó a Supabase real.
