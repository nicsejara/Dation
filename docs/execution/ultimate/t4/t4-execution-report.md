# T4 — Dynamic Data Contracts + Progressive Data Pack

Fecha: 26 de octubre de 2026. Alcance autorizado: exclusivamente T4. Fuente normativa: [Master Execution Plan](../../../../DATION_FINAL_MASTER_EXECUTION_PLAN.md), §3/F01–F23, §3.1, T4, §22 y §23; [orden del usuario](evidence/T4-user-request.txt). Baseline inmediato: [T3 aprobado](../t3/t3-execution-report.md).

T4 incorpora contratos dinámicos de demanda y recursos, templates exactos, validación y normalización reproducibles, candidatos recuperables y publicación explícita de manifests completos e inmutables. Case Data permite administrar ese flujo con los componentes nativos de Dation. La ejecución Ultimate continúa cerrada; publicar inputs no establece una Decision READY.

## Baseline

- Branch: `main`. HEAD al inicio y al cierre: `ef997235a30251fbf7ae53690ed738092ee973d8`. La referencia local de `origin/main` tiene ese mismo HEAD; no se hizo fetch ni se afirma una verificación remota nueva en T4.
- El workspace ya tenía cambios T0–T3 sin commit. Antes de T4 se registraron y copiaron **507 archivos pendientes**, 23.665.979 bytes, y se comprobaron las **144 entradas** del manifest histórico de T3. No se reseteó ni limpió ese trabajo.
- **500 archivos iniciales siguen idénticos**; siete se extendieron para conectar Case Data. Sus preimágenes post-T3 están preservadas en `evidence/post-t3/`. El manifest y los reportes T3 no se reescribieron: sus hashes se resuelven contra las preimágenes cuando corresponde.
- El diff propio T4 comprende **25 archivos de código, migración y tests: 14 nuevos y 11 modificados**, además de este reporte y su evidencia. Comparación contra el checkpoint post-T3, usando HEAD sólo para archivos previamente limpios.
- Sin cambios de engines, Results, approvals, Runs, context/ownership del Case o navegación legacy. Sin infraestructura, configuración productiva, migración remota, commit, staging, push ni deploy. No se inició T5.

Evidencia: [estado inicial](evidence/initial-state.json), [preservación](preservation.json), [scope diff y hashes](scope-diff.json), [patch T4](evidence/t4-changes.patch), [integridad final](artifact-integrity.json).

## Skills utilizadas

La precedencia aplicada fue arquitectura aprobada → comportamiento existente → componentes/tokens de Dation → recomendaciones de Skills. El [ledger](skills-ledger.json) distingue lectura, aplicación y verificación, y preserva fuentes y SHA256.

| Skill | Aplicación acotada | Verificación |
|---|---|---|
| `supabase:supabase` | RPC comprobado por actor/tenant, Storage privado, objetos sin upsert y flag cerrado; consulta de documentación oficial de Storage | S4, errores inyectados y catálogo/ACL/RLS |
| `supabase:supabase-postgres-best-practices` | Locks workspace → Case, CAS, constraints/FKs, manifest transaccional y journals | Concurrencia, retries, separación de tenants y protección de consumidores |
| `cloud-environment:cloud-environment-runtime` | Estado/política del entorno, Docker local owned y runners sin credenciales productivas | Versiones registradas y cleanup por labels |
| `design-system` | Composición de cards/dropzone/dialog/drawer existentes y tokens semánticos; guía de estados | Paridad de primitivas y screenshots de la superficie afectada |
| `emil-design-eng` | Feedback, foco, Escape, retorno de foco y reduced motion | W4 y tabla Before/After/Why siguiente |
| `ui-ux-pro-max` | Guía focal de formularios/accesibilidad ya leída en T3, aplicada a errores y headers exactos | W4, contraste y responsive |
| `break-ui` | Fixtures con filename permitido de 120 caracteres, Unicode, vacío/uno/múltiples, 320 px y zoom 200% | W4; sin toggles ni datos comerciales reales |

Las Skills Supabase/Postgres/runtime y la guía principal/estados de design-system se leyeron durante T4. Se reutilizaron lecturas pertinentes de esta misma conversación para las otras guías/referencias, como identifica el ledger. No se ejecutaron generadores de paleta, tipografía, design system o framework; tampoco una auditoría de motion o transversal. No se agregaron dependencias de aplicación. La autorización explícita de implementación T4 permite corregir sus findings acotados sin una nueva pausa de aprobación sugerida por break-ui.

