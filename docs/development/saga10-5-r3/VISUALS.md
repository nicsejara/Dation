# Comparación visual real

R3 mantiene la paleta/shell de Dation. Texto R3 prevalece: seis perfiles en Paso1, DIRECT/OWN en bandas, ayudas antes del control, dos CTA superiores y reset real. Imágenes de mockups no son evidencia de ejecución.

| Bloque / ancho | Antes (baseline) | Después (R3) |
|---|---|---|
| B01 · 1536px | [PNG](../saga10-5-r2/evidence/actual-B01-1536.png) | [PNG](evidence/actual-B01-1536.png) |
| B01 · 1024px | [PNG](evidence/baseline/before-B01-1024.png) | [PNG](evidence/actual-B01-1024.png) |
| B01 · 768px | [PNG](evidence/baseline/before-B01-768.png) | [PNG](evidence/actual-B01-768.png) |
| B01 · 390px | [PNG](../saga10-5-r2/evidence/actual-B01-390.png) | [PNG](evidence/actual-B01-390.png) |
| B01 · 320px | [PNG](../saga10-5-r2/evidence/actual-B01-320.png) | [PNG](evidence/actual-B01-320.png) |
| B02 · 1536px | [PNG](../saga10-5-r2/evidence/actual-B02-1536.png) | [PNG](evidence/actual-B02-1536.png) |
| B02 · 1024px | [PNG](evidence/baseline/before-B02-1024.png) | [PNG](evidence/actual-B02-1024.png) |
| B02 · 768px | [PNG](evidence/baseline/before-B02-768.png) | [PNG](evidence/actual-B02-768.png) |
| B02 · 390px | [PNG](../saga10-5-r2/evidence/actual-B02-390.png) | [PNG](evidence/actual-B02-390.png) |
| B02 · 320px | [PNG](../saga10-5-r2/evidence/actual-B02-320.png) | [PNG](evidence/actual-B02-320.png) |
| B03 · 1536px | [PNG](../saga10-5-r2/evidence/actual-B03-1536.png) | [PNG](evidence/actual-B03-1536.png) |
| B03 · 1024px | [PNG](evidence/baseline/before-B03-1024.png) | [PNG](evidence/actual-B03-1024.png) |
| B03 · 768px | [PNG](evidence/baseline/before-B03-768.png) | [PNG](evidence/actual-B03-768.png) |
| B03 · 390px | [PNG](../saga10-5-r2/evidence/actual-B03-390.png) | [PNG](evidence/actual-B03-390.png) |
| B03 · 320px | [PNG](../saga10-5-r2/evidence/actual-B03-320.png) | [PNG](evidence/actual-B03-320.png) |
| B04 · 1536px | [PNG](../saga10-5-r2/evidence/actual-B04-1536.png) | [PNG](evidence/actual-B04-1536.png) |
| B04 · 1024px | [PNG](evidence/baseline/before-B04-1024.png) | [PNG](evidence/actual-B04-1024.png) |
| B04 · 768px | [PNG](evidence/baseline/before-B04-768.png) | [PNG](evidence/actual-B04-768.png) |
| B04 · 390px | [PNG](../saga10-5-r2/evidence/actual-B04-390.png) | [PNG](evidence/actual-B04-390.png) |
| B04 · 320px | [PNG](../saga10-5-r2/evidence/actual-B04-320.png) | [PNG](evidence/actual-B04-320.png) |
| B05 · 1536px | [PNG](../saga10-5-r2/evidence/actual-B05-1536.png) | [PNG](evidence/actual-B05-1536.png) |
| B05 · 1024px | [PNG](evidence/baseline/before-B05-1024.png) | [PNG](evidence/actual-B05-1024.png) |
| B05 · 768px | [PNG](evidence/baseline/before-B05-768.png) | [PNG](evidence/actual-B05-768.png) |
| B05 · 390px | [PNG](../saga10-5-r2/evidence/actual-B05-390.png) | [PNG](evidence/actual-B05-390.png) |
| B05 · 320px | [PNG](../saga10-5-r2/evidence/actual-B05-320.png) | [PNG](evidence/actual-B05-320.png) |

Los15 PNG anteriores de R2 ya integrados son capturas reales del árbol idéntico al baseline de main (git diff1a1e39e/ad3f538 vacío). Se capturaron10 adicionales en1024/768 usando ese mismo código/fixture local, sin editarlo. No se simuló producción.

[Elección explícita](evidence/explicit-choice.png) · [Editor compatible voluntario](evidence/explicit-compatible.png). Las trazas G0 y capturas before/after de sources/currency documentan además el salto reproducido y su corrección; navigation.json contiene88 interacciones verificadas con nuevo y recuperado, desktop/mobile.

Evidencia complementaria: [geometría](evidence/geometry.json), [contraste](evidence/a11y.json), [CTA](evidence/cta-audit.json).

[Baseline: borrador homogéneo recuperado cae a siete pasos](evidence/baseline/before-recovered-seven.png) frente a [R3: elección explícita](evidence/explicit-choice.png) y [R3: tres pasos](evidence/actual-B03-1536.png). Captura local con edition=compatible y DTO homogéneo, no atribuida a una sesión productiva.
