# Saga 10 — evidencia por gate

La saga no está terminada. Este registro se actualiza al completar gates; los flags de esquema/UI/optimización se crean OFF y no se han aplicado a producción.

| Gate | Estado actual | Evidencia |
|---|---|---|
| G0 | PASS | G0_BASELINE.md; 125 unit tests + Journey UX09 + benchmark |
| G1 | PASS focal | Dominio inmutable, SQL aditivo; seis escenarios de persistencia con último resultado PASS |
| G2 | PASS focal | 29 pruebas dominio + compatibilidad v1; ejemplos A/B y 100 propiedades con semilla |
| G3 | PASS focal | 67 unit tests, ocho escenarios de catálogo y 24 regresiones Journey v1 |
| G4 | PENDIENTE | Adaptación D1 por líneas + oracle/benchmark |
| G5 | PENDIENTE | Handoff D1→D2 inmutable |
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
