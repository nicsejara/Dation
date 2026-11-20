# Arte R6, procedencia y QA

Diez unidades isométricas (5×empty/loaded) y caja individual del paquete del usuario. Veinte de22 archivos PNG/WebP se conservan byte por byte. Una única ilustración (caja vacía) se editó con ImageGen para retirar una línea separada del objeto en el borde izquierdo; el primer resultado se rechazó por transparencia insuficiente. El segundo se normalizó para distribución web300×335 con ImageMagick y WebP calidad85. No hubo cambios creativos en otros objetos. Fuentes, tamaños y SHA en ASSETS.json.

- WebP principal: **213,428 bytes** para once URLs únicas.
- PNG fallback: **830,807 bytes**, descargados únicamente si falla el WebP.
- Total almacenado runtime: **1,044,235 bytes**. Los archivos R5 permanecen para compatibilidad/rollback, sin usarse como fondo opaco R6.
- Sin CDN, stock ni fuentes externas. Marcos fijos, lazy, decode async, reutilización de nodos; ningún request por tecla.
- QA real en navegador sobre fondos claros/oscuros, alfa cero en esquinas y más de40% de píxeles transparentes por recurso. La comparación visual comprueba ausencia de halo difuso, recuadro oscuro o sombra exterior. No se usa máscara radial para ocultarlos.
- Fallback ensayado para WebP y PNG fallidos, manteniendo datos/guardado y usando iconografía local. Bultos sin ilustración exacta reciben icono neutral y texto genérico, nunca big bag como sustituto de una bolsa individual.

El costo de bytes depende del tráfico y cache del despliegue futuro; se miden requests y timings del fixture local, no un SLA Cloud Run ni una estimación monetaria garantizada. No se crea ninguna infraestructura ni proceso permanente.