## Files Created

| Archivo | Responsabilidad |
|---|---|
| `backend/app/domain/logistics/data_contracts.py` | Descriptor tipado, compiler y templates derivados |
| `backend/app/domain/logistics/normalizers.py` | Parser exacto, normalización, hashes y provenance |
| `backend/app/models/ultimate_data_pack.py` | DTOs de selección/publicación sin autoridad del cliente |
| `backend/app/platform/ultimate_data_routes.py` | API Case Data, templates, validación, candidatos, reuse y publicación |
| `backend/app/services/case_data_pack_service.py` | Orquestación SQL/Storage, verificación de bytes y recovery |
| `backend/app/static/css/ultimate-case-data.css` | Layout y preview exclusivamente bajo `.ultimate-case-data` |
| `backend/app/static/js/dispatch/upload/ultimate-case-data.mjs` | Case Data con uploader y controles nativos |
| `supabase/migrations/20261026184655_ultimate_progressive_data_pack.sql` | Flag, journals, metadata normalizada, RPC y guards aditivos |
| `backend/tests/test_ultimate_data_contracts.py` | U4, escenarios O/P/Q/R y determinismo |
| `backend/tests/test_ultimate_data_navigation.mjs` | Resolución contextual de la nueva superficie |
| `backend/tests/integration/test_ultimate_data_pack.py` | S4, API/SQL/Storage, concurrencia y recovery |
| `backend/tests/browser/test_ultimate_case_data.py` | W4, flujos y preservación visual/a11y |
| `backend/tests/e2e/ultimate_data_fixture.py` | Harness local de API/SQL/identidad y fault injection |
| `backend/tests/e2e/ultimate_storage_gateway.py` | Fixture privado del contrato HTTP de Storage |

## Files Modified

| Archivo | Cambio T4 |
|---|---|
| `backend/app/platform/data_hub.py` | Preview normalizado para los nuevos tipos; presentación compatible con la tabla del Hub |
| `backend/app/platform/data_routes.py` | Archive/unarchive de la cohorte nueva mediante RPC comprobado |
| `backend/app/platform/identity.py` | Proyección del flag y permiso de lectura de nuevos datasets |
| `backend/app/platform/routes.py` | Registro del router T4 |
| `backend/app/static/js/dispatch/cases/ultimate-case-setup.mjs` | Entrada contextual a Datos del Case |
| `backend/app/static/js/dispatch/navigation/resource.mjs` | Recurso `logistics-case-data` conservando Case ID |
| `backend/app/static/js/dispatch/workspace.mjs` | Mount/lifecycle de la nueva vista |
| `backend/app/static/js/platform/data-hub.mjs` | Archive de los dos tipos nuevos |
| `backend/app/static/js/platform/data-presentation.mjs` | Labels de demanda/recursos Ultimate |
| `backend/app/static/js/platform/dda-navigation.mjs` | Ruta `/app/ddas/logistics/case/data?case_id=…` |
| `backend/app/templates/app.html` | Root de la nueva vista |

El manifest identifica la preimagen exacta de cada modificación. Los CSS globales que aparecen pendientes en Git pertenecen al baseline previo; T4 no los altera. Tampoco cambia Hero, imágenes, fuentes, icon family, tokens ni navegación funcional D1/D2.

## Contract Compiler

`compile_contract(model_version, semantic_entity, registry_version)` usa la Model Version publicada recuperada por SQL y validada con el DTO de configuración T3. Entidades admitidas: `transport_demand` y `transport_resources`. Registry: `ULTIMATE_DOMAIN_V1`. Normalizer: `DATION_INPUT_NORMALIZER_V1`. Entidad/registry/normalizer desconocidos fallan de forma explícita.

El descriptor inmutable declara `contract_id`, `schema_version`, `registry_version`, `model_version_id`, `configuration_hash`, campos, tipos, unidades, `required_for`, `used_by`, reglas, `engine_role`, `public_header`, ejemplos, nulabilidad, condicionalidad, normalizer y hash. La serialización canónica incluye la identidad de Model Version y su configuración; no deriva significado de labels, nombres de archivos ni headers parecidos.

