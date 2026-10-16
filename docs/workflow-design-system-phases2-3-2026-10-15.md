# Workflow UI / Design System — Fases 2 y 3

Base: `07f5dffa355013c5ed6706dc33dff9ff38c6b6d4`. Esta entrega continúa la saga del documento Workflow UI / Design System, conservando navegación, motores, validación, ejecución y persistencia.

## Fase 2 — Barras compartidas

La fábrica existente agrupa los controles y el CTA en `.d-workflow-action-bar__actions`. El grupo usa una cuadrícula de ancho intrínseco y columnas iguales; los controles heredan esas columnas mediante `subgrid`. La columna del CTA tiene un factor de 1.35 respecto de cada control. El contenido determina el tamaño natural y el grupo se adapta al espacio disponible.

Los controles usan la misma altura mínima de 46 px, padding, radio y tipografía. Sus valores pueden ocupar varias líneas. Se retiraron el máximo fijo, los puntos suspensivos y la composición horizontal con scroll que divergían entre Data Pack y configuración. El mínimo tipográfico pasa de 12ch a 14ch para evitar cortes de palabras en móvil; no fija el ancho del grupo.

A 1100 px o menos, la metadata ocupa su propia fila. A 620 px o menos, los controles forman tantas columnas como permitan su mínimo tipográfico y el ancho disponible, con filas de igual altura; el CTA ocupa el ancho completo. Los observadores existentes siguen reservando espacio para la altura real de la barra. No se añaden observadores ni listeners globales.

El estilo genérico de botones de Assignment deja de aplicarse a las primitivas compartidas. Así D1 y D2 recuperan el CTA primario sin sobrescrituras adicionales ni nuevos `!important`. Los botones de contexto conservan `data-summary-target`, foco y callbacks; el CTA conserva su nodo y atributos de revisión al cambiar de estado. La prueba de identidad comprueba el mismo nodo dentro de la nueva agrupación.

Validación de esta fase antes de continuar:

- 21 pruebas existentes de contratos e imports aprobadas.
- 4 pruebas de navegador enfocadas aprobadas, incluida una nueva que recorre Data Pack, D1 y D2 en cinco anchos y verifica igualdad de controles, CTA más ancho, jerarquía primaria y ausencia de recortes con texto habitual y largo.
- 30 estados adicionales auditados en 1440, 1280, 1024, 768 y 390 px, sin errores JavaScript/HTTP, desbordamiento ni fallos reportados por el auditor HTML de contraste. Se conserva el teclado de los diez diálogos.
- Capturas revisadas de la barra D1 en escritorio y D2 en móvil.

## Fase 3 — CTA de avance

Pendiente de implementar y validar en el siguiente commit de esta misma entrega.
