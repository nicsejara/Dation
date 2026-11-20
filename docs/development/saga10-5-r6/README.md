# SAGA 10.5 R6 — Ultimate Final Refinement & Review Mode

Baseline main `2bc0d934350dbef3d303b2a931432c445a04305a` (PR130/131 merged). Rama exclusiva `feat/saga10-5-r6-review-mode`. Inicio 19/11/2026 20:36:53 Buenos Aires. SHA candidato, PR, resultado terminal y tiempo GitHub se registran en el reporte del PR para evitar un commit adicional sólo para insertar su propio SHA.

## Implementación

1. **Arte por contexto:** selector vacío; P1 unidad cargada; P2 caja individual o icono neutral explícito; historial unidad cargada. Once ilustraciones transparentes con WebP→PNG→SVG, sin fondo radial, halos ni requests por tecla. Una caja candidata se limpió tras QA, sin rediseñar el resto.
2. **Geometría:** títulos y ayudas uniformes; tarjetas de volumen R5 compartidas,176px de alto, abajo a la derecha; resúmenes equivalentes; Paso3 con filas subgrid para alinear títulos/ayudas/tarjetas.
3. **Tipos:** contador total «1 tipo registrado»/«2 tipos registrados», tarjetas con miniatura y estado, misma transacción progresiva R4 y máximo dos tipos homogéneos. IDs, edición, doble click, buffers y confirmaciones conservados.
4. **Volumen:** comparación exacta decimal con banda relativa1e-12; error específico para cajas rígidas excedidas, igualdad advertida, flexibles orientativos. Reevaluación de ambos tipos con cambio P1, sin borrar ni reconfirmar. No packing ni sustitución del volumen D1.
5. **Review:** datos exclusivamente del Model/Version/Case publicados del servidor; cinco secciones humanas, metadatos y vinculación reales, sin inputs/confirmaciones/JSON o panel vacío. Cabecera común CTA izquierdo y Publicado derecho, mismas dimensiones/estilos, indicador no interactivo.
6. **Navegación:** CTA reutiliza forceDerive y confirmaciones vigentes, abre Core01, selecciona otra versión y crea otro Case. E2E comprueba padre/version intactos. Review no resucita new_model. Históricos V1/V2 con la UI Saga10 habilitada se consultan sin inventar catálogo; vistas fuera de Unified Journey/feature flag conservan sus rutas existentes.

## Gates G0–G7

| Gate | Evidencia |
|---|---|
| G0 | [Baseline, handler real y contratos](G0_AUDIT.md); dos casos browser y75 backend baseline PASS |
| G1 | [Assets/procedencia](ASSETS.md), [claro/oscuro](evidence/asset-light-dark-qa.png), alfa real, once variantes y fallback |
| G2 | [Geometría](evidence/addendum-geometry.json), [títulos](evidence/r6-title-rule-geometry.json), capturas cuatro viewports |
| G3 | Fronteras y fixtures A–D, atomicidad y dos tipos: [unidad](evidence/volume-unit.json), R6.T03/T04 |
| G4 | [Subgrid medido](evidence/r6-title-rule-geometry.json), texto multilínea, sin márgenes artificiales |
| G5 | [Review/CTA](evidence/review-geometry.json), [inmutabilidad](evidence/review-integrity.json), [nuevo Case](evidence/review-new-case.json), históricos V1/V2 |
| G6 | Regresión integrada76 y cierres focales documentados abajo;75 contratos/domain; estado/unidades y a11y |
| G7 | Matriz132, evidencias y rollback local PASS; resultado final de CI/PR/SHA verificado en el reporte del PR. No merge/deploy |

## Resultados reales de pruebas