| Entidad | Campos según Model |
|---|---|
| Demanda | `order_id`, `origin_id`, `destination_id`, distancia, ready/due ISO, prioridad, split y cantidades de dimensiones activas; compatibilidad explícita salvo cargas homogéneas declaradas |
| Recursos comunes | ID, fuente, lanes como pares origen/destino JSON, capacidades garantizadas y máximas de dimensiones activas, compatibilidad |
| OWN | Unidades disponibles, base de origen y costo operativo por km; no exige oferta/tarifa EXTERNAL |
| EXTERNAL | Servicios finitos por horizonte y fuente de disponibilidad; PER_TRIP/PER_KM y ONE_WAY/ROUND_TRIP según Model; no exige base/unidades/costo OWN |

PALLETS_ONLY no declara columnas de kg. El compiler de campos y sus condiciones es la fuente del template, parser y normalizer; queda disponible para que readiness/admission futuras consuman el mismo descriptor. No se implementan esos resolvers ni se duplican columnas de schema en frontend.

## Templates

Descarga dinámica CSV UTF-8 con cinco ejemplos operativos generados exclusivamente desde el descriptor. Los headers de su template deben estar presentes y coincidir exactamente; la nulabilidad o no aplicabilidad habilita **celdas vacías**, no aliases ni eliminación de headers. El orden de columnas no cambia su significado. Separador coma, fechas `YYYY-MM-DD`, booleanos `true`/`false`, enums exactos, decimales sin inferencia de locale. Se admite BOM UTF-8; los valores se normalizan por trim y NFC declarados.

Los ejemplos revisables [demanda](evidence/samples/transport_demand.csv), [recursos](evidence/samples/transport_resources.csv) y [descriptor](evidence/samples/transport_resources-contract.json) provienen de una fixture sintética con forma de Version publicada; no de datos productivos. [source.json](evidence/samples/source.json) identifica su origen y funciones. Las URLs/templates Orders/Fleet legacy permanecen vigentes.

## Validation

La validación vuelve a compilar el contrato del Case y comprueba el hash presentado por el cliente. Rechaza columnas faltantes, extras, repetidas o fuzzy; CSV vacío/malformado/UTF-8 inválido; IDs duplicados; tipos, enums, fechas o intervalos inválidos; fuentes/cost models/billing no habilitados; campos de otra fuente con contenido; capacidad física no positiva; garantía mayor que máximo; escalas inválidas y splits/compatibilidad incompatibles con el Model.

No exige nombres de clientes, CUIT, SKU, descripción comercial, factura, revenue o margin. Extras como esos producen error antes del journal/Storage; los errores no reproducen los valores comerciales rechazados. No se aplica una conversión Orders/Fleet → Ultimate. La pseudonimización de los identificadores operativos sigue siendo responsabilidad del aportante: el parser valida el contrato, no certifica por contenido que un identificador carezca de PII.

Los reportes separan errores, advertencias, resumen y preview. Se muestran como máximo diez filas de preview y cien errores/advertencias; el resumen de assumptions incluye hasta veinte detalles y declara su total/truncamiento. El snapshot privado conserva la provenance completa. No se envían CSVs al LLM ni se invoca un solver para validar.

## Normalization

El normalizer produce DTOs T1 `Demand` / `TransportResource`, orden estable de IDs/lanes/grupos y bytes JSON canónicos. Conserva unidades y precisión T1; no calcula decisiones, costos finales ni fechas de engine. Cada input registra raw SHA256, canonical SHA256, contrato/hash, normalizer, entidad, Model Version y provenance. Cambios de orden/formato equivalentes pueden cambiar raw hash y conservar canonical hash bajo el mismo contrato; otra Model Version tiene una interpretación/hash distinta.

| Entrada | Representación preservada |
|---|---|
| Disponibilidad `0` | Cero válido; no unknown |
| `UNKNOWN` y servicios vacíos | `null` y fuente UNKNOWN; no ilimitado ni confirmado |
| `CONFIRMED` y servicios vacíos | Error |
| `ASSUMED` explícito y servicios vacíos | Un servicio, assumption congelada con fuente `DATION_DEFAULT` y advertencia |
| `ASSUMED` y cantidad explícita | Cantidad asumida preservada, provenance `DERIVED`; no confirmada |
| Costo desconocido | `null` y advertencia; no cero inventado |
| Tarifa explícita `0` | Cero conocido, distinto de unknown |

