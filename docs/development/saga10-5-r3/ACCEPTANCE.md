# Aceptación R3 — 35 criterios

R3-NN identifica test_saga10_5_r3.R3Tests.test_NN; Ultimate es la suite física/visual revalidada. CI se cierra en el PR al SHA terminal real, sin predeclarar verde en un commit.

| ID | Criterio | Estado | Evidencia |
|---|---|---|---|
| R3-001 | Copy superior no redundante, dos CTA equivalentes, ningún botón «Cambiar modelo» duplicado. | PASS | R3-08: header copy/DOM + geometry |
| R3-002 | Crear nuevo desde draft confirmado limpia nombre, descripción, todos checks, catálogo, previews, UUID. | PASS | R3-02: UUID, empty data/reviews and refresh |
| R3-003 | Crear nuevo desde un publicado no carga configuración anterior ni muta publicado. | PASS | R3-07: new empty model; published API unchanged |
| R3-004 | Cancelar confirmación de descarte mantiene exactamente estado anterior. | PASS | R3-02/04: cancel snapshot/checkpoint exact |
| R3-005 | Pending intent de publicación conserva idempotencia y no permite reset peligroso. | PASS | R3-09 + V1 lost-ACK/CAS regressions |
| R3-006 | Refresh después de reset no restaura datos históricos del draft que se quiso descartar. | PASS | R3-02 reload retains fresh UUID |
| R3-007 | B01 ayuda contextual antes de input, ejemplo del nombre, label/subrayado, errores abajo. | PASS | R3-08 exact DOM order/help/aria |
| R3-008 | B02 DIRECT se expresa sólo como banda informativa, carga fija igual en payload. | PASS | R3-08 DIRECT note; Ultimate02 payload |
| R3-009 | Click OWN/EXTERNAL no expande B03 ni navega ni reubica foco. | PASS | R3-01: new/recovered desktop/mobile, open/focus |
| R3-010 | Click cinco categorías B04 mantiene usuario en B04 y estado correcto. | PASS | R3-01 five categories; geometry |
| R3-011 | Click ARS/USD/EUR mantiene usuario en B05, sin abrir B03. | PASS | R3-01 USD/EUR/ARS; same accordion |
| R3-012 | Click tarifas/base B05 no abre B03; condicionales funcionan. | PASS | R3-01 costs/bases; Ultimate02 conditionals |
| R3-013 | CTA local inválido sólo muestra errores de su bloque. | PASS | R3-05: B04/B05 local errors and focus |
| R3-014 | CTA global inválido sí guía al error intencionalmente sin POST de publicación. | PASS | R3-05: disabled UI + dispatched click exercises global guard without POST |
| R3-015 | `input`/`change` no repiten validaciones con efectos secundarios; mantener preview/firma. | PASS | R3-01; snapshot dedupe + Ultimate06 stale/requests |
| R3-016 | B05 OWN cambia tarjeta con candado a banda info condicional, método inalterado. | PASS | R3-08 OWN note; Ultimate02 sources/DTO |
| R3-017 | B03 nuevo guiado presenta EXACTAMENTE tres pasos y seis perfiles en Paso1. | PASS | R3-03/08: 3 steps,6 profiles,0 legacy steps |
| R3-018 | B03 muestra perfil y unidad física cargada en Paso1, una sola cadena mental. | PASS | R3-06 profiles/type identity and persistence |
| R3-019 | B03 paso1 nota contextual en banda informativa. | PASS | R3-06 dynamic note; screenshots |
| R3-020 | B03 paso2 no tiene sobres/displays/unidades comerciales extras ni mezclas en presentación nueva. | PASS | Ultimate01/04/07 and guided catalog renderer |
| R3-021 | B03 peso 665kg y volumen exterior 1.8m³ con input físico demo, sin afirmar packing. | PASS | Ultimate01 DTO+compiler+D1 finite;70contracts |
| R3-022 | B03 dibujos vacía/cargada por tipo PALLET y caso BIG_BAG, OTHER. | PASS | Ultimate03 types/art; actual-B03 |
| R3-023 | B03 paso3 peso/volumen, split correcto, sin primary selector visible, sin pallets ocultos. | PASS | Ultimate01/07 + R3-06: active primary,no hiddenpallets |
| R3-024 | B03 sólo un CTA local final y ningún Volver/Continuar internos en ruta guiada. | PASS | R3-08/Ultimate01: single local footer |
| R3-025 | Recuperación de draft discreto representable abre 3 pasos sin exigir `edition=ultimate` previo. | PASS | R3-03: absent/compatible markers, exact DTO identity |
| R3-026 | Direct/mixed/continuous/legado no se altera; editor compatible explicitado, no fallback silencioso. | PASS | R3-04 + Ultimate08 + guided07 legacy bulk |
| R3-027 | Dos presentaciones homogéneas y catálogo compartido conservan referencias e IDs. | PASS | Ultimate04 + R3-06 IDs + guided10 |
| R3-028 | B04/B05, B01/B02 sin regresiones de opciones/condicionales/DTO. | PASS | Ultimate02; R3-01/05 |
| R3-029 | Cinco CTA finales comparten geometría, alineación, icono y estado validado efectivo. | PASS | R3-08 geometry5widths, shared helper |
| R3-030 | Modelos publicados v1/v2 y Data Contract 2/3 CSV conservan semántica. | PASS | Saga10 wizard02/03/04 + V1 12 regressions |
| R3-031 | No cambios SQL, backend, D1/D2 ni borrados de producción sin GAP y autorización. | PASS | Scoped diff frontend/tests/docs; no product backend change |
| R3-032 | Imágenes reales antes/después a 1536,1024,768,390,320; focus, scroll y accesibilidad comprobados. | PASS | VISUALS.md, geometry/a11y/navigation JSON |
| R3-033 | FAST y required-gate al SHA exacto, FULL si la política lo exige; sin trucar classifier. | TRACKED_IN_PR | Exact-SHA FAST/required-gate recorded in PR after completion |
| R3-034 | Único PR, sin merge, despliegue ni tráfico; rollback descrito. | PASS | Single PR open, no deployment; RELEASE.md |
| R3-035 | Blueprint review-only futuro incluido como documento; no nueva ruta/feature ahora. | PASS | FUTURE_REVIEW_ONLY.md; router unchanged |
