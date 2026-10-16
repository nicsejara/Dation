# Workflow UI / Design System — Fases 2 y 3

Base: `07f5dffa355013c5ed6706dc33dff9ff38c6b6d4`. Esta entrega continúa la saga del documento Workflow UI / Design System, conservando navegación, motores, validación, ejecución y persistencia.

## Fase 2 — Barras compartidas

La fábrica existente agrupa los controles y el CTA en `.d-workflow-action-bar__actions`. El grupo usa una cuadrícula de ancho intrínseco y columnas iguales; los controles heredan esas columnas mediante `subgrid`. La columna del CTA tiene un factor de 1.35 respecto de cada control. El contenido determina el tamaño natural y el grupo se adapta al espacio disponible.

Los controles usan la misma altura mínima de 46 px, padding, radio y tipografía. Sus valores pueden ocupar varias líneas. Se retiraron el máximo fijo, los puntos suspensivos y la composición horizontal con scroll que divergían entre Data Pack y configuración. El mínimo tipográfico pasa de 12ch a 14ch para evitar cortes de palabras en móvil; no fija el ancho del grupo.

A 1100 px o menos, la metadata ocupa su propia fila. A 620 px o menos, los controles forman tantas columnas como permitan su mínimo tipográfico y el ancho disponible, con filas de igual altura; el CTA ocupa el ancho completo. Los observadores existentes siguen reservando espacio para la altura real de la barra. No se añaden observadores ni listeners globales.

El estilo genérico de botones de Assignment deja de aplicarse a las primitivas compartidas. Así D1 y D2 recuperan el CTA primario sin sobrescrituras adicionales ni nuevos `!important`. Los botones de contexto conservan `data-summary-target`, foco y callbacks; el CTA conserva su nodo y atributos de revisión al cambiar de estado. La prueba de identidad comprueba el mismo nodo dentro de la nueva agrupación.

Se retiran el listener de desplazamiento y los márgenes de scroll del carrusel anterior. Su regresión móvil pasa a verificar la cuadrícula actual en D1 y D2 a 360 y 390 px: Tab y Shift+Tab recorren los tres controles, el contorno de foco completo queda dentro de la barra y no hay scroll horizontal ni cambios de estado al consultar el resumen.

Validación de esta fase antes de continuar:

- 21 pruebas existentes de contratos e imports aprobadas.
- 4 pruebas de navegador enfocadas aprobadas, incluida una nueva que recorre Data Pack, D1 y D2 en cinco anchos y verifica igualdad de controles, CTA más ancho, jerarquía primaria y ausencia de recortes con texto habitual y largo.
- 30 estados adicionales auditados en 1440, 1280, 1024, 768 y 390 px, sin errores JavaScript/HTTP, desbordamiento ni fallos reportados por el auditor HTML de contraste. Se conserva el teclado de los diez diálogos.
- Capturas revisadas de la barra D1 en escritorio y D2 en móvil.

## Fase 3 — CTA de avance

Los CTA activos de Data Pack, configuración, ejecución D1/D2, configuración/revisión del mapa, aprobación y continuación usan `.d-button.d-button--workflow.d-button--primary`. El Design System es el propietario de altura mínima de 46 px, padding, radio, tipografía, gradiente AA, foco, hover, disabled, busy y movimiento reducido. El tamaño de icono se comparte mediante `--control-icon-size`.

`workflow-action-bar.mjs` exporta la clase base y `workflowActionLabel()`, con texto escapado y una única flecha SVG decorativa a la derecha. La fábrica DOM reutiliza el mismo catálogo de iconos. Se conserva la etiqueta funcional de cada pantalla y se elimina la flecha textual duplicada al renderizarla. `dashboard-actions.mjs` usa el mismo renderer al actualizar dinámicamente la continuación.

El indicador de carga se define una sola vez en CSS, conserva el espacio del icono y usa `aria-busy`. En movimiento reducido queda estático. Aprobación y continuación informan ese estado y lo retiran al terminar o recuperar un error; sus callbacks, validaciones y guardas de ejecución permanecen bajo los propietarios existentes.