El envelope privado contiene Model/contract/normalizer/moneda, records y assumptions. Sus agregados estructurados dejan preparada la construcción futura de InputSummary sin raw CSV. T4 no fabrica un InputSummary de decisión, FrozenInputRefs de una Run inexistente ni evidencia IA.

## Progressive Pack

Se reutilizan Pack/Versions/Entries T2/T3. El Case conserva su Pack estable y versión inicial vacía. Guardar un candidato READY no modifica la versión actual. La publicación explícita crea una nueva versión con **manifest completo**, incluyendo los slots previos: vacío → demanda → demanda + recursos. Cambiar un slot no elimina los restantes ni reescribe versiones consumidas.

La selección tipada acepta referencias a upload/dataset, UUID de intención y revisión esperada; el browser no aporta schemas, actors, workspace, paths o manifests con autoridad. El backend arma el manifest y SQL lo reconstruye/compara bajo locks workspace → Case y CAS. Version/entries/journal/pointer se guardan en una transacción, con hash de manifest y contract set. El UUID de versión deriva determinísticamente de la intención de publicación.

Las publicaciones persistidas guardan versión previa/nueva, entidad y raw/canonical/contract hashes anteriores/nuevos por slot. Esa provenance permitirá invalidación posterior. T4 no modifica approvals, Runs, resultados, upstream ni calcula la closure downstream del Graph.

La publicación vuelve a verificar bytes privados raw y normalizados de **todas** las entradas antes de mover el pointer. Metadata y snapshots no pueden actualizarse o borrarse por la API/RPC; la protección de consumidores del Hub incorpora los objetos normalizados. La garantía cubre el flujo de aplicación y los errores probados; no presupone que un administrador externo de Storage sea incapaz de borrar objetos fuera de ese flujo.

## Storage / Recovery

Migración aditiva `20261026184655_ultimate_progressive_data_pack.sql`, ensayada sólo en sandbox PostgreSQL local owned. Agrega el flag `ultimate_data_pack_enabled=false`, tablas privadas `ultimate_input_uploads`, `ultimate_input_objects` y `ultimate_pack_publications`, constraints/índices/triggers y RPC `platform_ultimate_data_pack`. Las tablas nuevas fuerzan RLS y revocan grants directos; el RPC SECURITY DEFINER fija `search_path=pg_catalog`, exige service role y revalida tenant/membership/DDA/rol. Las escrituras también requieren el flag foundation T3.

El catálogo previo conserva ACL de relaciones/funciones/defaults y políticas RLS. Las únicas definiciones existentes extendidas son `dation_private.dataset_referenced` para el nuevo consumidor y `public.platform_data_hub` para permisos archive de nuevos tipos. Cinco filas sintéticas previas de datasets/Case/Run/approval permanecieron idénticas al aplicar la migración. [Evidencia de frontera](evidence/schema-boundary.json).

Pipeline: validar → preparar journal → subir raw privado → crear/verificar JSON normalizado → metadata comprobada → plan completo → verificar todos los bytes → publicar bajo CAS. Se comprueba bucket privado y admisión de MIME CSV/JSON si está restringida; no se cambia su configuración. Paths y UUID reservado de dataset los genera SQL, nunca el cliente. POST usa `x-upsert:false`; un objeto existente sólo se acepta tras comprobar hash y tamaño exactos.

| Interrupción o carrera | Recovery probado |
|---|---|
| Raw todavía ausente | Journal PREPARED; reenviar mismo archivo/intención, sin mover Pack |
| Raw presente / JSON ausente | Regenerar determinísticamente desde raw y verificar ambos |
| Storage YES / DB NO | Reconciliar journal y metadata, sin objetos sobrescritos ni publicación anticipada |
| Metadata confirmada / respuesta perdida | Recuperar mismo dataset; no duplicar |
| Publicación confirmada / respuesta perdida | Replay de intención devuelve la misma Version antes de revisar flags/revisión mutables; mantiene checks de actor/permisos |
| CAS conflict | Mantener candidato/selección; recargar y revisar explícitamente, sin retry ciego |
| Dos uploads iguales concurrentes | Reservas de paths distintas, un dataset deduplicado; limpiar exclusivamente objetos huérfanos de la reserva perdedora |
| Raw/JSON faltantes o corruptos al publicar | Rechazar publicación; versión actual preservada |
| Descartar candidato interrumpido | Idempotente; borrar sólo reserva sin consumidores demostrados; cleanup pendiente recuperable |

