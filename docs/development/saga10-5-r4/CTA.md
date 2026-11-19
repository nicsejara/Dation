# CTA y estados

Los cinco footers usan `confirmFooter` y los mismos tokens: 272×48 px desktop, ancho fluido móvil. Se conserva su label. Confirmado aplica `disabled` nativo, `aria-disabled`, fondo/borde/texto grises y check verde en encabezado; el handler también rechaza invocación programática. Datos relevantes cambian la firma y reactivan el CTA. B04 fuentes invalida B05; B05 no borra B04. B03 depende de catálogo guardado, buffer limpio, restricciones y preview vigente.

B03 validando preview queda disabled/busy. Un error físico conserva datos y permite corregir/reintentar. Errores locales se enfocan únicamente en su bloque. Reintento de preview y publicación conserva sus contratos y controles de generación originales.

Paso2 tiene un único CTA Guardar/Actualizar. No publica. Luego del commit limpia el formulario, agrega/actualiza tarjeta inferior y persiste el draft. Con un guardado y buffer vacío, Guardar queda disabled hasta comenzar otro; con dos, el alta queda bloqueada y las tarjetas permiten editar. Actualizar sin cambios también está disabled. Esto evita que un doble click vuelva a validar/insertar el formulario ya limpio.

Modelo publicado: los cinco CTA, campos y acciones de mutación bloqueados. La revisión histórica no crea controles de edición. La toolbar superior conserva permisos, reset con confirmación y protección de publicación incierta.

Evidencia ejecutable: R4 T02/T03/T05/T06/T09/T12, R3 T01/T05/T09, `evidence/cta-states.json`, `geometry.json`, `dom-audit.json` y capturas de cada bloque.
