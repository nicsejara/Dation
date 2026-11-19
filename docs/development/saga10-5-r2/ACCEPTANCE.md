# Acceptance — 103 requirements

88 final requirements plus15 retained V3 criteria. PASS means verified by the referenced local browser test, source contract or evidence. CI checks are tracked separately at the final candidate SHA in the PR; no green result is presumed here. `Ultimate NN` refers to test_saga10_5_ultimate.UltimateProTests.test_NN; `legacy guided` to test_saga10_5_guided; `legacy wizard` to test_logistics_model_wizard.

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| GLB-001 | Cinco bloques oficiales, sin renombre accidental | PASS | Screens B01–B05, Ultimate 01/05 |
| GLB-002 | Icono ORIGINAL visible ANTES de 01..05 | PASS | Screens B01–B05; guidedBlock icon before title |
| GLB-003 | Título interno semibold + línea teal 40-44×2 + ayuda semántica | PASS | Ultimate 05: 44×2 px pseudo-element + CSS semibold |
| GLB-004 | Barra superior tiene dos acciones, igual width/height, no Cambiar modelo | PASS | geometry.json toolbar; legacy create/reuse flows |
| GLB-005 | Círculo validado sólo tras confirmación realmente válida | PASS | Ultimate 01; legacy guided 01 |
| GLB-006 | Foco, teclado y `aria` en cards y acordeones | PASS | Ultimate 02/05; a11y.json; native controls |
| GLB-007 | Cinco footers usan la MISMA clase y tokens | PASS | guided-ui.confirmFooter + single guided-confirm-footer class |
| GLB-008 | Cinco CTAs misma altura/ancho/alineación en desktop y móvil | PASS | geometry.json; Ultimate 05 |
| GLB-009 | Confirmaciones locales no publican por sí solas | PASS | Ultimate 06 request spy |
| GLB-010 | Un input material invalida firma/preview y check | PASS | Ultimate 06/07; legacy stale tests |
| GLB-011 | Modelos publicados sin botones editables efectivos | PASS | Ultimate 04/08; legacy immutable tests |
| GLB-012 | 1536/1024/768/390/320 sin overflow ni truncamientos | PASS | geometry.json: five widths; 15 real PNGs |
| GLB-013 | No ampliar D1/D2/SQL/backend/infra/FX; diff scope documentado | PASS | Final diff scope / DECISIONS.md |
| B01-001 | B01 nombre required, descripción optional y placeholders correctos | PASS | Ultimate 01; name field constraints and exact helpers |
| B01-002 | B01 icono tag, field underline, columnas y footer final | PASS | actual-B01-1536/390.png; Ultimate 05 |
| B01-003 | B01 Create New y Reuse con draft/permiso correctos | PASS | Legacy wizard 02/07/08/11; CTA.md |
| B02-001 | Rol radio 3 opciones exactas SHIPPER/LOGISTICS_PROVIDER/HYBRID | PASS | Ultimate 02 native radio keyboard; DTO construction |
| B02-002 | Transporte directo read-only, no selector ficticio | PASS | Ultimate 02 negative selector; config DIRECT |
| B02-003 | Consolidación 2 radios true/false y no split implícito | PASS | Ultimate 02 DTO false; unchanged split contract/D1 |
| B02-004 | Sin boton Cambiar modelo redundante | PASS | Toolbar/source and real screenshots; CTA.md |
| B04-001 | OWN/EXTERNAL multiselect; al menos una requerida | PASS | Ultimate 02; legacy guided 11 logical missing source |
| B04-002 | GENERAL/REFRIGERATED/TANKER/BULK/FLATBED 5 cards en una fila 1536 | PASS | geometry.json categoryTops at1536; actual-B04 |
| B04-003 | Categorías vacías no filtran vehículos | PASS | Existing domain/Data Contract tests (70 passed); no backend diff |
| B04-004 | No resumen final B04 | PASS | actual-B04 screenshot; no block summary DOM |
| B04-005 | Cambiar fuentes actualiza condicionales B05 y firma | PASS | Ultimate 02; cost review signature includes allowed_sources |
| B05-001 | ARS/USD/EUR 3 tarjetas radio mismo renglón | PASS | Ultimate 02 and actual-B05-1536 |
| B05-002 | Moneda histórica no elegible preservada en readonly | PASS | Ultimate 08 BRL/minor5; legacy V1 unchanged |
| B05-003 | OWN readout fijo sólo cuando fuente OWN | PASS | Ultimate 02 + actual-B05 |
| B05-004 | PER_TRIP/PER_KM multiselect y requerido si EXTERNAL | PASS | Ultimate 02 invalid/repair |
| B05-005 | ONE_WAY/ROUND_TRIP multiselect sólo si EXTERNAL+PER_KM | PASS | Ultimate 02 both bases + PER_KM dependency |
| B05-006 | Minors 0..6 avanzados, default 2 nuevo, preserve guardado | PASS | Ultimate 02/08; native options0–6; newDraft default2 |
| B05-007 | No se pide tarifa real en este bloque; no FX | PASS | actual-B05; no FX/backend diff; note unknown≠0 |
| B03-001 | B03 exactly 3 visual step headings; no seven-step navigation | PASS | Ultimate01 exactly3 panels / no legacy steps |
| B03-002 | Sin botones internos Volver/Continuar ni CTA de Paso1 | PASS | Ultimate01/actual-B03; no Back/Continue controls |
| B03-003 | Paso1 5 tipos radio PALLET/BOX/CRATE/BIG_BAG/OTHER | PASS | Ultimate03 five type transitions |
| B03-004 | Cambio de tipo altera campos/ilustración, sin pérdida silenciosa | PASS | Ultimate03 cancel and preserved dimensions |
| B03-005 | Pallet dims cargadas al `LoadPresentation.loaded_dimensions`, no al soporte vacío | PASS | Ultimate01 DTO loaded_dimensions + empty_dimensions None |
| B03-006 | Tara 25 en `LogisticUnit.tare_mass`, una sola vez en bruto | PASS | Ultimate01 DTO and real compiler665kg |
| B03-007 | Pallet 120×100×150 cm → 1.80 m³ exterior cargado | PASS | Ultimate01 120×100×150cm =1.8m³ |
| B03-008 | Pallet vacío ilustración separada del pallet cargado | PASS | Ultimate03 art type; actual-B03 empty/loaded art |
| B03-009 | BIG_BAG permite volumen externo declarado y tara, sin prisma falso | PASS | Ultimate03 declared1m³,902kg,DISCRETE |
| B03-010 | OTHER soporta nombre personalizado/volumen o dimensiones del backend | PASS | Ultimate03 OTHER transition; guided declared-volume renderer |
| B03-011 | No se confunde `cargo.profile` con `logistic_unit.type` | PASS | Separate profile/type DTO fields; Ultimate03 |
| B03-012 | Paso2 omite unidad comercial/sobres por caja/displays | PASS | actual-B03; guided renderer only unit_label, no commercial count fields |
| B03-013 | Paso2 producto, tipo de bulto, medidas, kg/bulto, bultos/unidad | PASS | Ultimate01/03 UI→DTO |
| B03-014 | Product.dimensions informativo NO como volumen exterior de pallet | PASS | Physical tests unchanged + Ultimate01 |
| B03-015 | 30×20×30cm →0.018m³ por caja sólo informativo | PASS | Ultimate01 UI0.018m³ informational |
| B03-016 | 80×8kg=640kg componentes +25kg tara =665kg total | PASS | Ultimate01 compiler/D1; dto.json |
| B03-017 | `80` bultos declarado por user, no deducido de packing escalar | PASS | User-input quantity80 asserted; no packing function |
| B03-018 | Nuevas presentaciones homogeneous tienen exactamente un component | PASS | Ultimate01/04 DTO components length1 |
| B03-019 | Distintos productos en distintas presentaciones, soporte compartido | PASS | Ultimate04 two products/two presentations/one support |
| B03-020 | Presentaciones mixtas históricas preservadas al cargar y no destruidas | PASS | Ultimate08 + legacy guided02/03 mixed E2E |
| B03-021 | Paso3 sólo peso/volumen como tarjetas restricciones primarias | PASS | actual-B03 + Ultimate07 dims |
| B03-022 | No hay `pallets` activo oculto imponiendo capacidad en nuevo guided | PASS | Ultimate01 dto.json + d1-dry-run.txt |
| B03-023 | primary_dimension válido y activo sin selector visible | PASS | Ultimate01/07 deterministic weight/volume primary |
| B03-024 | La cantidad de presentaciones en order_lines no se confunde con primary weight | PASS | Ultimate01 DTO quantity80 vs primaryweight; D1 finite quantity2 |
| B03-025 | Al menos 1 dimensión activa, por defecto 2 donde completas | PASS | Ultimate07 none blocked; newDraft weight+volume |
| B03-026 | Split INDIVISIBLE vs DISCRETE preserva semántica de ORDEN | PASS | Ultimate07 + D1_WEIGHT_PRIMARY_NO_HIDDEN_PALLETS_AND_SPLIT_PASS |
| B03-027 | Compatibility_policy/co_load_pairs no cambiados silenciosamente | PASS | Ultimate01/08; legacy guided10 |
| B03-028 | Modo catalog requiere producto+presentación y tres CSV | PASS | Ultimate01 real publication and3 CSV |
| B03-029 | Modo direct conserva 2 CSV sin catálogo físico inventado | PASS | Saga10 wizard03 + legacy guided03 direct2 CSV |
| B03-030 | Granel continuo legacy no obligado a usar soporte BIG_BAG | PASS | Legacy guided07 continuous density; Ultimate03 discrete bigbag |
| B03-031 | Avisos no packing 3D/mezcla futura/cantidad por presentación visibles | PASS | actual-B03 explanatory notes |
| B03-032 | Un ÚNICO CTA Confirmar carga y capacidad al final | PASS | Ultimate01/05 single final CTA and common footer |
| B03-033 | CTA B03 valida preview de firma actual, sin stale success | PASS | Ultimate06 held stale preview / invalidquantity |
| B03-034 | CTA no publica ni duplica requests al doble click | PASS | Ultimate06 double click request count |
| B03-035 | Error red/validación enfoca primer subbloque inválido preservando datos | PASS | Ultimate06 explicit retry focuses server error; showErrors/native invalid fields |
| B03-036 | Editar campos tras confirmar invalida check y botón global | PASS | Ultimate06/07 invalidates review/globalpublish |
| B03-037 | Si cantidad/peso no informado, mostrar pendiente no cero | PASS | Initial blank input values, summary number/known guard (cargo-editor) |
| B03-038 | Discrete no permite cantidades fraccionarias de bultos | PASS | Ultimate06 fractional1.5 + local native step1/server domain validation |
| B03-039 | Protección de eliminar/duplicar catálogo y límites 100/50/200/30 | PASS | Legacy guided09 max100/50/200/30; Ultimate07 references/copy/delete |
| B03-040 | Abrir/cerrar subsección no muta payload ni confirmación | PASS | Simple sections have no mutation toggle handlers; Ultimate05 repeated accordion toggles/geometry |
| CTA-001 | Inventario de TODAS las acciones con efecto declarado | PASS | CTA.md complete action inventory + browser cta-audit.json |
| CTA-002 | Create New maneja draft pendiente sin pérdida | PASS | Legacy wizard02/08/11 + draft-preserving startNew |
| CTA-003 | Select Existing carga versión publicada correcta | PASS | Legacy wizard12 + Saga01 recurrent-version test |
| CTA-004 | CTA B01/02/03/04/05 geometría misma clase+bounding rect | PASS | geometry.json; same confirmFooter helper |
| CTA-005 | Toolbar action y confirm/local/global nunca se confunden | PASS | Ultimate 06 network spy; CTA.md |
| CTA-006 | New publish guarded by compiled current + all confirmations | PASS | Ultimate 01/06/07; canPublish signature guard |
| CTA-007 | Reintento publicación no crea duplicados | PASS | Legacy wizard03/04/05/09/10 |
| CTA-008 | Cancelar borrado no elimina; confirmado respeta referencia | PASS | Ultimate 07; legacy guided04/10 |
| CTA-009 | Published snapshots read-only, no hidden mutation via click | PASS | Ultimate 04/08; real immutable version regressions |
| ROL-001 | Regreso actual desde Data Contract no borra draft ni muta published | PASS | Ultimate 04; Saga01 recurrent; JourneyNavigation11 |
| ROL-002 | Blueprint review-only futura documentada, NO implementada en PR | PASS | FUTURE_REVIEW_ONLY.md; no new route |
| ROL-003 | Rollback técnico versión/digest compatible registrado (no ejecutado) | PASS | RELEASE.md (not executed) |
| CI-001 | Baseline SHA exacto/main actual y clasificación impacto | PASS | G0.md; actual classifier R2/FAST |
| CI-002 | Fast requerido verde, FULL sólo si impact lo exige | TRACKED_IN_PR | Final exact-SHA GitHub run/checks recorded in PR body after completion |
| CI-003 | No ampliar UX allowlist para forzar auto deploy | PASS | No workflow/policy changes; NO_AUTO_DEPLOY |
| CI-004 | PR no mergeado ni desplegado por Codex sin GO | PASS | PR remains open; no merge/publication/deployment executed |
| UX-001 | Barra superior tiene exactamente las dos acciones correctas; mismo ancho y alto; no «Cambiar modelo» redundante | PASS | geometry.json toolbar; legacy create/reuse flows |
| UX-002 | Los cinco acordeones preservan nombres oficiales e iconos originales antes del número | PASS | Screens B01–B05; guidedBlock icon before title |
| UX-003 | Títulos internos semibold + línea turquesa corta compartida; sin iconos junto a títulos | PASS | Ultimate 05: 44×2 px pseudo-element + CSS semibold |
| UX-004 | Footers de B01/B02/B04/B05 geométricamente idénticos (test DOM) y confirmación/invalidez consistente | PASS | geometry.json; Ultimate 05 |
| UX-005 | B02 rol = radio tres opciones serializadas correctamente; transporte DIRECT readout; consolidación radio true/false | PASS | Ultimate 02 native radio keyboard; DTO construction |
| UX-006 | B04 fuentes = dos checkboxes independientes, mínimo una; categorías = cinco checkboxes en una fila desktop | PASS | geometry.json categoryTops at1536; actual-B04 |
| UX-007 | B04 sin resumen al final; categorías vacías son válidas y no aplican filtro de tipo | PASS | Existing domain/Data Contract tests (70 passed); no backend diff |
| UX-008 | B05 monedas = radio ARS/USD/EUR para nuevos modelos; snapshots existentes sin mutación ni FX | PASS | Ultimate 08 BRL/minor5; legacy V1 unchanged |
| UX-009 | B05 propia solo si OWN; externa solo si EXTERNAL; bases solo si EXTERNAL+PER_KM; multiselección y payload correctos | PASS | Ultimate 02 both bases + PER_KM dependency |
| UX-010 | B05 precisión 0..6 existente, default 2 para nuevo modelo cuando aplique; cambiar moneda no reescribe precisión automáticamente | PASS | Ultimate 02/08; native options0–6; newDraft default2 |
| UX-011 | B05 sin importes tarifarios; nota de costos reales solo en flota; desconocido ≠ 0 | PASS | actual-B05; no FX/backend diff; note unknown≠0 |
| UX-012 | Check de encabezado solo tras confirmación válida; invalidez al editar campos/condicionales; modelo publicado inmutable | PASS | Ultimate 06/07; legacy stale tests |
| UX-013 | Sin cambios a D1/D2, SQL, API, modelos físicos ni políticas existentes | PASS | Final diff scope / DECISIONS.md |
| UX-014 | Capturas reales dark mode y tests en 1536, 1024, 768, 390, 320; sin overflow, accesibilidad teclado | PASS | geometry.json: five widths; 15 real PNGs |
| UX-015 | Conservar tests previos, ejecutar pruebas pertinentes y ruta CI R2/FAST si el diff real lo permite; NO alterar classifier/policies para forzar fast | TRACKED_IN_PR | Final exact-SHA GitHub run/checks recorded in PR body after completion |