Los tests usan PostgreSQL/PostgREST y API reales locales con fixtures de identidad/Auth y contrato HTTP de Storage privado; no certifican el servicio Storage/Auth productivo. El fixture admite explícitamente `text/csv` y `application/json`. No se disfraza JSON como CSV para eludir MIME. En un release futuro autorizado deberá comprobarse esa capacidad del bucket privado. No fue necesario tocar Storage productivo para completar T4.

## Dataset Reuse

Reuse explícito sólo dentro del workspace y con entidad, contract/hash, normalizer, unidades/configuración e **identidad de la Model Version publicada** compatibles. La política MVP es conservadora: dos Cases ligados a la misma Version pueden reutilizar el dataset; otra Version requiere validar/subir explícitamente aunque los raw bytes sean idénticos. No se declara equivalencia entre Versions ni se convierte legacy.

La unicidad combina workspace, tipo semántico, raw hash y contract hash; además se comprueban canonical hash y binding de Model/normalizer. Así, mismos bytes/contrato reutilizan un dataset lógico, mientras mismos bytes/otro contrato crean otro. El Hub representa los records normalizados verificando su hash; evita el sniff de delimitadores del flujo legacy para la cohorte nueva. El raw download histórico conserva su comportamiento.

## Case Data UX

Entrada desde el Case T3 y URL contextual que preserva su ID. Se compone `createDropCard`, drawer de validación, `mountDialog`, helpers de forms T3 y clases/tokens nativos. Sólo se agrega layout scoped y tablas de preview del nuevo flujo; el factory y los componentes legacy no se reescriben.

Flujo: descargar template → elegir CSV → validar/preview → guardar candidato → selección explícita → confirmar publicación → historial. Reuse y recovery son alternativas visibles. Una publicación parcial deliberada del Pack, por ejemplo sólo demanda, sigue siendo un **manifest completo de sus slots presentes**; no representa Decision READY. Estado publicado y candidato aparecen por separado.

Los IDs/intenciones se guardan en un draft de sesión; el CSV no se persiste en el browser. La publicación perdida reusa el body/UUID guardado. Seleccionar ambos CSVs y guardar uno conserva el otro; la publicación permanece bloqueada hasta guardar o quitar las selecciones locales. Reemplazar/quitar archivo y consultar columnas usan las acciones nativas. Viewer puede leer y volver al contexto, con escrituras deshabilitadas.

| Before | After | Why |
|---|---|---|
| T3 permitía crear el Case con Pack vacío, sin panel de carga Ultimate | Panel contextual de demanda/recursos con el mismo shell/tokens | Administrar inputs sin requerir archivos para que el Case exista |
| Copy/headers estáticos de Orders/Fleet | Descriptor del servidor, headers exactos y celdas opcionales diferenciadas | Evitar dos schemas y mensajes que sugieran omitir headers |
| Archivo seleccionado/validado sin una distinción Ultimate de publicación | Candidato, warnings/errors y Pack publicado separados | No insinuar READY ni mover el pointer por un upload |
| Primer montaje T4 omitía la clase contextual del uploader y reemplazaba la clase de posición del badge | Contexto `dispatch-upload-pro` y badge nativo conservados | Restituir iconos de trazo, tamaño de controles y estado legible sin tocar CSS global |
| Acciones del archivo permanecían ocultas y preview apretaba headers en columnas mínimas | Acciones visibles con archivo y preview horizontal enfocable con headers legibles | Permitir quitar selección/consultar contrato y leer datos sin deformar tablas |
| Interrupciones/retries sin una UI Ultimate propia | Recovery por identidad, confirmación modal y revisión explícita tras CAS | Conservar intención, historial y foco |

Antes del cambio se capturaron primitivas vigentes a 1440/390 px. La comparación final usa misma fixture/theme/datos antes/después de cargar CSS T4: píxeles y estilos computados idénticos a **1440, 1280, 1024, 768 y 390 px**. Es una comprobación de primitivas nativas y ausencia de contaminación global, no una afirmación de igualdad de pantallas con nueva funcionalidad.

