# Cambios focales y contratos preservados

## Layout y valores

`cargo-presentation-ui.mjs` aporta un único componente `volumeCard`, marco de arte y título de sección. P1 y P2 comparten `r5-cargo-layout` 60/40, `r5-field-form` y `r5-form-tail`. El volumen ocupa columna 2/fila 1 del mismo tail, abajo a la derecha; en móvil columna 1/fila 2 para ambos. Igual ancho/alto (176 px), padding, radio, borde, icono, tipografía y espacios internos. Resúmenes con igual ancho y padding de 20 px. En responsive apilado la comparación de alineación utiliza el gap respecto al formulario, no la altura absoluta de formularios con diferente cantidad de campos.

`cargo-presentation-values.mjs` sólo formatea valores y convierte la representación cm/m con strings decimales, sin redondeo binario. Cambiar unidad de entrada mantiene longitud/volumen. `volume`, física, tara, cantidades y serialización R4 no se reescriben. Las dos métricas no editables muestran pendiente, nunca cero inventado, sin anuncios aria-live por tecla.

## Arte y mensajes

Diez WebP suministrados, copiados intactos, mapa por tipo/estado y rutas locales versionadas. Marco fijo, object-fit contain, imagen decorativa con texto equivalente, fallback SVG local R4. No se genera imagen en función de cantidad, peso o producto; no certifica packing. Se preservan nodos de imagen entre inputs y se reutilizan tarjetas por ID, evitando requests por tecla y pérdidas de foco.

Guardado progresivo R4 intacto: un soporte, máximo dos tipos homogéneos, upsert con mismos IDs, buffer separado, limpieza y tarjetas inferiores. Mensajes distinguen primer tipo, segundo, edición sin cambios, edición pendiente, cambio de unidad, 2/2 y readonly. Los mensajes de éxito son de borrador, no de motor/publicación. Guardado local síncrono e idempotente; sin sleeps ni esperas artificiales.

## Históricos

`model-historical-view.mjs` muestra nombres, unidades, pesos, cantidades, componentes, reglas, referencias y metadatos disponibles, con textos en español. Fechas disponibles se muestran en Buenos Aires; no se alteran los timestamps originales. Colecciones grandes tienen scroll accesible, sin truncar entidades. Datos ausentes se señalan como no definidos; composiciones mixtas, continuo, >2 tipos, unidades comerciales y políticas previas siguen íntegros.

No hay JSON, YAML ni editor técnico como interfaz habitual. `read()` devuelve copia exacta del snapshot original. Una evaluación de representabilidad incompleta no rompe el render. Un draft histórico no publicable permanece en consulta y no se envía como configuración nueva al compilador. Publicados se consultan por su versión pinneada; ninguna migración/conversión silenciosa.

## Límites conservados

Data Contract: transport_demand + order_lines + transport_resources; líneas por presentation_id/quantity. La unidad se comparte entre dos presentaciones, un componente por presentación. Se mantienen grupos y pares de compatibilidad R4: no co-carga implícita. INDIVISIBLE se aplica a la orden; DISCRETE sólo distribuye unidades completas con permiso por orden. Pesos 745/665 kg, volumen exterior 1.8 m³ y prueba D1 6+4 se validan con el DTO realmente publicado en fixture. Sin cambios D1/D2/SQL/API/infraestructura.
