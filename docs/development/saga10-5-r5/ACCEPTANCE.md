# Matriz de aceptación R5

110 criterios del paquete, sin eliminar ni redefinir requisitos. PASS combina ejecución local, capturas medidas e inspección de diff. El control GitHub y PR de G7 se registra con SHA/run terminal en el reporte del PR; no se declara CI verde por inferencia.

Alias: R5 = `test_saga10_5_r5.R5Tests`; R4 = `test_saga10_5_r4.R4Tests`; R3 = `test_saga10_5_r3.R3Tests`; Guided = `test_saga10_5_guided.Saga10GuidedTests` (ver nombre exacto en log); Tnn identifica el método con ese prefijo. No se suman reejecuciones para inflar cobertura.

| ID | Criterio | Resultado | Verificación / evidencia |
|---|---|---|---|
| R5-BASE-01 | Verificar HEAD main y PR130 antes de modificar | PASS | G0 / git · G0.md |
| R5-BASE-02 | No cambiar contratos ni motor D1/D2 | PASS | diff / contratos75 · ARCHITECTURE.md; evidence/contracts-75.txt |
| R5-BASE-03 | Un único PR sin merge | PASS | PR asociado a feat/saga10-5-r5-premium-ux · Reporte de integración del PR |
| R5-BASE-04 | No deploy ni billing/infra | PASS | diff / contratos75 · ARCHITECTURE.md; evidence/contracts-75.txt |
| R5-BASE-05 | Capturas anteriores conservadas como evidencia, no normativa | PASS | G0 navegador · evidence/baseline-layout.json; evidence/before-1440.png |
| R5-P1_UX-01 | Tres pasos B03 visibles sin acordeones internos | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/integrated-65.txt |
| R5-P1_UX-02 | Selector B03 muestra exactamente 5 unidades | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/integrated-65.txt |
| R5-P1_UX-03 | Título Tipo de unidad logística y copy debajo | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json; evidence/final-focal-7.txt |
| R5-P1_UX-04 | Título Dimensiones de la unidad cargada y copy debajo | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json; evidence/final-focal-7.txt |
| R5-P1_UX-05 | Separador visual limpio entre A/B | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json; evidence/final-focal-7.txt |
| R5-P1_UX-06 | Las etiquetas de campos usan acento sutil sin decorar exceso | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json; evidence/final-focal-7.txt |
| R5-P1_UX-07 | Los cinco tipos cambian el render del resumen | PASS | R5.T02 · evidence/asset-matrix.json; evidence/unit-*.png; evidence/final-focal-7.txt |
| R5-P1_UX-08 | Pallet vacío 3D correcto | PASS | R5.T02 · evidence/asset-matrix.json; evidence/unit-*.png; evidence/final-focal-7.txt |
| R5-P1_UX-09 | Caja vacía 3D correcta | PASS | R5.T02 · evidence/asset-matrix.json; evidence/unit-*.png; evidence/final-focal-7.txt |
| R5-P1_UX-10 | Cajón vacío 3D correcto | PASS | R5.T02 · evidence/asset-matrix.json; evidence/unit-*.png; evidence/final-focal-7.txt |
| R5-P1_UX-11 | Big bag vacío 3D correcto | PASS | R5.T02 · evidence/asset-matrix.json; evidence/unit-*.png; evidence/final-focal-7.txt |
| R5-P1_UX-12 | Otra unidad vacía 3D correcta | PASS | R5.T02 · evidence/asset-matrix.json; evidence/unit-*.png; evidence/final-focal-7.txt |
| R5-P1_UX-13 | Panel resumen legible cuando no hay datos | PASS | R5.T03 · evidence/empty-1440.png; evidence/pending-tare-2.txt |
| R5-P1_UX-14 | Tarjeta premium Volumen exterior calculado | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json; evidence/final-focal-7.txt |
| R5-P1_UX-15 | Volumen sin datos muestra pendiente (no 0) | PASS | R5.T03 · evidence/empty-1440.png; evidence/pending-tare-2.txt |
| R5-P1_UX-16 | Pallet 120×100×150cm=1.80m³ | PASS | R5.T01,T06 · evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P1_UX-17 | Cambiar a 160cm=1.92m³ | PASS | R4.T01 + estado puro · evidence/integrated-65.txt; evidence/pure-state-2.txt |
| R5-P1_UX-18 | Tara cero sólo si explícita | PASS | R5.T06 · evidence/pending-tare-2.txt |
| R5-P1_UX-19 | No se agrega botón Agregar unidad | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/integrated-65.txt |
| R5-P2_UX-01 | Producto y tipo de bulto jerarquizados | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json |
| R5-P2_UX-02 | Dimensiones y peso del bulto jerarquizados | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json |
| R5-P2_UX-03 | Volumen por bulto en tarjeta premium equivalente | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json |
| R5-P2_UX-04 | Caja 30×30×25cm=0.0225m³ | PASS | R5.T01,T03 / R4.T01 · evidence/final-focal-7.txt; evidence/integrated-65.txt; evidence/regression-published-dto.json |
| R5-P2_UX-05 | Caja 30×20×30cm=0.018m³ | PASS | R4.T01 · evidence/integrated-65.txt |
| R5-P2_UX-06 | Pallet cargado 3D correcto | PASS | R5.T02 · evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-P2_UX-07 | Caja cargada 3D correcta | PASS | R5.T02 · evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-P2_UX-08 | Cajón cargado 3D correcto | PASS | R5.T02 · evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-P2_UX-09 | Big bag cargado 3D correcto | PASS | R5.T02 · evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-P2_UX-10 | Otra unidad cargada 3D correcta | PASS | R5.T02 · evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-P2_UX-11 | Volumen de caja no sustituye volumen exterior | PASS | R5.T01,T03 / R4.T01 · evidence/final-focal-7.txt; evidence/integrated-65.txt; evidence/regression-published-dto.json |
| R5-P2_UX-12 | Resumen cargado peso 60×12+25=745kg | PASS | R5.T01,T03 / R4.T01 · evidence/final-focal-7.txt; evidence/integrated-65.txt; evidence/regression-published-dto.json |
| R5-P2_UX-13 | Resumen cargado peso 80×8+25=665kg | PASS | R5.T01,T03 / R4.T01 · evidence/final-focal-7.txt; evidence/integrated-65.txt; evidence/regression-published-dto.json |
| R5-P2_UX-14 | Resumen lado derecho equivalente Paso1 | PASS | R5.T01 + inspección visual · evidence/paired-complete-1440.png; evidence/addendum-geometry.json |
| R5-P2_UX-15 | Guardar tipo de carga permanece único CTA interno | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/regression-geometry.json; evidence/integrated-65.txt |
| R5-P2_UX-16 | Guardar tipo no publica | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-17 | Guardar 1 limpia formulario | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-18 | Mensaje orienta cargar segundo tipo | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-19 | Historial aparece BAJO formulario | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/regression-geometry.json; evidence/integrated-65.txt |
| R5-P2_UX-20 | Título Tipos de carga registrados | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-21 | Subtexto del historial aclaratorio | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-22 | Tarjeta historial contiene arte cargado miniatura | PASS | R5.T02 · evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-P2_UX-23 | Tarjeta historial contiene ordinal nombre y 3 métricas | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-24 | Tarjeta historial muestra estado guardado/revisar | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-25 | Tarjeta historial clic/teclado habilita editar | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-26 | Editar no crea nuevos IDs | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-27 | Actualizar CTA disabled si no hay cambios | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-28 | Dirty habilita CTA actualización | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-29 | Doble click guardar no duplica | PASS | R4.T02 · evidence/integrated-65.txt |
| R5-P2_UX-30 | Límite 2 tipos controlado | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-31 | Mensaje 2 de 2 y ruta de edición | PASS | R5.T03 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/final-focal-7.txt; evidence/pending-tare-2.txt |
| R5-P2_UX-32 | No agregar botón + tipo ni gestor catálogo | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/regression-geometry.json; evidence/integrated-65.txt |
| R5-P2_UX-33 | Error de guardado no limpia datos | PASS | R4.T02 · evidence/integrated-65.txt |
| R5-P2_UX-34 | Guardar B03 no deja segundo sucio sin revisar | PASS | R4.T02 · evidence/integrated-65.txt |
| R5-P3_CTA-01 | Peso y volumen siguen disponibles | PASS | R4.T10 + D1/contratos · evidence/integrated-65.txt; evidence/regression-d1-and-contract.txt |
| R5-P3_CTA-02 | Dividir se refiere a orden completa | PASS | R4.T10 + D1/contratos · evidence/integrated-65.txt; evidence/regression-d1-and-contract.txt |
| R5-P3_CTA-03 | No dividir un pallet físico | PASS | R4.T07 / D1 real del fixture · evidence/regression-d1-and-contract.txt |
| R5-P3_CTA-04 | D1 primaria válida e invisible | PASS | R4.T10 + D1/contratos · evidence/integrated-65.txt; evidence/regression-d1-and-contract.txt |
| R5-P3_CTA-05 | Bandas info no duplicadas | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/regression-geometry.json; evidence/integrated-65.txt |
| R5-P3_CTA-06 | B03 confirmar exige preview vigente | PASS | R4.T03,T06 / R3.T09 · evidence/integrated-65.txt |
| R5-P3_CTA-07 | B01 CTA disabled grisado y check verde | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-08 | B02 CTA disabled grisado y check verde | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-09 | B03 CTA disabled grisado y check verde | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-10 | B04 CTA disabled grisado y check verde | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-11 | B05 CTA disabled grisado y check verde | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-12 | Cambios relevantes reactivan CTAs | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-13 | Firma idéntica puede mantener confirmado | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-65.txt |
| R5-P3_CTA-14 | No dobles submits en validación asíncrona | PASS | R4.T03,T06 / R3.T09 · evidence/integrated-65.txt |
| R5-P3_CTA-15 | Geometría uniforme entre 5 CTA | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/regression-geometry.json; evidence/integrated-65.txt |
| R5-ESTADO-01 | B04 fuente no hace saltar a B03 | PASS | R3.T01 · evidence/integrated-65.txt |
| R5-ESTADO-02 | B04 categoría no hace saltar a B03 | PASS | R3.T01 · evidence/integrated-65.txt |
| R5-ESTADO-03 | B05 moneda no hace saltar a B03 | PASS | R3.T01 · evidence/integrated-65.txt |
| R5-ESTADO-04 | B05 tarifas no hacen saltar a B03 | PASS | R3.T01 · evidence/integrated-65.txt |
| R5-ESTADO-05 | Crear nuevo modelo limpia datos/IDs/checks | PASS | R4.T05,T12 · evidence/integrated-65.txt |
| R5-ESTADO-06 | Recarga mantiene tipos y estado de formulario | PASS | R4.T01,T02 · evidence/integrated-65.txt |
| R5-ESTADO-07 | Incógnito inicia borrador independiente | PASS | R5.T05 · evidence/final-focal-7.txt |
| R5-ESTADO-08 | Desde Decision Graph vuelve read-only publicado | PASS | R4.T07,T08,T13 · evidence/regression-published-review-return-2.png; evidence/regression-legacy-integrity.json; evidence/integrated-65.txt |
| R5-ESTADO-09 | Histórico incompleto muestra resumen humano | PASS | R5.T04 / R4.T08,T11 / Guided.T03 · evidence/historical-incomplete-1440.png; evidence/historical-metadata.txt; evidence/final-focal-7.txt; evidence/regression-legacy-integrity.json |
| R5-ESTADO-10 | No JSON crudo como UI primaria | PASS | R5.T04 / R4.T08,T11 / Guided.T03 · evidence/historical-incomplete-1440.png; evidence/historical-metadata.txt; evidence/final-focal-7.txt; evidence/regression-legacy-integrity.json |
| R5-ESTADO-11 | Histórico conserva payload original | PASS | R5.T04 / R4.T08,T11 / Guided.T03 · evidence/historical-incomplete-1440.png; evidence/historical-metadata.txt; evidence/final-focal-7.txt; evidence/regression-legacy-integrity.json |
| R5-ESTADO-12 | Un published no se modifica por UX | PASS | R4.T07,T08,T13 · evidence/regression-published-review-return-2.png; evidence/regression-legacy-integrity.json; evidence/integrated-65.txt |
| R5-ESTADO-13 | Cambio de tara recalcula ambos tipos | PASS | R4.T01 · evidence/integrated-65.txt |
| R5-ESTADO-14 | Cambio altura sincroniza ambas presentaciones | PASS | R4.T01 · evidence/integrated-65.txt |
| R5-VISUAL_ART-01 | Fichero assets mapea 5×2 sin URL externa | PASS | R5.T02 + SHA activos · ASSETS.json; evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-VISUAL_ART-02 | Lazy/estático sin request por tecla | PASS | R5.T02 · evidence/asset-network.json; evidence/asset-matrix.json; ASSETS.md |
| R5-VISUAL_ART-03 | Alt/aria correctos o decorativos | PASS | DOM + R5.T01,T02 · evidence/a11y-1440.json; evidence/final-focal-7.txt |
| R5-VISUAL_ART-04 | Fallback para asset faltante | PASS | R5.T05 · evidence/asset-fallback-1440.png; evidence/final-focal-7.txt |
| R5-VISUAL_ART-05 | No jump de layout al cambiar unidad | PASS | R5.T02 · evidence/final-focal-7.txt; evidence/unit-*.png |
| R5-VISUAL_ART-06 | Responsive 375px sin overflow | PASS | R5.T01 · evidence/addendum-geometry.json; evidence/paired-complete-*.png |
| R5-VISUAL_ART-07 | Responsive 768px coherente | PASS | R5.T01 · evidence/addendum-geometry.json; evidence/paired-complete-*.png |
| R5-VISUAL_ART-08 | Desktop 1280 y 1440 comparable | PASS | R5.T01 · evidence/addendum-geometry.json; evidence/paired-complete-*.png |
| R5-VISUAL_ART-09 | Contrast ratio y focus visible | PASS | R4.T09 + R5.T01,T03 · evidence/integrated-65.txt; evidence/a11y-*.json; evidence/final-focal-7.txt |
| R5-VISUAL_ART-10 | Reduced motion respetado | PASS | R4.T09 + R5.T01,T03 · evidence/integrated-65.txt; evidence/a11y-*.json; evidence/final-focal-7.txt |
| R5-VISUAL_ART-11 | Ilustración no afirma packing real | PASS | DOM R5 + R4.T09 · evidence/paired-complete-1440.png; ARCHITECTURE.md |
| R5-VISUAL_ART-12 | No fonts externas empaquetadas | PASS | R5.T02 + SHA activos · ASSETS.json; evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-VISUAL_ART-13 | No imágenes externas/stock | PASS | R5.T02 + SHA activos · ASSETS.json; evidence/asset-matrix.json; evidence/final-focal-7.txt |
| R5-CONTRATO-01 | 1 unidad lógica compartida por 2 presentaciones | PASS | R4.T01 + R5.T03 / estado puro · evidence/regression-published-dto.json; evidence/integrated-65.txt; evidence/pure-state-2.txt |
| R5-CONTRATO-02 | 1 producto por presentación | PASS | R4.T01 + R5.T03 / estado puro · evidence/regression-published-dto.json; evidence/integrated-65.txt; evidence/pure-state-2.txt |
| R5-CONTRATO-03 | IDs de producto/presentación estables | PASS | R4.T01 + R5.T03 / estado puro · evidence/regression-published-dto.json; evidence/integrated-65.txt; evidence/pure-state-2.txt |
| R5-CONTRATO-04 | Data Contract mantiene 3 CSV | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/contracts-75.txt; evidence/integrated-65.txt |
| R5-CONTRATO-05 | Líneas usan presentation_id y quantity | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/contracts-75.txt; evidence/integrated-65.txt |
| R5-CONTRATO-06 | Política co-load no cambia silenciosamente | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/contracts-75.txt; evidence/integrated-65.txt |
| R5-CONTRATO-07 | Separación orden indivisible vs discreta preservada | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/contracts-75.txt; evidence/integrated-65.txt |
| R5-CONTRATO-08 | Pruebas E2E sin modificar datos reales | PASS | Fixtures SQL/API/browser locales · README.md; evidence/integrated-65.txt |
| R5-CONTRATO-09 | No tercer tipo en nuevo guiado | PASS | R4.T01 + R5.T03 / estado puro · evidence/regression-published-dto.json; evidence/integrated-65.txt; evidence/pure-state-2.txt |
| R5-CONTRATO-10 | No botón Presentación activa / Soporte compartido | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/integrated-65.txt |