W4 comprueba la superficie real a esos anchos y 320 px, zoom 200%, filename máximo/Unicode, teclado, foco visible y no tapado, Escape/retorno, reduced motion y touch. Las capturas previas al último arreglo local se preservan en `evidence/visual-composition-fix/`; las finales, en `evidence/browser/`. La prueba ahora comprueba también geometría del badge, trazo/tamaño de iconos, tamaño del file picker, lectura de headers y visibilidad/funcionamiento de las acciones. No se agregó animación propia.

El audit de contraste de la superficie final midió **117 elementos de texto**, mínimo **5,429:1**, sin fallos; el documento no presenta overflow horizontal a ninguno de los seis anchos. Las tablas pueden desplazarse dentro de su región enfocable. [Contraste](evidence/browser/contrast.json), [responsive](evidence/browser/responsive.json), [foco](evidence/browser/keyboard-focus.json), [captura 1440 px](evidence/browser/case-data-1440.png), [captura 390 px](evidence/browser/case-data-390.png).

Historial paginado a veinte versiones y reuse a veinticinco datasets. La vista de candidatos muestra los veinte recientes; los journals son durables y el recovery por UUID sigue disponible. No se implementó purga/TTL automática.

## Legacy Compatibility

Orders/Fleet siguen en su rama de contrato/validación/raw/dedup, con sus IDs, downloads, reuse, archive/delete y journals. No hay conversión ni backfill. El archive de nuevos tipos pasa por RPC comprobado; el guard de delete reconoce la metadata normalizada como consumidor durable.

Se ejecutaron cuatro pruebas focales del Data Hub, incluida una con browser real y worker v1: upload/library/lineage/download/safe delete; cleanup autorizado; filtros/historial/lectura sin efectos; y respuesta perdida de upload comprometido. También se repitió el flujo T3 Model → publicación → Case sin CSV → reload.

Las atribuciones Admin/Operator para administrar datos permanecen iguales al upload existente; Viewer sigue readonly. No se asigna automáticamente Data Owner ni Decision Owner, ni se cambia el contexto/las responsabilidades del Case. Los gates de ejecución y approvals no se eluden: Ultimate runtime permanece cerrado. S4 comprueba preservación de owners/contexto además de permisos y separación de tenants.

## Tests

Resultados finales y comandos exactos: [test ledger](test-ledger.json), [command ledger](command-ledger.json), [runtime](evidence/runtime.json). Cada resultado tiene timestamps, duración, exit code y hash del log. U4 se contabiliza dentro de B-PY para no repetir una suite por su alias.

| Suite | Tests | Estado | Failures / errors / skips |
|---|---:|---|---|
| B-PY | 498 | PASS | 0 / 0 / 0 |
| B-NODE | 134 | PASS | 0 / 0 / 0 |
| U4, incluido en B-PY | 25 | PASS | 0 / 0 / 0 |
| S4 | 30 | PASS | 0 / 0 / 0 |
| W4, última ejecución sobre UI final | 8 | PASS | 0 / 0 / 0 |
| Focal legacy Hub/API/browser | 4 | PASS | 0 / 0 / 0 |
| Focal T3 Case Setup browser | 1 | PASS | 0 / 0 / 0 |

**Cobertura funcional:** U4 prueba exact schema, campos condicionales, dimensiones activas, source/cost/billing, privacidad, raw/canonical hashes, null/0 y versiones desconocidas. Su matriz Q cubre 3 roles × 3 conjuntos de fuentes × 4 dimensiones, compilando ambas entidades. O prueba disponibilidad ASSUMED/default/provenance; P demanda pseudonimizada y extras comerciales rechazados; R tipos/fechas/enums/IDs/capacidades/escala inválidos. Son escenarios controlados implementados en U4, no archivos O/P/Q/R preexistentes ni datos comerciales reales.

S4 cubre manifests acumulativos/inmutables, CAS y concurrencia, dedup/reuse/Model incompatible, bytes corruptos o faltantes, recovery/replay, descarte/cleanup, flags, direct grants/RLS, tenant/actor/Viewer, paths/schema forjados, protección de delete, preview/Hub y owners intactos. W4 cubre upload/preview/publicación/reload, errores/contrato/foco, interrupción/recovery, respuesta perdida, reuse/CAS, responsive/stress y selección de múltiples archivos.