Se retiraron las reglas de aspecto de CTA en `dispatch.css`, `decision-map-case-v2.css`, `dashboard-toolbar.css` y las hojas de Scheduling. Los estilos genéricos de botones y foco dejan de aplicarse a `.d-button`. No se añaden `!important`; se eliminan los que impedían aplicar el contrato común.

Las acciones de inspección de resultados aprobados o en curso, «Volver», «Cambiar datos», copiar, exportar, detalles y herramientas conservan su jerarquía secundaria. La acción «Revisar» del mapa sí adopta el patrón de avance cuando el resultado requiere aprobación. No se modifica la estructura visual de los review dialogs, pendiente de Fase 5, ni la composición del Hero, pendiente de Fase 4.

Validación específica antes de integrar:

- Matriz de 45 comparaciones en Chromium: nueve CTA de avance en 1440, 1280, 1024, 768 y 390 px. Comprueba estilos calculados, foco de teclado, un solo icono decorativo, ausencia de flecha textual duplicada y texto sin recortes. Las aprobaciones de esta prueba usan exclusivamente la API sintética.
- Las regresiones de aprobación verifican también `aria-busy`, indicador de carga, recuperación del error y confirmación única. La prueba de estados del botón comprueba el indicador con y sin movimiento reducido.
- Nueva auditoría de 30 estados con igualdad de estilos primarios, sin errores JavaScript/HTTP, desbordamiento ni fallos de contraste reportados. Se mantiene el teclado de los diez diálogos.
- Suites completas de Python y Node aprobadas: 350 y 41 pruebas respectivamente. La suite completa de navegador y los gates oficiales de CI son requisitos antes de integrar.

## Archivos y responsabilidades

- `backend/app/static/css/tokens.css`: mínimos tipográficos y tamaños compartidos.
- `backend/app/static/css/dation-design-system.css`: cuadrícula de barras, botones, estados e indicador de carga.
- `backend/app/static/js/dispatch/workflow-action-bar.mjs`: fábrica, agrupación, clase y etiqueta comunes.
- `backend/app/static/js/dispatch/decision-map.mjs`: consumo del patrón según la intención de la acción.
- `backend/app/static/js/dispatch/assignment-config.mjs` y `scheduling-config-v2.mjs`: CTA finales conservando sus hooks y propietarios de ejecución.
- `backend/app/static/js/dispatch/dashboard-toolbar.mjs` y `dashboard-actions.mjs`: aprobación, continuación y actualizaciones de estado visual.
- `backend/app/static/css/dispatch.css`, `decision-map-case-v2.css`, `assignment-config-v2.css`, `assignment-dashboard-v2.css`, `dashboard-toolbar.css`, `scheduling-config-v2.css` y `scheduling-config-shared-phase2.css`: retirada o acotación de overrides de los propietarios.
- `backend/tests/browser/test_navigation.py`: dos regresiones nuevas y ampliación de comprobaciones de estados existentes.
- `backend/tests/test_decision_map_micro_polish.py`: actualización del contrato visual anterior del mapa al patrón compartido.
- Este informe.

## Verificación de entrega

Desde `backend`, con el entorno existente activado:

```bash
python -m unittest discover -s tests -v
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium \
DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
  .browser-venv/bin/python -m unittest discover -s tests/browser -p test_navigation.py -v
```

La integración requiere CI verde sobre el head exacto, incluidos PostgreSQL y E2E con API/worker/base desechables. Después del despliegue se comprueban assets, salud y flujos de producción sobre casos existentes, cancelando las revisiones y comparando los registros comprobados antes y después. No requiere migración ni cambios de configuración del entorno.

Las Fases 2 y 3 quedan en commits separados. La siguiente fase es la **4: Hero System**; siguen luego revisión compartida, validación final responsive/accesibilidad y E2E de toda la saga.
