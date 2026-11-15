# UX04 — G2–G6, aceptación y evidencia

Pruebas exclusivamente en sandbox sintético local: FastAPI real, PostgreSQL17/PostgREST, Storage privado simulado, Chromium. El ciclo D1/D2 usa los motores reales existentes con un worker local temporal que termina con la fixture. No certifica producción ni despliegue.

## Gates implementados

- **G0:** #118 mergeado; baseline y 23 regresiones iniciales PASS; estrategia en [DESIGN](DESIGN.md).
- **G1:** staging privado por actor/workspace/version, CAS, TTL/cotas, cleanup y finalización recuperable; migración aditiva OFF. 24 tests de integración PASS.
- **G2:** contratos UX02 + tarjetas de CSV/errores/advertencias/preview/candidatos; Data Owner provisional; continuar con dos datos o sin datos; candidatos guardados recuperables y selección de preparación propia.
- **G3:** creación y publicación canónicas idempotentes, intención durable, mismo Case ante falla o respuesta perdida; consulta del Graph antes de navegar.
- **G4:** una barra global de cuatro niveles y un rail interno de tres pasos por contexto (Core o Studio), sin segunda barra horizontal ni «Paso X de 6». Core sin accordions principales; internos conservados. Studio Graph/Configuration/Dashboard; retornos serializados y validados.
- **G5:** derivación sin mutar original, linaje persistente, edición administrativa contextual, aprobación confirmada/lost-response→Graph y cierre explícito bajo CAS/auditoría. Archivado anterior conserva su semántica.
- **G6:** 15 E2E nuevos únicos (incluyen respuesta tardía, archivos locales sin guardar y composición de navegación con restauración histórica), 51 regresiones UX01/02/03/setup/navegación, Node de rutas y estáticos. FAST/FULL/required-gate se registran en el PR con su resultado terminal y SHA; no se crean commits sólo para actualizar tiempos de CI.
- **G7:** PR abierto/revisión y [activación MANUAL](ACTIVATION.md); ninguna operación productiva realizada.

## Matriz AC-01–34

`Bxx`: test de integración `tests.integration.test_decision_journey.DecisionJourneyTests.test_xx…`.
`Wxx`: E2E `test_unified_decision_journey.UnifiedDecisionJourneyTests.test_xx…`, salvo W08 que pertenece a JourneyEngineTests. Los nombres/afirmaciones exactas están en esos archivos. `Reg`: suite focal de 51 regresiones. Los escenarios de backend histórico se vuelven a ejecutar en FULL requerido.

| AC | Local | Evidencia / alcance |
| --- | --- | --- |
| 01 Comenzar | PASS | W01/02: Core nuevo paso01; Reg/Saga Planning en FULL conserva entrada canónica, sin Case oculto |
| 02 Modelo nuevo | PASS | Reg Logistics Model12 + W01 contratos/version real seleccionada; publicación canónica intacta |
| 03 Modelo reutilizado | PASS | W01/03/11, B01: versión exacta ligada al stage, readonly vinculada al Case |
| 04 Templates | PASS | Reg Data Contract10 + W01/12: descargas reales; compilador/headers sin cambios |
| 05 CSV faltante | PASS | W02/14, B05: continuar vacío → DATA_REQUIRED y Core02 del mismo Case |
| 06 CSV inválido | PASS | W06, B02/13: detalle real, sin candidato/bytes válidos ni Case residual |
| 07 Advertencias | PASS | W12: UNKNOWN_COST real, detalle, candidato guardado sin publicación |
| 08 Dos CSV válidos | PASS | W01, B01/04: stage privado de ambas entidades sin crear Case anticipado |
| 09 Refresh/logout/aislamiento | PASS | W01/09: refresh y reanudación; B03: otro actor/workspace/viewer no obtiene stage; drafts existentes se aíslan por identidad, auth/logout en FULL |
| 10 Cambio de Model | PASS | W11/13 + B01/09/21; versiones y hashes canónicos comprobados; nueva preparación no mezcla contratos; generación invalida respuestas anteriores |
| 11 Data Owner | PASS | W01: intención elegible + asignación efectiva; B04/17: permiso/elegibilidad revalidados |
| 12 Finalizar Core03 | PASS | W01/14, B04/05: Case/Pack/Graph reales, sin autoejecución |
| 13 Falla después de Case | PASS | W09, B06/13: FINALIZING durable, mismo Case, recuperación explícita |
| 14 Respuesta perdida | PASS | B07/14: publicación UUID estable y una única versión; W09 recarga y recuperación |
| 15 D1 sin datos | PASS | W02 → Core02, conserva case_id, no ingesta en Graph |
| 16 Actualizar sin Run | PASS | W02 extendido: publica v2 desde Core02, conserva Case e historial; B18 conserva API histórica |
| 17 Origen con Run | PASS | W03, B18: modal y guard de publicación contra admisión concurrente; error/superseded cuentan como Run |
| 18 Cancelar derivación | PASS | W03: modal cancelado, URL/original inmutados; cancelar draft posterior conserva explícitamente borrador |
| 19 Confirmar derivación | PASS | W03, B10: stage nuevo → Case nuevo con parent_case_id; sin runs/aprobaciones copiados |
| 20 Nombre tras aprobar D1 | PASS | W04 + W08: PATCH administrativo y origen exacto Dashboard tras reload; aprobación original se conserva |
| 21 Horizonte congelado | PASS | W04/11, Reg UX03: controles deshabilitados y acción de derivar; no PATCH matemático |
| 22 Ejecutar D1 | PASS | W08: UI Config → admisión real/worker local → corrida y Dashboard exactos |
| 23 Aprobar D1 | PASS | W08: respuesta de aprobación confirmada perdida, reconciliación por GET → Graph, sin re-POST ni D2 automática |
| 24 Aprobar D2 | PASS | W08: fuente D1 vigente, aprobación real → Graph → cierre |
| 25 D2 NOT_APPLICABLE | PASS | W05 + B12: metadata de escenario explícita, Graph autoritativo; cierre no exige aprobación imposible |
| 26 Cierre elegible | PASS | W05/08 + B12/19: estado revalidado en servidor bajo lock/CAS, evento auditable y Center |
| 27 Cierre bloqueado | PASS | W07 + B11/22: incompleto o candidato pendiente no archiva ni inventa aprobación |
| 28 Cases A/B | PASS | W03/B10: original activo con aprobación intacta después de crear derivado; Reg Center/navegación conserva acceso a Cases independientes |
| 29 Deep links | PASS | W04/08/11 + Node rutas + Reg navegación10: case/node/run y retorno canónico; URLs externas/IDs inválidos rechazados |
| 30 Roles | PASS | B03/17 + Reg UX03 permisos05–08/navegación05: viewer/operator/Admin, ACL servidor y elegibilidad |
| 31 Concurrencia | PASS | B09/14/18/19: CAS, doble finalize, sin doble Case/Pack y recheck de Run/cierre |
| 32 Responsive/foco | PASS | W06/07/08: cinco anchos, controles nativos/drop por teclado, modal con foco; sin overflow tras layout estable |
| 33 Histórico backend | PASS local / FULL requerido | B18 + Reg; FULL ejecuta suites existentes STALE, publicación, snapshots, lineage, Center, SQL y E2E sin alterarlas |
| 34 Scale-to-zero | PASS código | Sin recursos, procesos o jobs nuevos productivos; límites, cleanup bajo demanda y costo residual documentados |

