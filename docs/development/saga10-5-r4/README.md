# Saga 10.5 R4 — Cargo Configuration Ultimate Pro y CTA global

Implementación frontend completa desde `797f9fc49b497fb6d266621926cdffbe03640e77` (PR #129 integrado). Un solo PR de revisión; **sin merge ni despliegue**. Paquete rector SHA-256: `41390eaeae1ea2f9929e9219db1f762c3c5eb34b5eb13591dfc3205c4a96724f`.

## Gates

| Gate | Resultado | Evidencia |
|---|---|---|
| G0 | PASS | [Baseline, CI y reproducción](G0.md) |
| G1 | PASS | `test_cargo_guided_state`, state-contract.json, backend normalization |
| G2 | PASS | R4 T01/T04/T09/T14: cinco unidades, física compartida |
| G3 | PASS | R4 T01/T02/T14: guardado progresivo, máximo dos, edición con mismos IDs |
| G4 | PASS | R4 T07: DTO real publicado → 3 CSV → D1; [GAP-01 conservador](ARCHITECTURE.md) |
| G5 | PASS | R4 T03/T05/T06/T07/T11/T12, R3 T01/T05/T09 |
| G6 | PASS local | [74 criterios](ACCEPTANCE.md), [capturas](VISUALS.md), pruebas detalladas debajo |
| G7 | PR preparado | PR/HEAD y resultado CI terminal registrados en la descripción del PR |

## Cambios y propósito

- `cargo-guided-state.mjs` y `cargo-guided-editor.mjs`: una unidad compartida, buffer separado del catálogo guardado, dos tipos homogéneos como máximo, historial inferior, validación local y serialización con IDs estables.
- `model-fields-v2.mjs`: renderer definitivo de tres pasos y consulta fiel de históricos incompatibles; cinco confirmaciones realmente disabled/grises con checks verdes y firmas por bloque.
- `planning-model.mjs`: persistencia/reset del buffer y preview invalidado por cambios de configuración; mantiene CAS, permisos e idempotencia.
- `ultimate-case-setup.mjs`: vuelve desde Graph al visor V2 pinneado readonly; conserva ruta V1 y contratos del Case.
- `guided-ui.mjs` y CSS scoped: gráficos vacío/cargado por tipo, geometría responsive, cards inferiores, gris confirmado y lector histórico con scroll accesible.
- Pruebas browser, helper público, probe local de dominio y documentación/evidencias. Sin backend, SQL, Supabase, infra ni workflows.

## Validación real

- Baseline: 70 contratos GREEN (1.524 s); reproducción de cinco CTA habilitados y controles sobrantes.
- Regresión inicial de 46 casos: 44 PASS; dos incidencias focales corregidas. El lector de máximo histórico necesitaba una región con scroll para no exceder el límite de screenshot; el fixture de masa declarada todavía incluía componentes con masa y el backend elegía correctamente esa procedencia. No se cambió física ni se relajó la assertion de procedencia.
- Verificación final: 27 browser PASS (148.557 s): 13 R4, dos correcciones focales y 12 del wizard V1. Tres comprobaciones adicionales de firmas/teclado/gráficos/capturas PASS (28.540 s), más captura final de ocho estados PASS (18.158 s).
- 70 contratos originales PASS (1.604 s); cinco regresiones D2/consumidores PASS (0.504 s); siete pruebas del clasificador PASS. Test puro Node/Python de estado/mapeo PASS, incluidos IDs inconsistentes fail-closed.
- Revisión final de copy readonly: dos E2E PASS (28.766 s), con tres regresos desde Graph y publicación incierta. La vista bloqueada no promete actualizar tarjetas.
- Los escenarios anteriores se ejecutan también mediante helpers compartidos; no representan necesariamente cobertura distinta. [Migración de pruebas](TEST_MIGRATION.md).
- Rollback inverso y reaplicación PASS en worktree temporal: ambos árboles coinciden exactamente; evidencia `rollback-dry-run.txt`.
- CI obligatoria: clasificación real R2, FAST requerido, FULL no requerido. Clasificación completa en `classification.json`. Estado CI terminal y FAST/FULL/required-gate terminal en el PR. No se altera el clasificador ni se omiten gates para reducir pruebas.

## Límites explícitos

La nueva UI no permite borrar tipos guardados ni editar compatibilidad entre tipos. La política conservadora no autoriza co-carga implícita: [decisión y matriz D1](ARCHITECTURE.md). Contratos históricos no representables se conservan completos en lectura. No hay packing 3D ni edición de versiones publicadas.

[CTA y estados](CTA.md) · [Activación/rollback](RELEASE.md) · [Matriz CSV](ACCEPTANCE.csv). El reporte final del PR identifica HEAD validado, duración real hasta CI y controles terminales.
