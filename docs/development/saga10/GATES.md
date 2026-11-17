# Saga 10 — evidencia por gate

La saga no está terminada. Este registro se actualiza al completar gates; los flags de esquema/UI/optimización se crean OFF y no se han aplicado a producción.

| Gate | Estado actual | Evidencia |
|---|---|---|
| G0 | PASS | G0_BASELINE.md; 125 unit tests + Journey UX09 + benchmark |
| G1 | PASS focal | Dominio inmutable, SQL aditivo; seis escenarios de persistencia con último resultado PASS |
| G2 | PASS focal | 29 pruebas dominio + compatibilidad v1; ejemplos A/B y 100 propiedades con semilla |
| G3 | PENDIENTE | Compiler, CSV y publicación cruzada |
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