## Capturas reales

Las dos imágenes del paquete son referencias estéticas; el documento manda sobre UX02 antiguo. Se conservan el shell real, los tokens y los patrones de UX01–03. Core02 combina ahora contratos con preparación; su altura aumenta por contenido real. No se generan CSV ni estados a partir del mockup.

| Estado | Archivo |
| --- | --- |
| Core01 | [Desktop](evidence/core01-1536.png) · [Tablet](evidence/core01-1024.png) · [Móvil](evidence/core01-390.png) |
| Core02 vacío | [Desktop](evidence/core02-empty-1536.png) |
| Core02 dos candidatos | [Desktop](evidence/core02-valid-1536.png) · [Tablet](evidence/core02-valid-1024.png) · [Móvil](evidence/core02-valid-390.png) |
| Core02 advertencia real | [Desktop](evidence/core02-warning-1536.png) |
| Core03 | [Desktop](evidence/core03-1536.png) · [Tablet](evidence/core03-1024.png) · [Móvil](evidence/core03-390.png) |
| Graph | [Desktop](evidence/studio-graph-1536.png) · [Tablet](evidence/studio-graph-1024.png) · [Móvil](evidence/studio-graph-390.png) |
| Config D1 | [Desktop](evidence/logistics_assignment-configuration-1536.png) · [Tablet](evidence/logistics_assignment-configuration-1024.png) · [Móvil](evidence/logistics_assignment-configuration-390.png) |
| Config D2 | [Desktop](evidence/logistics_scheduling-configuration-1536.png) · [Tablet](evidence/logistics_scheduling-configuration-1024.png) · [Móvil](evidence/logistics_scheduling-configuration-390.png) |
| Dashboard D1 | [Desktop](evidence/logistics_assignment-dashboard-1536.png) · [Tablet](evidence/logistics_assignment-dashboard-1024.png) · [Móvil](evidence/logistics_assignment-dashboard-390.png) |
| Dashboard D2 | [Desktop](evidence/logistics_scheduling-dashboard-1536.png) · [Tablet](evidence/logistics_scheduling-dashboard-1024.png) · [Móvil](evidence/logistics_scheduling-dashboard-390.png) |
| Cierre habilitado | [Desktop](evidence/studio-closure-ready-1536.png) |
| Derivación | [Core02](evidence/derivation.png) |

No se retocan screenshots. Se capturan desde scroll0, con fuentes/estilos del producto. El viewport se sincroniza con dos requestAnimationFrame antes de medir layout: el diagnóstico inicial midió el contenedor aún con el ancho previo (x264/94px a 390); tras el render estable x76 y ancho correcto, sin cambio de assertion, clipping ni espera temporal arbitraria. [Mediciones Core](evidence/responsive.json) · [Studio390](evidence/studio-overflow.json).

