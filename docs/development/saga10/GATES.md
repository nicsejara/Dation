# Saga 10 — evidencia por gate

La saga no está terminada. Este registro se actualiza al completar gates; los flags de esquema/UI/optimización se crean OFF y no se han aplicado a producción.

| Gate | Estado actual | Evidencia |
|---|---|---|
| G0 | PASS | G0_BASELINE.md; 125 unit tests + Journey UX09 + benchmark |
| G1 | PASS focal | Dominio inmutable, SQL aditivo; seis escenarios de persistencia con último resultado PASS |
| G2 | PASS focal | 29 pruebas dominio + compatibilidad v1; ejemplos A/B y 100 propiedades con semilla |
| G3 | PASS focal | 67 unit tests, ocho escenarios de catálogo y 24 regresiones Journey v1 |
| G4 | PASS focal | 16 pruebas D1 v2 + oracle, regresiones, SQL/worker y benchmark |
| G5 | PASS focal | Dos pruebas de handoff/artifacts + ciclo API/worker/aprobación/D2 |
| G6 | PASS focal | Cuatro E2E Saga10 + UX09; CPU lenta y navegador v1 |
| G7 | PASS focal | Detalle cargo, CSV por línea, linaje y Data Hub; 3 escenarios API/worker PASS |
| G8 | PASS focal; CI integral pendiente | 13 desafíos industriales, benchmarks y regresión transversal |
| G9 | PENDIENTE de CI/PR | Plan ROLLOUT y matriz ACCEPTANCE preparados; no merge/deploy |

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


## G6–G8 — implementación y evidencia intermedia

Cinco tarjetas nativas dentro de Core01, sin rutas nuevas. UI v2 opt-in con flag; los modelos publicados v1 mantienen su renderer/identidad. No se muestran controles de versión del wizard nuevo. Producto inicial sólo al elegir catálogo, unidades compartidas y CRUD de presentaciones simples/mixtas; controles referenciados bloquean eliminación, componentes y cantidades tienen validación real. Directo omite todo catálogo del payload. El compiler valida y muestra coeficientes/fuentes, sin fórmulas divergentes en JavaScript. Condicionales de fuentes/tarifas/km y perfil como sugerencia explícita.

Data Contract, preparación, resumen, lectura del Case y requisitos de Studio reconocen dos o tres entidades. La validación cruzada usa revisión/modelo/hashes normalizados públicos, no rutas privadas; toda respuesta obsoleta o mal ligada se rechaza. La primera prueba detectó que la proyección pública no exponía el hash canónico: se agregó sólo para catálogo. Otro ensayo detectó que el selector de Data Owner modificaba la revisión mientras Continuar podía seguir habilitado; se bloquea la transición durante ese guardado y se exige una nueva prueba de la revisión correcta. No se aumentaron esperas ni se agregaron retries/sleeps para ocultarlo.

G7 conserva datasets de resultados históricos y agrega un detalle `cargo` sólo en resultados catálogo. D1/D2 CSV usan `TRIP_ORDER_LINE`, cantidades y productos copiados del certificado; D1 reconoce costo Trip una sola vez. Etiquetas del snapshot también se certifican. Data Hub usa el mismo snapshot normalizado y mantiene el bloqueo de borrado de entradas referenciadas. El kernel temporal acepta el DTO categorizado completo; no pierde sus metadatos ni cambia los ciclos.

Resultados focales acumulados, sin sumar repeticiones como cobertura nueva:
- Última tanda amplia de motores/contratos: **167 PASS**, 6,059 s; luego dos guards adicionales de v1/multicategoría: `test_saga10_assignment` **15 PASS**, 1,871 s.
- `test_saga10_result_consumers` + industrias: **16 escenarios únicos** (una tanda anterior ejecutó además dos pruebas importadas redundantes; importación corregida).
- Casos industriales: doce sectores y negativo literal; limitaciones expresas para intradía/multistop/hazmat/temperatura/amarre.
- Integración SQL/API: **41 PASS**, 106,385 s — persistence6, catálogo8, ejecución3, Journey24. Incluye las cuatro migraciones.
- Sintaxis frontend: **135 módulos PASS**. Node: **27 archivos/suites PASS**, 3,919 s.
- Navegador: cuatro pruebas Saga10 con edición/cálculos/mixta, proof cruzado y modo directo; las últimas únicas fueron PASS antes de la ampliación transversal. La ampliación halló la carrera del guardado de owner, corregida como se describe arriba; su verificación bajo CPU lenta y la regresión UX09/UX06/v1 se registran al finalizar. Un arranque de fixture histórico quedó en bootstrap sin error JS; se investiga focalmente con traza, sin atribuir causa no demostrada.

