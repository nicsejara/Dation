# Revalidación de los103 criterios anteriores

No se heredan PASS de R2. La evidencia de esta ejecución cubre los contratos anteriores; las correcciones textuales de R3 (DIRECT/OWN banda, perfil visible, reset real y errores por intención) prevalecen ante la presentación previa.

| ID | Criterio anterior | Estado | Evidencia actual |
|---|---|---|---|
| GLB-001 | Cinco bloques oficiales, sin renombre accidental | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-002 | Icono ORIGINAL visible ANTES de 01..05 | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-003 | Título interno semibold + línea teal 40-44×2 + ayuda semántica | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-004 | Barra superior tiene dos acciones, igual width/height, no Cambiar modelo | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-005 | Círculo validado sólo tras confirmación realmente válida | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-006 | Foco, teclado y `aria` en cards y acordeones | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-007 | Cinco footers usan la MISMA clase y tokens | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-008 | Cinco CTAs misma altura/ancho/alineación en desktop y móvil | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-009 | Confirmaciones locales no publican por sí solas | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-010 | Un input material invalida firma/preview y check | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-011 | Modelos publicados sin botones editables efectivos | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-012 | 1536/1024/768/390/320 sin overflow ni truncamientos | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| GLB-013 | No ampliar D1/D2/SQL/backend/infra/FX; diff scope documentado | PASS | R3-01/02/03/05/08; geometry/a11y/CTA; diff |
| B01-001 | B01 nombre required, descripción optional y placeholders correctos | PASS | V1 12 regresiones y R3-02/07/08 |
| B01-002 | B01 icono tag, field underline, columnas y footer final | PASS | V1 12 regresiones y R3-02/07/08 |
| B01-003 | B01 Create New y Reuse con draft/permiso correctos | PASS | V1 12 regresiones y R3-02/07/08 |
| B02-001 | Rol radio 3 opciones exactas SHIPPER/LOGISTICS_PROVIDER/HYBRID | PASS | Ultimate02 y R3-01/06/08 |
| B02-002 | Transporte directo read-only, no selector ficticio | PASS | Ultimate02 y R3-01/06/08 |
| B02-003 | Consolidación 2 radios true/false y no split implícito | PASS | Ultimate02 y R3-01/06/08 |
| B02-004 | Sin boton Cambiar modelo redundante | PASS | Ultimate02 y R3-01/06/08 |
| B04-001 | OWN/EXTERNAL multiselect; al menos una requerida | PASS | guided11 y R3-01/05/08 |
| B04-002 | GENERAL/REFRIGERATED/TANKER/BULK/FLATBED 5 cards en una fila 1536 | PASS | guided11 y R3-01/05/08 |
| B04-003 | Categorías vacías no filtran vehículos | PASS | guided11 y R3-01/05/08 |
| B04-004 | No resumen final B04 | PASS | guided11 y R3-01/05/08 |
| B04-005 | Cambiar fuentes actualiza condicionales B05 y firma | PASS | guided11 y R3-01/05/08 |
| B05-001 | ARS/USD/EUR 3 tarjetas radio mismo renglón | PASS | Ultimate02/08 y R3-01/05/08 |
| B05-002 | Moneda histórica no elegible preservada en readonly | PASS | Ultimate02/08 y R3-01/05/08 |
| B05-003 | OWN readout fijo sólo cuando fuente OWN | PASS | Ultimate02/08 y R3-01/05/08 |
| B05-004 | PER_TRIP/PER_KM multiselect y requerido si EXTERNAL | PASS | Ultimate02/08 y R3-01/05/08 |
| B05-005 | ONE_WAY/ROUND_TRIP multiselect sólo si EXTERNAL+PER_KM | PASS | Ultimate02/08 y R3-01/05/08 |
| B05-006 | Minors 0..6 avanzados, default 2 nuevo, preserve guardado | PASS | Ultimate02/08 y R3-01/05/08 |
| B05-007 | No se pide tarifa real en este bloque; no FX | PASS | Ultimate02/08 y R3-01/05/08 |
| B03-001 | B03 exactly 3 visual step headings; no seven-step navigation | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-002 | Sin botones internos Volver/Continuar ni CTA de Paso1 | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-003 | Paso1 5 tipos radio PALLET/BOX/CRATE/BIG_BAG/OTHER | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-004 | Cambio de tipo altera campos/ilustración, sin pérdida silenciosa | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-005 | Pallet dims cargadas al `LoadPresentation.loaded_dimensions`, no al soporte vacío | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-006 | Tara 25 en `LogisticUnit.tare_mass`, una sola vez en bruto | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-007 | Pallet 120×100×150 cm → 1.80 m³ exterior cargado | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-008 | Pallet vacío ilustración separada del pallet cargado | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-009 | BIG_BAG permite volumen externo declarado y tara, sin prisma falso | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-010 | OTHER soporta nombre personalizado/volumen o dimensiones del backend | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-011 | No se confunde `cargo.profile` con `logistic_unit.type` | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-012 | Paso2 omite unidad comercial/sobres por caja/displays | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-013 | Paso2 producto, tipo de bulto, medidas, kg/bulto, bultos/unidad | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-014 | Product.dimensions informativo NO como volumen exterior de pallet | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-015 | 30×20×30cm →0.018m³ por caja sólo informativo | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-016 | 80×8kg=640kg componentes +25kg tara =665kg total | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-017 | `80` bultos declarado por user, no deducido de packing escalar | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-018 | Nuevas presentaciones homogeneous tienen exactamente un component | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-019 | Distintos productos en distintas presentaciones, soporte compartido | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-020 | Presentaciones mixtas históricas preservadas al cargar y no destruidas | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-021 | Paso3 sólo peso/volumen como tarjetas restricciones primarias | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-022 | No hay `pallets` activo oculto imponiendo capacidad en nuevo guided | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-023 | primary_dimension válido y activo sin selector visible | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-024 | La cantidad de presentaciones en order_lines no se confunde con primary weight | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-025 | Al menos 1 dimensión activa, por defecto 2 donde completas | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-026 | Split INDIVISIBLE vs DISCRETE preserva semántica de ORDEN | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-027 | Compatibility_policy/co_load_pairs no cambiados silenciosamente | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-028 | Modo catalog requiere producto+presentación y tres CSV | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-029 | Modo direct conserva 2 CSV sin catálogo físico inventado | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-030 | Granel continuo legacy no obligado a usar soporte BIG_BAG | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-031 | Avisos no packing 3D/mezcla futura/cantidad por presentación visibles | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-032 | Un ÚNICO CTA Confirmar carga y capacidad al final | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-033 | CTA B03 valida preview de firma actual, sin stale success | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-034 | CTA no publica ni duplica requests al doble click | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-035 | Error red/validación enfoca primer subbloque inválido preservando datos | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-036 | Editar campos tras confirmar invalida check y botón global | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-037 | Si cantidad/peso no informado, mostrar pendiente no cero | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-038 | Discrete no permite cantidades fraccionarias de bultos | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-039 | Protección de eliminar/duplicar catálogo y límites 100/50/200/30 | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| B03-040 | Abrir/cerrar subsección no muta payload ni confirmación | PASS | Ultimate01/03/04/06/07, guided02/07/09/10 y R3-03/04/06/08 |
| CTA-001 | Inventario de TODAS las acciones con efecto declarado | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-002 | Create New maneja draft pendiente sin pérdida | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-003 | Select Existing carga versión publicada correcta | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-004 | CTA B01/02/03/04/05 geometría misma clase+bounding rect | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-005 | Toolbar action y confirm/local/global nunca se confunden | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-006 | New publish guarded by compiled current + all confirmations | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-007 | Reintento publicación no crea duplicados | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-008 | Cancelar borrado no elimina; confirmado respeta referencia | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| CTA-009 | Published snapshots read-only, no hidden mutation via click | PASS | CTA.md; R3-01/02/04/05/07/09;45 tests locales |
| ROL-001 | Regreso actual desde Data Contract no borra draft ni muta published | PASS | R3-07, Saga10Wizard02/04 y blueprint/runbook |
| ROL-002 | Blueprint review-only futura documentada, NO implementada en PR | PASS | R3-07, Saga10Wizard02/04 y blueprint/runbook |
| ROL-003 | Rollback técnico versión/digest compatible registrado (no ejecutado) | PASS | R3-07, Saga10Wizard02/04 y blueprint/runbook |
| CI-001 | Baseline SHA exacto/main actual y clasificación impacto | PASS | Clasificación real/CI exacta en PR; sin políticas cambiadas |
| CI-002 | Fast requerido verde, FULL sólo si impact lo exige | TRACKED_IN_PR | Clasificación real/CI exacta en PR; sin políticas cambiadas |
| CI-003 | No ampliar UX allowlist para forzar auto deploy | PASS | Clasificación real/CI exacta en PR; sin políticas cambiadas |
| CI-004 | PR no mergeado ni desplegado por Codex sin GO | PASS | Clasificación real/CI exacta en PR; sin políticas cambiadas |
| UX-001 | Barra superior tiene exactamente las dos acciones correctas; mismo ancho y alto; no «Cambiar modelo» redundante | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-002 | Los cinco acordeones preservan nombres oficiales e iconos originales antes del número | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-003 | Títulos internos semibold + línea turquesa corta compartida; sin iconos junto a títulos | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-004 | Footers de B01/B02/B04/B05 geométricamente idénticos (test DOM) y confirmación/invalidez consistente | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-005 | B02 rol = radio tres opciones serializadas correctamente; transporte DIRECT readout; consolidación radio true/false | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-006 | B04 fuentes = dos checkboxes independientes, mínimo una; categorías = cinco checkboxes en una fila desktop | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-007 | B04 sin resumen al final; categorías vacías son válidas y no aplican filtro de tipo | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-008 | B05 monedas = radio ARS/USD/EUR para nuevos modelos; snapshots existentes sin mutación ni FX | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-009 | B05 propia solo si OWN; externa solo si EXTERNAL; bases solo si EXTERNAL+PER_KM; multiselección y payload correctos | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-010 | B05 precisión 0..6 existente, default 2 para nuevo modelo cuando aplique; cambiar moneda no reescribe precisión automáticamente | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-011 | B05 sin importes tarifarios; nota de costos reales solo en flota; desconocido ≠ 0 | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-012 | Check de encabezado solo tras confirmación válida; invalidez al editar campos/condicionales; modelo publicado inmutable | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-013 | Sin cambios a D1/D2, SQL, API, modelos físicos ni políticas existentes | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-014 | Capturas reales dark mode y tests en 1536, 1024, 768, 390, 320; sin overflow, accesibilidad teclado | PASS | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
| UX-015 | Conservar tests previos, ejecutar pruebas pertinentes y ruta CI R2/FAST si el diff real lo permite; NO alterar classifier/policies para forzar fast | TRACKED_IN_PR | R3-01..09 + Ultimate01..08 + V1/Guided/Saga10 regresión |