- Baseline: browser **2 PASS,38.523s**; contratos **75 PASS,2.523s**.
- Integrada sobre R6: **76 casos,75 PASS y una expectativa visual R4 pendiente de actualizar**. El aviso de solo lectura se trasladó del Paso2 a la cabecera de la consulta histórica. Se corrigió exclusivamente el alcance del locator, conservando texto, ausencia de edición y comparaciones íntegras de API/IDs. Log original conservado.
- Cierre focal final de layout/arte/Review/históricos/R4.T07: cinco PASS; el sexto test ampliado de otro Case se detuvo ante la confirmación existente de cambio de Model Version. Se agregó su interacción explícita con el label real, sin sleeps ni omitir la confirmación. **R6.T06 final PASS,21.766s**, con nuevo Case realmente creado y padre intacto.
- R4.T07 corregida PASS: publicación real en fixture, tres CSV, Case/Graph/retorno×3, snapshot íntegro y prueba D1 usando exactamente el DTO publicado. Pesos745/665kg, exterior1,8m³, orden indivisible, discreta6+4 y co-load explícito conservados.
- Cierre de históricos/Review V1/V2: R6.T09/T05/T07 **3 PASS,26.851s**, resultado en `evidence/legacy-review-final.txt`.
- Domain/contratos/backend de regresión **75 PASS,2.357s**: frontend_contract, saga10_data_contracts, saga10_domain_physical, saga10_assignment, saga10_scheduling y saga10_result_consumers.
- R6Volume **1 PASS,0.074s**: fixtures, precisión/fronteras, flexibles, inválidos, buffer atómico, máximo2 y IDs. Estado/unidades R4/R5 **2 PASS** en la integrada. Clasificador **7 PASS**.
- Navegador:1440/1280/768/375 y320 adicional; contraste/overflow, teclado, foco, reduced-motion, roles/errores y PNG/WebP fallidos. Geometría CTA Review240×48 desktop y ancho disponible×64 móvil, idéntica entre ambos elementos.
- Clasificador real del candidato determina FAST/FULL. No se modifica política, workflows, skips, permisos o cobertura para forzar un resultado. CI terminal enlazada en el PR.

Los primeros fallos reales de CSS (título12px heredado y badge180px heredado) se corrigieron con selectores/tokens compartidos. Se conservaron las mediciones estrictas. Las expectativas de arte/contador/readonly de R4/R5 se actualizan a la semántica R6; assertions de contratos y seguridad intactas. No se presenta ninguna ejecución fallida como verde ni se suman reejecuciones para inflar cobertura.

## Riesgos y límites

- La nueva condición volumétrica pertenece al flujo guiado frontend. No hay identificador de escritura R6 en el contrato API para aplicarla globalmente sin afectar históricos/clientes previos. El servidor mantiene su contrato físico anterior; no se afirma enforcement backend ni certificado de packing.
- El picker Saga10 existente selecciona la última versión publicada del Model elegido. Se conserva ese contrato; no se agrega un selector técnico ni administración de catálogo. Los Cases anteriores continúan fijados a su versión.
- Los checks de Review indican sección de un contrato publicado en consulta; no reconstruyen ni certifican pasos de un wizard histórico. Ausencia de información se expresa sin inventar fechas, capacidades de flota, densidad o packing.
- Nuevos módulos/imports requieren revisión explícita de release; no se amplía la allowlist G6 ni se activa CD. La revisión/digest productivos no se infieren de main ni se verifican mediante mutaciones en esta tarea.
- Arte estático; tiempos y red medidos en fixture local, no SLA Cloud Run. No dependencias nuevas, procesos residentes, APIs de terceros o cambios de escala.

## Archivos y entrega

Cambios runtime: cargo-guided-editor (presentación/guía), cargo-guided-state (guardia local), cargo-volume-coherence nuevo (comparación pura), cargo-presentation-ui (mapa/fallback/token), model-fields-v2 (subgrid), model-published-review nuevo, model-historical-view (proyección V1), ultimate-case-setup (Review/CTA), CSS scoped y22 archivos de assets. Sin cambios backend, SQL, Supabase, motores, flags, infraestructura o workflows.

[132 criterios](ACCEPTANCE.md) · [CSV](ACCEPTANCE_132.csv) · [Capturas](VISUALS.md) · [Arquitectura](ARCHITECTURE.md) · [Assets/SHA](ASSETS.json) · [Activación/rollback](RELEASE_ROLLBACK.md). Los PNG de navegador se conservan originales. Pruebas exclusivamente con SQL/API/datos sintéticos propios; no se accede a datos históricos productivos.

**Entrega restringida: PR abierto, NOT_MERGED, NOT_DEPLOYED.** No imágenes Docker publicadas, tráfico, Jobs, Scheduler, Billing, motores o migraciones productivas.

Higiene de evidencia: los logs conservan su salida textual; sólo se normalizan espacios finales de línea. Los PNG de navegador no se modifican. SHA-256 de los archivos entregados en evidence/SHA256SUMS.
