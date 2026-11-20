# Matriz R6 — 132 criterios

Se conservan los132 IDs y requisitos del CSV normativo. Se reemplaza el estado pendiente por el resultado observado y se enlaza su evidencia. Los resultados de CI/PR y SHA finales se registran en el reporte del PR, sin crear un commit sólo para incluir su propio SHA.

Alias: R6=`test_saga10_5_r6.R6Tests`; R5=`test_saga10_5_r5.R5Tests`; R4=`test_saga10_5_r4.R4Tests`; R3=`test_saga10_5_r3.R3Tests`; R6Volume=`test_r6_volume_coherence.R6VolumeTests`. Tnn = método con ese prefijo. Las suites R4/R5 se vuelven a ejecutar sobre R6; no se hereda un PASS histórico.

| ID | Criterio | Resultado | Prueba / evidencia |
|---|---|---|---|
| R6-P1-Arte-01 | Cada tarjeta de cinco tipos muestra icono empty correcto | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-02 | Pallet card muestra pallet vacío | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-03 | Caja card muestra caja vacía | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-04 | Cajón card muestra cajón vacío | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-05 | Big bag card muestra big bag vacío | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-06 | Otra unidad muestra contenedor genérico vacío | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-07 | P1 resumen pallet muestra pallet cargado | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-08 | P1 resumen caja muestra caja cargada | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-09 | P1 resumen cajón muestra cajón cargado | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-10 | P1 resumen big bag muestra big bag cargado | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-11 | P1 resumen otra unidad muestra unidad cargada | PASS | R6.T02 + QA arte · evidence/asset-alpha.json; evidence/asset-light-dark-qa.png; evidence/asset-matrix.json; ASSETS.json |
| R6-P1-Arte-12 | No hay background baked-in | PASS | R6.T08 + inspección visual · evidence/asset-light-dark-qa.png; evidence/asset-alpha.json; ASSETS.md |
| R6-P1-Arte-13 | No hay halo oscuro | PASS | R6.T08 + inspección visual · evidence/asset-light-dark-qa.png; evidence/asset-alpha.json; ASSETS.md |
| R6-P1-Arte-14 | El arte mantiene escala constante | PASS | R6.T02 · evidence/integrated-76.txt; evidence/asset-matrix.json |
| R6-P1-Arte-15 | Ilustraciones conservan estilo del hero | PASS | R6.T08 + inspección visual · evidence/asset-light-dark-qa.png; evidence/asset-alpha.json; ASSETS.md |
| R6-P1-Arte-16 | Fallback sin red ni bloqueo | PASS | R6.T08 / R5.T05 · evidence/asset-fallback-1440.png; evidence/integrated-76.txt |
| R6-P1-Arte-17 | Decorativas sin alt redundante | PASS | R6.T02 · evidence/integrated-76.txt; evidence/asset-matrix.json |
| R6-P1-Arte-18 | Ningún arte sugiere packing certificada | PASS | R6.T03 + R4.T09 · evidence/volume-60-1440.png; evidence/integrated-76.txt |
| R6-P1-UX-01 | Los dos subtítulos internos son iguales tipográficamente | PASS | R6.T01 · evidence/r6-title-rule-geometry.json; evidence/complete-forms-1440.png |
| R6-P1-UX-02 | Las ayudas van bajo subtítulo | PASS | R6.T01 · evidence/r6-title-rule-geometry.json; evidence/complete-forms-1440.png |
| R6-P1-UX-03 | Campos L/W/H no alterados | PASS | R6.T03 / R5.T06 / D1 · evidence/integrated-76.txt; evidence/volume-unit.json; evidence/regression-d1-and-contract.txt |
| R6-P1-UX-04 | cm/m preserva magnitud | PASS | R6.T03 / R5.T06 / D1 · evidence/integrated-76.txt; evidence/volume-unit.json; evidence/regression-d1-and-contract.txt |
| R6-P1-UX-05 | Tara se aplica una vez | PASS | R6.T03 / R5.T06 / D1 · evidence/integrated-76.txt; evidence/volume-unit.json; evidence/regression-d1-and-contract.txt |
| R6-P1-UX-06 | Volumen exterior es sólo lectura | PASS | R6.T01 · evidence/addendum-geometry.json; evidence/complete-forms-*.png |
| R6-P1-UX-07 | Card de volumen abajo derecha | PASS | R6.T01 · evidence/addendum-geometry.json; evidence/complete-forms-*.png |
| R6-P1-UX-08 | Card ancho igual a P2 | PASS | R6.T01 · evidence/addendum-geometry.json; evidence/complete-forms-*.png |
| R6-P1-UX-09 | Card alto igual a P2 | PASS | R6.T01 · evidence/addendum-geometry.json; evidence/complete-forms-*.png |
| R6-P1-UX-10 | Panel resumen mismo ancho que P2 | PASS | R6.T01 · evidence/addendum-geometry.json; evidence/complete-forms-*.png |
| R6-P1-UX-11 | Cambio de unidad actualiza arte sin reiniciar datos inadvertidamente | PASS | R6.T02 / R4.T04 · evidence/integrated-76.txt; evidence/asset-matrix.json |
| R6-P1-UX-12 | Cambio de P1 reevalúa tipos guardados | PASS | R6.T04 · evidence/saved-invalid-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-01 | Resumen P2 muestra bulto individual | PASS | R6.T02,T03 · evidence/complete-forms-1440.png; evidence/unit-pallet-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-02 | Bulto caja usa caja sola | PASS | R6.T02,T03 · evidence/complete-forms-1440.png; evidence/unit-pallet-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-03 | El resumen sigue mostrando peso total unidad | PASS | R6.T02,T03 · evidence/complete-forms-1440.png; evidence/unit-pallet-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-04 | No se muestra pallet cargado como imagen de bulto Caja | PASS | R6.T02,T03 · evidence/complete-forms-1440.png; evidence/unit-pallet-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-05 | Volumen por bulto no cambia fórmula | PASS | R6.T01,T03 · evidence/addendum-geometry.json; evidence/r6-title-rule-geometry.json; evidence/volume-60-1440.png |
| R6-P2-UX-06 | Card volumen igual geometría P1 | PASS | R6.T01,T03 · evidence/addendum-geometry.json; evidence/r6-title-rule-geometry.json; evidence/volume-60-1440.png |
| R6-P2-UX-07 | Subtítulos P2 consistentes | PASS | R6.T01,T03 · evidence/addendum-geometry.json; evidence/r6-title-rule-geometry.json; evidence/volume-60-1440.png |
| R6-P2-UX-08 | Primer guardado limpia formulario | PASS | R5.T03 / R6.T04 · evidence/one-saved-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-09 | Guía tras primer guardado presente | PASS | R5.T03 / R6.T04 · evidence/one-saved-1440.png; evidence/integrated-76.txt |
| R6-P2-UX-10 | Historial bajo formulario | PASS | R4.T09 / R6.T02 · evidence/regression-geometry.json; evidence/asset-matrix.json; evidence/integrated-76.txt |
| R6-P2-UX-11 | Historial usa miniatura loaded | PASS | R4.T09 / R6.T02 · evidence/regression-geometry.json; evidence/asset-matrix.json; evidence/integrated-76.txt |
| R6-P2-UX-12 | Historial contador total 1 | PASS | R5.T03 / R6.T04 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/integrated-76.txt |
| R6-P2-UX-13 | Historial contador total 2 | PASS | R5.T03 / R6.T04 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/integrated-76.txt |
| R6-P2-UX-14 | No muestra de 2 en encabezado | PASS | R5.T03 / R6.T04 · evidence/one-saved-1440.png; evidence/two-saved-375.png; evidence/integrated-76.txt |
| R6-P2-UX-15 | Tarjeta guardada indica nombre | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-16 | Tarjeta indica cantidad | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-17 | Tarjeta indica peso bruto | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-18 | Tarjeta indica volumen exterior | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-19 | Tarjeta estado guardado | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-20 | Tarjeta estado revisar | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-21 | Tarjeta editable al hacer clic | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-22 | Edición no cambia IDs | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-23 | Segundo tipo no duplica primero | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-24 | Tercer tipo no permitido | PASS | R5.T03 / R4.T01,T02 / R6.T04 · evidence/two-saved-1440.png; evidence/integrated-76.txt; evidence/regression-published-dto.json |
| R6-P2-UX-25 | No aparecen CTA catálogo antiguo | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/integrated-76.txt |
| R6-VOL-01 | V exterior 1.8 correcto | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-02 | Vol nominal caja 0.0225 correcto | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-03 | V 60 cajas 1.35 correcto | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-04 | Ratio 60 cajas 75% | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-05 | V 90 cajas 2.025 correcto | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-06 | 90 cajas da error bloqueante para caja | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-07 | Mensaje vinculado a cantidad | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-08 | Error no borra valores | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-09 | 80 cajas igual no bloquea | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-10 | 80 cajas muestra advertencia | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-11 | No promete packing para inferiores | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-12 | R sin redondeos prematuros | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-13 | cm a m equivalente | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-14 | 2.52 exterior se calcula bien | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-15 | Ratio 1.35/2.52 correcto | PASS | R6.T03 + R6Volume · evidence/volume-unit.json; evidence/volume-60-1440.png; evidence/volume-90-blocked-1440.png; evidence/volume-80-equal-1440.png; evidence/volume-252-1440.png; evidence/integrated-76.txt |
| R6-VOL-16 | Bolsa no bloquea por supuestos | PASS | R6.T03 + R6Volume · evidence/neutral-bulto-1440.png; evidence/volume-unit.json; evidence/integrated-76.txt |
| R6-VOL-17 | Saco no bloquea por supuestos | PASS | R6.T03 + R6Volume · evidence/neutral-bulto-1440.png; evidence/volume-unit.json; evidence/integrated-76.txt |
| R6-VOL-18 | Valores inválidos respetan validadores previos | PASS | R6Volume + R4.T02 · evidence/volume-unit.json; evidence/integrated-76.txt |
| R6-VOL-19 | Edición P1 revalida dos tipos | PASS | R6.T04 · evidence/saved-invalid-1440.png; evidence/saved-corrected-1440.png; evidence/integrated-76.txt |
| R6-VOL-20 | Tipo inválido aparece revisar | PASS | R6.T04 · evidence/saved-invalid-1440.png; evidence/saved-corrected-1440.png; evidence/integrated-76.txt |
| R6-VOL-21 | Cambio físico invalida CTA B03 | PASS | R6.T04 · evidence/saved-invalid-1440.png; evidence/saved-corrected-1440.png; evidence/integrated-76.txt |
| R6-VOL-22 | D1 consume V exterior no suma cajas | PASS | R4.T07 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/contracts-75.txt; evidence/regression-published-dto.json |
| R6-VOL-23 | Histórico contradictorio sigue legible | PASS | R6.T07 · evidence/historical-integrity.json; evidence/historical-contradictory-1440.png; evidence/integrated-76.txt |
| R6-VOL-24 | Tolerancia documentada y testeada | PASS | R6Volume / arquitectura · evidence/volume-unit.json; ARCHITECTURE.md |
| R6-P3-01 | Encabezados de columnas misma fila | PASS | R6.T01 · evidence/r6-title-rule-geometry.json; evidence/complete-forms-*.png |
| R6-P3-02 | Descripción larga no desplaza tarjeta | PASS | R6.T01 · evidence/r6-title-rule-geometry.json; evidence/complete-forms-*.png |
| R6-P3-03 | Peso y volumen como restricciones | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/integrated-76.txt; evidence/contracts-75.txt |
| R6-P3-04 | INDIVISIBLE corresponde a orden | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/integrated-76.txt; evidence/contracts-75.txt |
| R6-P3-05 | DISCRETE corresponde a orden | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/integrated-76.txt; evidence/contracts-75.txt |
| R6-P3-06 | Bultos permanecen enteros | PASS | R4.T07,T10 + contratos75 · evidence/regression-d1-and-contract.txt; evidence/integrated-76.txt; evidence/contracts-75.txt |
| R6-P3-07 | No selector dimensión principal visible | PASS | R4.T09 · evidence/regression-dom-audit.json; evidence/integrated-76.txt |
| R6-REVIEW-01 | Regreso Graph abre published pinned | PASS | R6.T05 / R4.T07 · evidence/review-integrity.json; evidence/review-expanded-1440.png; evidence/integrated-76.txt |
| R6-REVIEW-02 | Case conserva model_id | PASS | R6.T05 / R4.T07 · evidence/review-integrity.json; evidence/review-expanded-1440.png; evidence/integrated-76.txt |
| R6-REVIEW-03 | Case conserva version_id | PASS | R6.T05 / R4.T07 · evidence/review-integrity.json; evidence/review-expanded-1440.png; evidence/integrated-76.txt |
| R6-REVIEW-04 | Review no input editable | PASS | R6.T05 / R4.T07 · evidence/review-integrity.json; evidence/review-expanded-1440.png; evidence/integrated-76.txt |
| R6-REVIEW-05 | Review no CTA confirm activo | PASS | R6.T05 / R4.T07 · evidence/review-integrity.json; evidence/review-expanded-1440.png; evidence/integrated-76.txt |
| R6-REVIEW-06 | CTA Review a izquierda de badge | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-07 | Badge Publicado extremo derecha | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-08 | Ancho de ambos idéntico | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-09 | Alto de ambos idéntico | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-10 | Padding de ambos idéntico | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-11 | Border radius idéntico | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-12 | Publicado no click ni botón | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-1440.png; evidence/review-375.png |
| R6-REVIEW-13 | CTA acción funcional real | PASS | R6.T06 · evidence/review-cta-route.json; evidence/review-new-case.json; evidence/final-review-focal.txt; evidence/derived-case-final.txt |
| R6-REVIEW-14 | CTA no muta case actual | PASS | R6.T06 · evidence/review-cta-route.json; evidence/review-new-case.json; evidence/final-review-focal.txt; evidence/derived-case-final.txt |
| R6-REVIEW-15 | No panel gigante vacío | PASS | R6.T05 · evidence/review-1440.png; evidence/review-375.png; evidence/review-expanded-1440.png |
| R6-REVIEW-16 | Dos columnas bien proporcionadas | PASS | R6.T05 · evidence/review-1440.png; evidence/review-375.png; evidence/review-expanded-1440.png |
| R6-REVIEW-17 | Cinco bloques consultables | PASS | R6.T05 · evidence/review-1440.png; evidence/review-375.png; evidence/review-expanded-1440.png |
| R6-REVIEW-18 | Panel resumen metadatos reales | PASS | R6.T05,T07 · evidence/review-1440.png; evidence/historical-integrity.json; evidence/historical-contradictory-1440.png |
| R6-REVIEW-19 | No capacidades de flota falsas | PASS | R6.T05,T07 · evidence/review-1440.png; evidence/historical-integrity.json; evidence/historical-contradictory-1440.png |
| R6-REVIEW-20 | Sin fechas inventadas | PASS | R6.T05,T07 · evidence/review-1440.png; evidence/historical-integrity.json; evidence/historical-contradictory-1440.png |
| R6-REVIEW-21 | Histórico no JSON crudo | PASS | R6.T07 / R4.T08 / R5.T04 · evidence/historical-integrity.json; evidence/regression-legacy-integrity.json; evidence/integrated-76.txt |
| R6-REVIEW-22 | Datos históricos inmutables | PASS | R6.T07 / R4.T08 / R5.T04 · evidence/historical-integrity.json; evidence/regression-legacy-integrity.json; evidence/integrated-76.txt |
| R6-REVIEW-23 | Responsive sin overflow | PASS | R6.T05 · evidence/review-geometry.json; evidence/review-*.png |
| R6-REGRESION-01 | B01 confirm disabled | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-02 | B02 confirm disabled | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-03 | B03 confirm disabled | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-04 | B04 confirm disabled | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-05 | B05 confirm disabled | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-06 | B01 dirty reactivado | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-07 | B02 dirty reactivado | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-08 | B03 dirty reactivado | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-09 | B04 dirty reactivado | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-10 | B05 dirty reactivado | PASS | R4.T03 · evidence/regression-cta-states.json; evidence/integrated-76.txt |
| R6-REGRESION-11 | B04 sin salto B03 | PASS | R3.T01 · evidence/integrated-76.txt |
| R6-REGRESION-12 | B05 sin salto B03 | PASS | R3.T01 · evidence/integrated-76.txt |
| R6-REGRESION-13 | Crear nuevo modelo limpio | PASS | R4.T05,T12 · evidence/integrated-76.txt |
| R6-REGRESION-14 | Borrador preserva productos | PASS | R4.T01,T02,T03 / R6.T04 · evidence/integrated-76.txt; evidence/regression-cta-states.json |
| R6-REGRESION-15 | Borrador preserva firmas válidas | PASS | R4.T01,T02,T03 / R6.T04 · evidence/integrated-76.txt; evidence/regression-cta-states.json |
| R6-REGRESION-16 | No doble save | PASS | R4.T01,T02,T03 / R6.T04 · evidence/integrated-76.txt; evidence/regression-cta-states.json |
| R6-REGRESION-17 | 3 CSV igual contrato | PASS | R4.T07 / contratos75 · evidence/regression-d1-and-contract.txt; evidence/regression-published-dto.json; evidence/contracts-75.txt; evidence/integrated-76.txt |
| R6-REGRESION-18 | D1 pesos 745/665 | PASS | R4.T07 / contratos75 · evidence/regression-d1-and-contract.txt; evidence/regression-published-dto.json; evidence/contracts-75.txt; evidence/integrated-76.txt |
| R6-REGRESION-19 | D1 volumen exterior 1.8 | PASS | R4.T07 / contratos75 · evidence/regression-d1-and-contract.txt; evidence/regression-published-dto.json; evidence/contracts-75.txt; evidence/integrated-76.txt |
| R6-REGRESION-20 | Versionado no reescritura | PASS | R4.T07 / contratos75 · evidence/regression-d1-and-contract.txt; evidence/regression-published-dto.json; evidence/contracts-75.txt; evidence/integrated-76.txt |
| R6-REGRESION-21 | Rollback sin SQL/infrastuctura | PASS | Rollback dry-run · evidence/rollback-dry-run.json; RELEASE_ROLLBACK.md |
| R6-REGRESION-22 | Test teclado/a11y | PASS | R6.T01,T02,T03,T05,T08 / R4.T09 · evidence/review-geometry.json; evidence/addendum-geometry.json; evidence/a11y-*.json; evidence/integrated-76.txt |
| R6-REGRESION-23 | Responsive 375/768/1280/1440 | PASS | R6.T01,T02,T03,T05,T08 / R4.T09 · evidence/review-geometry.json; evidence/addendum-geometry.json; evidence/a11y-*.json; evidence/integrated-76.txt |