No se repitió B-BROWSER/B-E2E completo ni todo B-SQL histórico: el impacto demostrado se verificó con W4/S4 y los focales anteriores. Se reutiliza T0–T3 como baseline aprobado. Tras corregir copy y luego composición/acciones/preview, se repitió W4; tras el último CSS, también la comparación visual de primitivas. Backend/parser/SQL y los consumidores cubiertos por B-PY/B-NODE/S4/focales no cambiaron: [justificación de reuse de QA](evidence/qa-reuse.json).

Los intentos intermedios se conservan en `evidence/attempts/` y no se presentan como PASS finales. Incluyen una carrera de startup del sandbox, alias SQL ambiguo en reuse, permisos archive del reader delegado, readiness DOM obsoleto y un teardown del harness mal enlazado. Todos se corrigieron y las suites afectadas se ejecutaron de nuevo. La inspección de capturas detectó después la composición CSS/acciones; W4 se amplió para cubrir su comportamiento real. Un intento que no llegó a ejecutar tests no cuenta como suite aprobada.

## Deviations

- Se agregó una migración aditiva para los journals/objetos/publicaciones previstos por T4; se mantienen las estructuras Pack/Version/Entry T2/T3 y sus invariantes. No hizo falta rediseño contractual.
- La compatibilidad de reuse exige la misma Model Version, una concreción conservadora de la política exacta aprobada. No se introdujo un mapeo entre versiones.
- La UI compone el uploader existente; se agregó un módulo específico para orquestar su nuevo lifecycle. El uploader legacy no representa candidates/manifests Ultimate y por eso no bastaba reutilizar su controlador completo.
- Se corrigieron etiquetas heredadas de scripts de evidencia (`post-T3`/`T4` y `t4_stylesheet_loaded_after`). El driver visual ya cargaba `ultimate-case-data.css`; fue una corrección de metadata, no una alteración de resultados ni logs. [Registro](evidence/evidence-label-corrections.json).
- La consulta de changelog CLI fue rechazada por el proxy; no se intentó evadirlo. Se registran las versiones instaladas y la documentación oficial de Storage consultada por MCP. Ninguna verificación obligatoria quedó omitida por ese acceso.

## Risks

1. **Release pendiente:** migración/flags y compatibilidad MIME del bucket productivo no se aplicaron ni comprobaron mediante escritura. El release autorizado deberá verificar Storage privado CSV+JSON y catálogo antes de habilitar publicaciones. No se afirma deploy validado.
2. **Límites MVP explícitos:** 10 MiB tanto para raw como normalizado y 10.000 filas; los límites se validan antes de publicar. No existe soporte XLSX ni megarchivos/chunking de inputs. El backend lee esos objetos acotados para verificar hashes; no se afirma un benchmark de carga productiva.
3. **Desconocidos admitidos con honestidad:** costos/disponibilidad unknown pueden formar un candidato válido con advertencias; la habilitación económica y factibilidad de una Decision será resuelta por fases posteriores. El dato no se cambia a cero, infinito o confirmado.
4. **Journals y visibilidad:** los veinte candidatos recientes son una lista acotada de UI. Recovery por identidad y metadata durable se preservan; no hay TTL/purga automática, ni un nuevo proceso de mantenimiento fuera de alcance.
5. **Administración externa de bytes:** el flujo impide upsert y protege consumers de borrado por Dation. Una eliminación administrativa fuera de la aplicación requiere controles operativos de Storage en el release; la lectura/publicación detectan bytes ausentes o con hash incorrecto.
6. **Frente posterior:** Graph/readiness/admission/invalidación completa/InputSummary de decisión/IA no se implementaron aquí. Tener ambos slots publicados no habilita ejecución. Estas tareas no están marcadas PASS como si pertenecieran a T4.
7. **Estado Git heredado:** el trabajo T0–T4 sigue local y sin staging/commit. El manifest permite revisar esta fase por separado, sin atribuirle todos los archivos pendientes del repositorio.

## Rollback

