# SAGA 10.5 R5 — Premium UX, 3D Assets & Stability

Implementación focal frontend desde main `9f466b505ee2b852a5c83e240b6871778c81a380` (PR130 fusionado), rama `feat/saga10-5-r5-premium-ux`. Inicio 19/11/2026 18:15:05 Buenos Aires. SHA candidato, PR y tiempos terminales GitHub se registran en el reporte del PR para evitar un commit adicional sólo para insertar su propio SHA.

## Alcance

1. P1/P2: títulos y ayudas previos a controles, divisor limpio, métricas premium compartidas. Addendum con layout idéntico y volumen inferior derecho aplicado prioritariamente.
2. Diez WebP originales vacíos/cargados, selección por cinco tipos, miniaturas y fallback local. 69,156 bytes; sin recursos externos ni requests por tecla.
3. Resúmenes estables, peso bruto destacado, historial inferior y mensajes progresivos de primer guardado/segundo/edición/2 de 2.
4. Cinco CTA R4 conservados: disabled real/check tras confirmar, invalidación por firma y preview vigente.
5. Consulta histórica humana, incompletos explícitos, snapshots íntegros, sin JSON normal ni conversión/escritura. Se evita preview de un draft histórico no editable.
6. Corrección demostrada del selector existente cm/m para conservar magnitud, con desplazamiento decimal exacto; no cambia ninguna fórmula física ni DTO.

## Gates

| Gate | Resultado verificable |
|---|---|
| G0 baseline | PASS: PR130/main, paquete53, navegador baseline y contratos75; [G0](G0.md) |
| G1 titulares/metricas | PASS: componente/clases comunes y captura/rectángulos R5.T01 |
| G2 arte | PASS: cinco tipos × dos estados, miniaturas, zero requests/input y fallback R5.T02/T05 |
| G3 layout | PASS: [8 controles addendum](ADDENDUM_GEOMETRY.md) en cuatro viewports |
| G4 progresivo | PASS: R5.T03 y R4.T01/T02, IDs/upsert/máximo2 sin catálogo nuevo |
| G5 estabilidad/histórico/CTA | PASS: R3.T01, R4.T03/T05/T07/T08/T11/T12, R5.T04/T05 |
| G6 regresión | PASS local: suite integrada65 corregida focalmente, contratos75 y estado/unidades2; detalle abajo |
| G7 entrega | Documentación, matriz110+8, capturas y rollback preparados. Estado final de PR/CI/SHA se comprueba y registra en el PR; merge/deploy excluidos |

## Pruebas ejecutadas

- Baseline real navegador: 1 PASS, 16.311 s; backend 75 PASS, 2.453 s.
- Integrada navegador: **65 ejecutadas, 64 PASS y una expectativa visual anterior** (`MIXED` en vez del texto humano «Operación mixta»). Log íntegro conservado. Se actualiza esa expectativa exclusivamente; igualdad exacta de payload y códigos originales intacta.
- Cierre focal: **7 PASS, 60.778 s**: seis R5 y Guided.T03 corregida. No quedan fallos de esa suite sin resolver.
- Metadatos/histórico final: R5.T04 **PASS, 17.087 s**; hora Buenos Aires explícita en formato24h, versión/timestamp conservados, payload exacto, XSS como texto, cero preview POST.
- Pendiente/tara/unidades y guardado final: R5.T03/T06: **2 PASS, 21.279 s**, resultado en `evidence/pending-tare-2.txt` (cero sólo cuando se ingresa explícitamente).
- Backend/compatibilidad: **75 PASS, 2.288 s** (`test_frontend_contract`, `test_saga10_data_contracts`, `test_saga10_domain_physical`, `test_saga10_assignment`, `test_saga10_scheduling`, `test_saga10_result_consumers`).
- Estado puro y unidades: **2 PASS, 0.113 s**; clasificador **7 PASS**. Sin modificación de impacto, workflows, skips o assertions de negocio.
- Regresión publicada R4.T07: tres CSV reales, Case/Graph/retorno ×3 y snapshot API íntegro. Prueba D1 aislada usando DTO realmente publicado: 745/665 kg, 1,8 m³, orden indivisible, discreta6+4, split_allowed=false y compatibilidad explícita. No se activan motores productivos.

Los primeros fallos y sus correcciones se conservan en los logs, sin presentarlos como ejecuciones verdes. El primer contraste de geometría responsive se corrigió para comparar gaps equivalentes, manteniendo todas las igualdades de ancho/alto/estilo/posición. El fallo real heredado cm/m se corrigió en representación; no se introdujeron sleeps ni retries.

## Riesgo y limitaciones

Cambios frontend R2 según clasificador vigente (confirmar diff del SHA en CI). Sin backend, SQL, motores, flags, Supabase, infraestructura ni políticas CI. El formato humano es una proyección, no un editor histórico. Contratos no representables conservan todos sus datos en consulta; no se fuerza conversión al límite de dos. Un co-load no autorizado sigue siendo conservador. Arte estático decorativo: no afirma packing real. Mediciones de red locales, no SLA productivo. Nuevos módulos/imports requieren la revisión explícita normal de release; no se altera la política G6 para admitirlos automáticamente.

## Archivos y evidencia

- `cargo-guided-editor.mjs`: presentación, guía e historial estables sobre el estado R4 sin cambios.
- `cargo-presentation-ui.mjs`: componente compartido métrica/arte/título.
- `cargo-presentation-values.mjs`: formato y conversión de representación exacta.
- `model-historical-view.mjs`: lectura humana sin transformación del snapshot.
- `model-fields-v2.mjs`, `planning-model.mjs`: copy y selección/guard de histórico.
- `ultimate-foundation.css`: geometría/arte/tipografía scoped a R5.
- Diez WebP originales, tests R5/estado y tres expectativas visuales actualizadas.

[Arquitectura](ARCHITECTURE.md) · [Assets y SHA](ASSETS.md) · [Matriz110](ACCEPTANCE.md) · [CSV](ACCEPTANCE_110.csv) · [Addendum8](ADDENDUM_GEOMETRY.md) · [Capturas](VISUALS.md) · [Activación/rollback](RELEASE_ROLLBACK.md).

Entrega restringida a código y PR abierto. Sin merge, imágenes Docker publicadas, deploy, tráfico, ejecución de Jobs, activación de motores o escrituras históricas/productivas.