## Límites de la evidencia

Storage es un servidor privado de contrato del sandbox, no Supabase productivo. Algunos escenarios de congelamiento/NOT_APPLICABLE usan fixtures explícitas de metadata; W08 ejecuta y aprueba D1/D2 reales de principio a fin localmente. Los tests de roles modifican sólo identidades sintéticas y las restauran. Las pruebas no prueban IAM real, cuota de Storage del proyecto ni activación del schema; eso pertenece al GO manual.

FULL y flags OFF son obligatorios antes de revisión final. El resultado de CI, SHA y duración final se publican en la descripción del único PR. No se declara PROD_READY.

## Control final de CSV local sin guardar

W14 reprodujo un defecto antes de integrar: saltar por el rail a Core03 con un CSV sólo local permitía crear el Case antes de resolver la selección. La validación compartida ahora bloquea ese submit antes de congelar la intención; conserva archivo y campos y recupera el progreso al guardar. W14 PASS (18,271 s), con flujos normal y sin datos también PASS en la tanda focal de tres. La CI del candidato anterior se canceló para evitar completar FULL sobre un SHA sustituido; el nuevo candidato requiere nuevamente su gate FAST/FULL completo. No se debilitaron assertions.

## Corrección focal de expectativa histórica de E2E

La ejecución FULL [43658139128](https://github.com/nicsejara/Dation/actions/runs/43658139128) aprobó Python, Node, los 344 tests de navegador, Docker y los 192 tests SQL. El último recorrido E2E falló en dos casos (`test_workflow` desktop/mobile), ambos en la misma comparación exacta de los títulos de Core. El test esperaba `01 Logistics Model`/`02 Data Contract`/`03 Decision Case`, mientras que el main inicial ya genera `01. Logistics Model`/`02. Data Contract`/`03. Decision Case`.

Se reprodujeron los dos fallos en un checkout aislado de `4b66044806f93535a363ad8829c8eb003644958e`: misma línea 75, mismos dos fallos, sin errores de infraestructura. Es una expectativa obsoleta preexistente, no una regresión de UX04. Se actualizan sólo los tres textos esperados, conservando igualdad exacta, paneles, visibilidad, creación/ejecución/aprobación/navegación y los controles de seguridad del recorrido completo. Ambos E2E PASS (87,161 s) sobre la rama corregida. [Recibo focal baseline/corrección](evidence/workflow-labels.json). El producto no cambia con esta corrección; el nuevo SHA debe obtener FAST/FULL/required-gate terminales antes de cerrar la entrega.

## Ajuste visual de navegación sobre el candidato 4287d868

Por instrucción del propietario, se retira únicamente el renderer horizontal de seis pasos, su estado «Paso X de 6» y sus estilos exclusivos. `renderCaseFlow` oculta completamente `#dda-workspace-nav-shell` en Unified Journey, vacía sus hijos y limpia el cache; el renderer histórico de cuatro pasos mantiene destinos, permisos y bloqueos cuando Unified Journey está OFF. La actualización de contexto vuelve a sincronizar ese contenedor después de resolver el flag en una entrada directa a Studio, evitando una franja vacía. La barra global y los rails internos no cambian sus componentes ni reglas.

W15 reproduce el defecto antes del ajuste y exige después: cuatro niveles globales con su estado activo exacto; tres pasos internos con estado activo correcto; ausencia de botones, texto, separadores y caja residual de la barra eliminada; restauración histórica sobre el mismo DOM, repetida dos veces; entrada directa y recarga de Graph. W07/W08 verifican también Core, Config y Dashboard en 1536/1024/768/390/320 px, sin overflow y con idénticos estados y permisos al cambiar de ancho. Todas las capturas comprueban esa composición antes de guardarse. [Mediciones de navegación](evidence/navigation-layout.json) · [Resultado focal](evidence/navigation-focal.txt).

Alcance exclusivo de presentación: sin cambios a Data Preparation, contratos de Case/Graph, configuración, resultados, backend, API, motores, persistencia o migración SQL. El delta visual corresponde a R2; el PR acumulado conserva R3 y sus gates FAST/FULL obligatorios, sin modificar el clasificador. No merge ni operación productiva.

Validación local del ajuste: 25 escenarios únicos cubiertos (15 Journey y 10 navegación histórica). La tanda combinada tuvo 24 PASS y un timeout W08 de respuesta perdida; el diagnóstico focal confirmó HTTP200 de aprobación y D1 APPROVED/CURRENT en el servidor, sin atribuir una causa al timeout ni cambiar el producto. Después del último timeout, W08 pasó tres veces consecutivas (30,930 s y dos casos en 46,601 s), conservando assertions y espera de navegación de 30 s. W07/W15 finales PASS (28,715 s), cinco archivos Node PASS. Las capturas de Config comienzan explícitamente en 1536 px para que el nombre del archivo coincida con el viewport real. La CI del SHA definitivo sigue siendo obligatoria; el resultado terminal se registra en el PR.