Cerrar nuevas publicaciones mediante el flag T4 en un procedimiento futuro autorizado; conservar lectura y snapshots existentes. Reconciliar journals y metadata antes de cualquier limpieza. Descartar únicamente candidatos/reservas sin consumidores comprobados. No hacer down migration destructiva, borrar historia, reemplazar bytes consumidos, mover Runs ni fabricar una versión anterior. S4 verifica lectura/replay tras cierre del flag y descarte idempotente. En esta ejecución no se modificó ningún flag o entorno productivo.

## Gate Evaluation

| Gate | Estado de T4 | Evidencia / límite |
|---|---|---|
| G-A — Alcance | PASS | Orden exclusiva T4, checkpoint, diff de 25 archivos, sin auditoría nueva ni escritura remota |
| G-C — Contract | PASS | Descriptor único y versionado; U4; mismo contrato gobierna template/parser/normalizer; ningún mapping fuzzy |
| G-D — Datos | PASS | Migración aditiva en sandbox, manifests completos/inmutables, catálogo/ACL/RLS y cinco filas previas preservados; S4 |
| G-E — Engine | N/A implementación nueva | Engines/solver fuera de T4; suite B-PY preservada. No se declara implementado D1/D2 Ultimate |
| G-R — Result | PASS en inputs; N/A package nuevo | Hashes canónicos/null/provenance coherentes; resultados y assembler no modificados |
| G-L — Lineage | PASS en Pack | Versiones previas y consumidores conservados, CAS/replay/faults/concurrencia; lineage de Runs y closure completa permanecen fuera de fase |
| G-S — Security | PASS en sandbox | Membership/actor/Viewer, tenant/FKs, paths derivados, privados/RLS/grants, extras antes de persistencia, sin acceso productivo |
| G-P — Performance | PASS en alcance acotado | Límites de bytes/filas, preview/report/assumptions acotados, history/reuse paginados; sin claim de carga productiva |
| G-UI — UI Preservation / Skills | PASS | Componentes nativos, corrección de su composición, W4, contraste/foco/zoom/touch y paridad visual scoped; sin tokens globales alterados |
| G-ENV — Entorno | PASS | Suites con tests > 0, sin skips/failures/errors; runners conocidos, SQL local owned y cleanup comprobado |
| G-B — Deuda histórica | Baseline aprobado preservado | Ninguna regresión nueva observada en las suites requeridas/focales; no se ocultaron ni desactivaron asserts |
| G-REL — Release | NOT RUN | No autorizado en T4; sin deploy, pipeline observado, migración remota ni push. T11/T12 pendientes |

Las condiciones STOP específicas se revisaron contra los resultados finales:

| Condición que bloquearía T4 | Resultado |
|---|---|
| Mapping heurístico o schemas divergentes entre template/backend | No observado; compiler único y exact schema |
| Bytes consumidos reemplazables por el flujo Dation | No observado; no-upsert, hash verification y protección de consumidores |
| Current Pack apuntando a upload incompleto | Rechazado en S4; pointer anterior intacto |
| Retry creando Versions duplicadas | Rechazado; replay devuelve misma Version/intención |
| Reuse cross-tenant o refs arbitrarias | Rechazado por API/RPC/FKs y Storage lookup autorizado |
| Extras comerciales/PII persistidos silenciosamente | Rechazados antes de journal/Storage; sin eco de valores en errores |
| Dedup del mismo raw bajo otro contrato | No ocurre; dataset lógico distinto y binding/version comprobados |
| Ruptura de upload/Hub legacy | No observada en cuatro focales, incluido browser/worker real |
| Pack readiness implementando el Graph T5 | No ocurre; `decision_readiness=null` y ejecución Ultimate cerrada |
| Solver/engine necesario para validar | No; normalización y DTOs puros |
| Cambio de Storage productivo necesario para continuar T4 | No; fixtures autorizados y configuración productiva intacta |

Los defectos intermedios se corrigieron dentro de T4 y se verificaron otra vez. No queda una STOP CONDITION abierta. Se retiraron los recursos locales owned de esta fase sin detener el daemon ni recursos ajenos: [cleanup](evidence/cleanup.json). El [estado final](evidence/final-state.json) registra HEAD, branch, staging vacío y alcance local; el manifest final verifica los archivos revisables y la resolución histórica T3.

## FINAL DECISION

**GO — T4 completado. T5 puede ser solicitado.**

T5 no fue ejecutado. El trabajo queda local, sin staging, commit, push, deploy ni cambios productivos.