No se habilitaron flags ni motores reales. La CI completa se reserva para el candidato estable; los resultados terminales se enlazarán desde el PR.


## Cierre focal del candidato (antes de la CI requerida)

- `tests.test_saga10_assignment`: **16 PASS**, 1,299 s; incluye CUSTOM, guardrails, prioridad, v1/DTO v2 y categorías directas.
- `test_saga10_wizard` + UX09 T01: **5 PASS**, 64,047 s. Capturas reales de ocho escenas escritorio/móvil y cuatro archivos de geometría en `evidence/`; todos los controles sin overflow en cinco anchos, contraste comprobado por `theme_audit.js`.
- Journey catálogo T02 repetido **3/3 PASS bajo CPU4× lenta**, 57,378 s. El test ahora comprueba delta de Cases y versión exacta, permitiendo repetirlo sin asumir una base vacía ni debilitar el control de creación única.
- Prueba de proof cruzado T04 **PASS**, 18,630 s: respuesta vieja después de nueva revisión y respuesta200 con hash incorrecto no habilitan un estado inválido. Se corrigió el harness para esperar la entrega de la respuesta interceptada antes de quitar el route; sin sleeps.
- Logistics Model v1 T01 focal **PASS**, 23,242 s, con traza de red sin errores HTTP ni JS. El timeout de bootstrap de una tanda previa no se reprodujo; no se modificó Auth ni se atribuyó una causa sin evidencia. UX06 T12 y UX09 T01 también tuvieron último resultado PASS en la regresión transversal. FULL CI será la validación final sobre el SHA del PR.
- Compilación Python, sintaxis JS/Node y `git diff --check` PASS. `zero_idle_release.py validate` PASS, `mutation_performed=false`; no apply ni comandos cloud.
- Benchmark final reproducible: `DATION_EXECUTION_MODE=legacy PYTHONPATH=backend python -m tests.benchmarks.saga10`. Python3.13.5 / OR-Tools9.15.6755; source digest de todos los archivos Python de backend en `g8-benchmark.json`. Para1/10/100/250 órdenes y líneas: OPTIMAL en0,1043/0,2266/2,4834/8,4629 s; límites vacíos, objetivo y best_bound coinciden; RSS pico acumulado185.612KiB. Comparación G0 y presupuestos en G4. No es un benchmark productivo ni un SLA.

G9 técnico: matriz de40 criterios, diccionario, decisiones, restricciones y procedimiento manual/rollback preparados. El PR y sus checks terminales se deben revisar externamente en GitHub; este archivo no declara una CI verde antes de su ejecución. No habrá merge ni despliegue como parte del cierre.


Revisión final de errores físicos: el handler existente ya entrega errores sanitizados en `errors[{field,message}]`, además de su resumen genérico. El preview v2 ahora presenta esos mensajes de negocio dentro del bloque de carga, conserva el fallback y no cambia el handler ni los mensajes v1. Una prueba real introduce peso bruto500kg contra componentes+tara985kg: publicación bloqueada, causa «contradice» visible como alert, corrección recupera preview y publicación. **T01 ampliado PASS**, 24,595 s. Capturas actualizadas. Se conserva el source digest de backend del benchmark porque este ajuste sólo cambia presentación y prueba de navegador.

El primer candidato f5a68b36 obtuvo impact/FAST success; al agregar esta verificación y corregir la presentación, su FULL deja de ser válido para el HEAD nuevo. Se detiene la ejecución obsoleta si sigue activa y se exige un único run completo del candidato definitivo; no se usa el resultado anterior como aprobación.
