# Matriz de aceptación R4 — 74 criterios

Txx = `test_saga10_5_r4.R4Tests.test_xx_*`. Los escenarios R3, Guided y V1 se identifican por suite/número. Evidencias JSON/TXT y capturas en `evidence/`. GAP-01 registra la política conservadora; no se concede co-carga implícita.

| ID | Criterio | Resultado | Evidencia |
|---|---|---|---|
| B03-01 | Exactamente 3 secciones verticales visibles en B03, no 7, sin subacordeones. | PASS | T09 DOM; T07 Graph |
| B03-02 | 5 tarjetas unidad Pallet/Caja/Cajón/Big bag/Otra; ninguna sexta opción perfil. | PASS | T04/T09 cinco radios |
| B03-03 | El formulario físico aparece de inmediato sin clic de agregar unidad. | PASS | T01/T14 formulario inicial |
| B03-04 | El tipo default Pallet está seleccionado, sin dar confirmación verde anticipada. | PASS | T14 estado 0; T03 checks pendientes |
| B03-05 | Nombre/tara/3 dimensiones y unidad de medida están en orden del mockup. | PASS | T14 desktop/mobile; geometry.json |
| B03-06 | Dimensiones representan exterior cargado, no soporte vacío; DTO correcto. | PASS | T01 DTO; state-contract.json |
| B03-07 | 120×100×150 cm = 1.8m³, sin error de conversión con metros. | PASS | T01/T04 cm/m; T07 dry run |
| B03-08 | Tara 25 kg queda en LogisticUnit; no se suma dos veces. | PASS | T01 y dry run 745/665 |
| B03-09 | Ilustración unidad vacía correcta según tipo. | PASS | T04 SVG por tipo; T14 capturas |
| B03-10 | Big bag/Otra admite volumen exterior explícito, sin geometría inventada. | PASS | T04 volumen explícito + errores |
| B03-11 | Cambiar unidad con datos guardados no destruye silenciosamente los tipos. | PASS | T04 confirmar/cancelar unidad e IDs |
| B03-12 | No aparecen Presentación activa / Agregar soporte / Soporte compartido. | PASS | T09 dom-audit.json |
| B03-13 | Primer ingreso: formulario único vacío visible, historial debajo sin tarjetas. | PASS | T14 estado 0 + T01 |
| B03-14 | Producto, bulto, 3 dimensiones, volumen informativo, peso, cantidad: ningún campo comercial anidado. | PASS | T01/T09 DOM; T14 edición |
| B03-15 | Caja vino 30×30×25 = 0.0225m³, peso 12, qty 60. | PASS | T01/T14: 0.0225 m³/12kg/60 |
| B03-16 | Resumen tipo1: 745kg y 1.8m³, dibujo de pallet cargado. | PASS | T01/T14: 745kg/1.8m³ |
| B03-17 | Guardar tipo de carga registra UNA presentación y UN producto, IDs distintos y estables. | PASS | T01 DTO + pure state test |
| B03-18 | Tras guardado válido tipo1 formulario LIMPIO, unidad del Paso1 intacta. | PASS | T01/T14 estado 1 |
| B03-19 | Tarjeta tipo01 aparece DEBAJO del formulario con nombre/60 cajas/745/1.8. | PASS | T01/T09 historyBelow + T14 |
| B03-20 | Se puede llenar segundo en formulario limpio, sin `Agregar segundo` extra. | PASS | T01/T14 sin CTA adicional |
| B03-21 | Aceite 30×20×30 =0.018m³; qty80 mass8; total665kg. | PASS | T01/T14: 0.018/8/80/665 |
| B03-22 | Guardar segundo genera tarjeta tipo02 ABAJO sin duplicar tipo01. | PASS | T01 dos tarjetas e IDs |
| B03-23 | 2 guardados → no tercera alta; formulario limpio inactivo y texto de límite. | PASS | T01/T14 estado 2; pure MAX2 |
| B03-24 | Click en tarjeta tipo01 reabre mismos datos arriba, CTA `Actualizar tipo de carga`. | PASS | T01/T14 estado 3 |
| B03-25 | Actualizar 01 no genera ID nuevo ni modifica 02. | PASS | T01 IDs + segundo íntegro |
| B03-26 | Cambiar formulario con datos sin guardar y seleccionar otra tarjeta no pierde datos sin confirmación. | PASS | T02 diálogo cancel/descartar + reload |
| B03-27 | Guardar inválido muestra errores locales, no crea tarjeta, no limpia formulario. | PASS | T02 errores inline y foco local |
| B03-28 | Doble click rápido en Guardar no crea dos tipos ni dos requests. | PASS | T02 dblclick + sin POST |
| B03-29 | No hay botones de duplicar/eliminar/administrar catálogo en DOM nuevo. | PASS | T09 DOM sin controles DENY |
| B03-30 | Cambiar alto pallet 150→160 actualiza volúmenes de ambos a 1.92m³, pesos intactos. | PASS | T01 dos volúmenes 1.92 |
| B03-31 | Cambiar tara 25→30 actualiza pesos a 750 y 670kg, volúmenes intactos. | PASS | T01 dos pesos 750/670 |
| B03-32 | Peso máximo y Volumen máximo son únicas restricciones visibles y ambas activas inicialmente. | PASS | T09 DOM + T10 restricciones |
| B03-33 | No hay pallets/units como restricción activa oculta en DTO guiado. | PASS | T01/T10 DTO + T07 D1 |
| B03-34 | `primary_dimension` físicamente válida y activa, no selector UI. | PASS | T10 primary volume / T01 weight |
| B03-35 | Copy split: `¿Una orden puede distribuirse en varios viajes?` y tarjetas exactas. | PASS | T09 DOM exacto + T07 |
| B03-36 | `INDIVISIBLE`: orden 10 pallets se asigna completa en un viaje o no servida. | PASS | T07 d1-and-contract.txt: indivisible |
| B03-37 | `DISCRETE`: orden puede repartir 6+4 pallets completos si permiso orden y capacidad. | PASS | T07 d1-and-contract.txt: 6+4 |
| B03-38 | Orden `split_allowed=false` no permite dividir aunque el modelo esté en DISCRETE. | PASS | T07 d1-and-contract.txt: split false |
| B03-39 | Tres bandas informativas exactas; referencia líneas de órdenes correcta. | PASS | T09 tres bandas + T14 |
| B03-40 | Cada presentación tiene un componente; una LogisticUnit compartida; 3 CSV. | PASS | T01/T07 DTO + 3 CSV |
| B03-41 | Compatibilidad D1 con tipos diferentes probada, sin permiso de co-carga inventado. | PASS | T07 matriz real; GAP-01 documentado |
| B03-42 | No se afirma packing 3D ni se deduce qty por división de volúmenes. | PASS | T09/T14 copy + domain probe |
| CTA-01 | B01 CTA confirmado disabled real + gris + check verde. | PASS | T03 bloque 1: disabled/gray/check |
| CTA-02 | B02 CTA confirmado disabled real + gris + check verde. | PASS | T03 bloque 2: disabled/gray/check |
| CTA-03 | B03 CTA confirmado disabled real + gris + check verde. | PASS | T03 bloque 3: disabled/gray/check |
| CTA-04 | B04 CTA confirmado disabled real + gris + check verde. | PASS | T03 bloque 4: disabled/gray/check |
| CTA-05 | B05 CTA confirmado disabled real + gris + check verde. | PASS | T03 bloque 5: disabled/gray/check |
| CTA-06 | Clic reiterado en los cinco no produce handler ni requests. | PASS | T03 dispatch: cero model-review y requests |
| CTA-07 | Cambiar campo B01 reactiva CTA B01 y quita check; reconfirmar re-desactiva. | PASS | T03 editar nombre/reconfirmar |
| CTA-08 | Cambiar rol/consolidación B02 reactiva B02 sin perder datos. | PASS | T03 rol/reconfirmar; Ultimate02 |
| CTA-09 | Guardar/editar tipo o modificar soporte/interno B03 reactiva B03 y quita check. | PASS | T01/T03 unidad + T02 buffer pendiente |
| CTA-10 | Cambiar fuente o categoría B04 reactiva B04; dependencias B05 correctas. | PASS | T03 sources → B04/B05 |
| CTA-11 | Cambiar moneda/tarifa/base B05 reactiva B05; no abre B03. | PASS | T03 moneda conserva B04; R3 T01 |
| CTA-12 | Preview stale B03 no se confirma con respuesta antigua. | PASS | T06 respuesta retenida + dato inválido |
| CTA-13 | Error local sólo altera bloque clicado; no mueve scroll a otro. | PASS | T02/R3 T05/Guided11 |
| CTA-14 | Botones de los 5 footers tienen geometría/tokens consistentes. | PASS | T09 geometry.json cinco anchos |
| CTA-15 | Estado confirmado restaurado sólo con firma vigente de draft. | PASS | T03 reload firma válida + FOREIGN_DRAFT |
| CTA-16 | Confirmado publicado en review no permite edición, clic ni confirmación. | PASS | T01/T07/T12 published locks |
| CTA-17 | CTA local Guardar tipo y global Confirmar B03 son independientes de publicación global. | PASS | T02/T06 cero publicaciones locales; T07 publish único |
| NAV-01 | Crear nuevo desde publicado genera UUID distinto, 0 tipos, 0 checks. | PASS | T12 UUID independiente/0 tipos/0 checks |
| NAV-02 | Crear nuevo no repuebla borrador antiguo tras recargar. | PASS | T05/T11/T12 reload sin residuos |
| NAV-03 | Cancelar descarte conserva borrador antiguo íntegro. | PASS | T05 + R3 T02 igualdad draft |
| NAV-04 | Recuperar draft con 2 tipos muestra listado INFERIOR, no viejo wizard. | PASS | T01 reload + T02 buffer + R3 T03 |
| NAV-05 | Volver desde Graph conserva modelo/version publicado y abre review read-only. | PASS | T07 Case real/Graph → review |
| NAV-06 | Volver/avanzar 3 veces sin recrear IDs ni publicar versiones. | PASS | T07 tres retornos + igualdad API/sin POST |
| NAV-07 | Legacy mixto/continuo/más de dos se lee fiel read-only, sin truncar DTO. | PASS | T08 + Guided02/04/07/09/10/12 |
| NAV-08 | Ninguna nueva ruta de creación/review monta 7 pasos o `editorChoice` viejo. | PASS | T07/T08/T11/T12 DOM cero seven/choice |
| NAV-09 | Ningún control del inventario DENY queda en DOM guiado nuevo. | PASS | T09 dom-audit.json |
| NAV-10 | Responsive 1536/1024/768/390/320 sin textos cortados. | PASS | T09 geometry/a11y 1536/1024/768/390/320 |
| NAV-11 | Teclado y lector de pantalla: radios, checkbox, tarjetas, focus y errores. | PASS | T04 radios teclado + T09 cards Enter/Space/foco/contraste |
| NAV-12 | B04/B05 no abren B03 al elegir recursos/moneda. | PASS | R3 T01 88 acciones + T03 B04/B05 |
| NAV-13 | D1/D2/contratos publicados anteriores pasan regresión necesaria. | PASS | 75 contratos/D1/D2; Saga10 T02/T04 + V1 12 |
| NAV-14 | Publicación incierta no genera versiones duplicadas ni permite reset inseguro. | PASS | T05/R3 T09/V1 T03..T07 idempotencia |
| NAV-15 | No se modificó BD, billing, infraestructura ni tráfico; merge/deploy esperando GO. | PASS | diff y rama: solo frontend/tests/docs; sin merge/deploy |
