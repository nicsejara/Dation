# Evidencia visual real

Capturas del navegador con API y base de pruebas aisladas. Sin mockups generados ni retoques. La interacción, cálculos y persistencia pertenecen al runtime real de pruebas.

- [Desktop: edición del tipo 01](evidence/progressive-3-editing-1536.png)
- [Móvil: dos tipos guardados / formulario limpio](evidence/progressive-2-full-390.png)
- [Nuevo / cero tipos](evidence/progressive-0-empty-1536.png)
- [Primer guardado](evidence/progressive-1-saved-1536.png)
- [B03 confirmado](evidence/actual-B03-1536.png)
- [B01 confirmado](evidence/actual-B01-1536.png) · [B02](evidence/actual-B02-1536.png) · [B04](evidence/actual-B04-1536.png) · [B05](evidence/actual-B05-1536.png)
- [Vuelta desde Graph: publicado readonly](evidence/published-review-return-2.png)
- [Histórico continuo íntegro](evidence/legacy-readonly-2.png)
- [Comparador R3 antes](evidence/baseline-r3.png)

La serie `actual-B0{1..5}-{1536,1024,768,390,320}.png` contiene 25 capturas. `progressive-{0-empty,1-saved,2-full,3-editing}-{1536,390}.png` contiene ocho estados del flujo. Las dos imágenes aprobadas del paquete guían estilo; su selector superior queda sustituido por historial inferior según la excepción R4. No se replican los textos históricos de fraccionamiento por pallet ni los seis perfiles.

`geometry.json` registra overflow, ubicación inferior, cinco footers iguales y cinco radios en fila desktop. `a11y.json` verifica contraste/overflow en cinco anchos. `dom-audit.json` registra controles DENY ausentes. Los máximos históricos se muestran en regiones con scroll accesible, sin truncar su JSON ni producir páginas ilimitadas.
