# G0 — Inspección localizada y baseline real

Inicio: 19/11/2026 20:36:53 Buenos Aires (23:36:53 UTC). Repositorio nicsejara/Dation, main `2bc0d934350dbef3d303b2a931432c445a04305a`; PR130 y PR131 confirmados merged mediante GitHub. Working tree inicial limpio; rama exclusiva `feat/saga10-5-r6-review-mode` creada desde origin/main. Paquete R6 íntegro: 64 entradas SHA-256 verificadas. R5 conservado como baseline, sin editar sus evidencias.

Inspección: cargo-guided-state/editor/presentation, model-fields-v2, model-historical-view, planning-model, ultimate-case-setup, wizard-ui, journey navigation/targets, estilos compartidos y contratos físicos/DC existentes. No auditoría general ni reimplementación de R4/R5.

Baseline ejecutado sobre main exacto: navegador 2 PASS en 38.523 s (geometría con formularios completos y publicación/3CSV/Case/Graph/retorno×3); contratos backend 75 PASS en 2.523 s. Capturas `before-edit-*` y `before-review-1536.png`. La revisión productiva no se infiere del merge: esta tarea no consulta ni modifica recursos productivos. Se revisó el flujo GitHub existente: autorelease se limita a workflow_run/main; abrir este PR no publica ni despliega. La verificación de revisión/digest productivos pertenece al GO posterior por runbook.

## Hallazgos y decisiones

- CTA real en ultimate-case-setup: `editSource(... forceDerive:true)`, conserva padre y retorna al origen. Se reutiliza ese flujo con confirmación; únicamente su destino inicial pasa a Core01 para seleccionar otra versión. No se inventa ruta ni se cambia el Case existente. Guardas de edición y creación preservadas.
- Modelo publicado: fuente current.model/model_version/case del GET context. El módulo Review no acepta ni consulta draft/sessionStorage ni realiza llamadas de red. No usa el último Model del picker como sustituto.
- Confirmaciones: R4 signatures, compiledKey y cinco CTA se mantienen; la nueva condición volumétrica entra en formErrors/validate y en la proyección de estado de cada tipo, sin keys nuevas persistidas.
- API no distingue una escritura guiada R6 de importaciones/contratos previos. Guardia nueva exclusivamente frontend guiado; no se añade enforcement global que vuelva ilegibles los históricos. El backend sigue siendo el contrato físico previo y no certifica packing. Limitación documentada expresamente.
- El arte R5 era opaco y el panel P1 mostraba soporte vacío/P2 unidad completa. R6 usa transparencia real y tres contextos distintos. La caja vacía candidata tenía una línea ajena en su borde izquierdo: se corrige sólo ese recurso; procedencia y hashes en ASSETS.json.
- La geometría heredada de títulos/badge tenía selectores más específicos. Se detectó por medición y se corrigió con tokens/reglas R6 comunes, sin relajar assertions. Paso3 usa subgrid explícita, no márgenes mágicos.
