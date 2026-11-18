# CI — Saga10 / PR126

Los checks terminales del HEAD vigente se informan en GitHub, sin atribuir a un commit nuevo el resultado de otro SHA. Un run pendiente o fallido impide declarar CI_GREEN.

| Run | Candidato | Resultado / acción |
|---|---|---|
|44238035433|f5a68b36|impact/FAST success; FULL cancelado al cerrar la presentación de errores físicos del preview v2 |
|44238718559|d791b0fd|impact/FAST success; FULL y required-gate failure: una expectativa obsoleta de copy, 779/780 pruebas Python aprobadas |

## Causa del fallo44238718559

`test_frontend_contract.FrontendContractTests.test_dda_logistics_landing_contract` esperaba el eyebrow anterior «DDA LOGÍSTICA · PLANIFICACIÓN DE DESPACHOS» y una frase anterior del hero. La landing de UX08 ya usa «DDA LOGÍSTICA» y «Configurá tus despachos, compará alternativas y revisá resultados antes de aprobar.».

Clasificación: **test obsoleto preexistente**, no regresión de Saga10. El test y el template del candidato eran byte a byte idénticos al baseline main `f7fb4be3aa750b1c609a3579fd35e9180b40a9c9`:

- test: SHA256 `17d52ad401d7828485a390b7f9cc5a17285a3cb20c33086684b14eba27eb7269`.
- template: SHA256 `01586772779bc76114bf953a0e02edfaa6f7c6e49ef23f7f14bbb83c0930677f`.

Se ejecutó además el método original obtenido de ese commit, con el HTML original, y se confirmó el mismo fallo. No se cambió el HTML de la landing. Se actualizaron sólo las dos expectativas literales, exigiendo además el span de eyebrow exacto. Permanecen los controles de CTA, orden de pasos, acciones, mapa, archivos mínimos, FAQ y elementos prohibidos.

Validación focal posterior: `python -m unittest -v tests.test_frontend_contract` desde backend, **29 PASS**, 0,017s. No se deshabilitaron ni omitieron tests, no se cambió el clasificador, no se alteraron workflows. Se requiere nueva CI automática completa sobre el commit que incorpora esta corrección, manteniendo el mismo PR abierto y sin merge/deploy.
