# Workflow UI / Design System — Fase 6: responsive y accesibilidad

Base: `103fda53474883fe847f1c9aa1cdb84dc224d925`, con las Fases 0–5 integradas. Esta entrega valida Heroes, metadata, barras, botones y revisiones como un workflow común y corrige los hallazgos de reflow, teclado y semántica.

## Hallazgos y correcciones

La auditoría inicial recorre 48 estados de Data Pack, mapa, Assignment, Scheduling y ambas revisiones en ocho tamaños: 1440 × 1000, 1280 × 1000, 1024 × 1000, 768 × 1000, 390 × 844, 320 × 568, 320 × 256 y 568 × 320. Incluye 584 comprobaciones de foco, contraste HTML, árbol de accesibilidad, espaciado de texto aumentado y ausencia de desbordamiento horizontal.

Se reproducen 33 avisos, correspondientes a cuatro causas:

- Tres indicadores de progreso sin nombre accesible: el avance de decisiones aprobadas y los contadores de órdenes/flota de Assignment. Sus valores no cambian; ahora tienen nombre y texto de valor con contexto.
- Pasos parcialmente visibles en la navegación horizontal al recibir Tab, incluso después de esperar a que termine el scroll. Un listener delegado de `focusin` en el contenedor existente desplaza exclusivamente su eje horizontal cuando hace falta y reserva el margen del foco. El scroll es inmediato. Se mantiene el snap para interacción fuera del foco de la navegación; mientras contiene el foco se desactiva para evitar que deshaga el ajuste.
- A 320 × 568, la combinación de cabecera, navegación y barra inferior fija podía tapar opciones. El modo de flujo normal existente del Design System se amplía a pantallas de hasta 620 px de ancho y 700 px de alto. También se conserva su activación global a 540 px de alto o menos. No se ocultan controles ni se limita su contenido. Los viewports habituales más altos conservan las barras sticky.
- Los badges de estado compartidos podían salir de la columna a 320 px con espaciado de texto aumentado. Ahora respetan su ancho disponible y permiten envolver el texto completo.

## Arquitectura

`decisionHero()`, `createWorkflowActionBar()` y `executionReviewDialog()` siguen siendo los renderers compartidos. `dation-design-system.css` conserva la composición y el modo de pantallas bajas. La navegación mantiene su renderer en `app.html` y sus estilos en `app.css`; el nuevo listener se registra una sola vez sobre el contenedor permanente, sin duplicarse al reconstruir los pasos. El badge conserva su definición compartida por Assignment y Scheduling en la hoja existente.

Las correcciones son de presentación, scroll y atributos accesibles. No se modifican rutas, callbacks de navegación, motores, API, payloads, validación, estado de Decision Case, persistencia ni aprobación. No se añade dependencia, framework, token duplicado ni `!important`. No requiere SQL ni cambios de configuración del entorno.

## Regresiones y validación

Se amplía la regresión existente de nombres accesibles para incluir `progressbar` en las ocho pantallas principales y los cinco anchos requeridos. Se añaden dos pruebas de Chromium:

1. Recorrido completo con Tab y Shift+Tab de los cuatro pasos a 320 × 568, 320 × 256 y 568 × 320; foco visible y sin obstrucción, margen del foco dentro de la navegación horizontal, valores accesibles del progreso, ausencia de overflow con espaciado aumentado, badges sin recorte y revisiones con Enter, Tab, Shift+Tab, Escape y restitución del foco. No inicia ejecuciones ni aprobaciones.
2. Cambio de `prefers-reduced-motion` con cada revisión abierta: la animación se cancela al activar reducción de movimiento, la siguiente apertura conserva esa preferencia y el botón Volver funciona con Space sin cambiar la ruta ni generar solicitudes.

El espaciado de prueba usa altura de línea de 1,5, separación entre letras de 0,12 em, palabras de 0,16 em y párrafos de 2 em. Se aplica únicamente en el navegador de QA. Las tarjetas informativas de solo lectura que superan la altura del viewport se comprueban por su tramo visible y su indicador de foco; los controles accionables deben estar completamente visibles. El auditor no exige que una tarjeta más alta que la pantalla quepa entera.

Se mantienen las regresiones de altura/metadata/panel de Hero, controles homogéneos y CTA destacado, hover/disabled/loading, diálogo compartido, confirmación única, validación, payloads, recuperación, dashboards y aprobaciones. Las auditorías visuales antes/después siguen recorriendo otros 30 estados cada una en los cinco anchos requeridos, con capturas comparables.

Antes de integrar se requieren las suites completas y CI del head exacto, incluidos PostgreSQL 17 y el E2E con API, worker y base desechables. La publicación verifica fuente, revisiones, tráfico, plantilla y hashes de assets. La QA productiva amplía el recorrido a nueve tamaños e incluye teclado, nombres accesibles, espaciado y movimiento reducido. Solo abre y cancela revisiones; compara los registros consultados antes y después.

Las comprobaciones se realizan con Chromium, su árbol de accesibilidad y los auditores HTML integrados. No equivalen a una sesión manual con un lector de pantalla específico.

## Archivos

- `backend/app/static/css/app.css`: margen y snap de la navegación horizontal.
- `backend/app/templates/app.html`: scroll horizontal delegado al recibir foco.
- `backend/app/static/css/dation-design-system.css`: modo de flujo normal para pantallas estrechas y bajas.
- `backend/app/static/css/assignment-config-v2.css`: wrapping del badge compartido.
- `backend/app/static/js/dispatch/decision-map.mjs` y `assignment-config.mjs`: nombres y valores accesibles de progreso.
- `backend/tests/browser/test_navigation.py`: regresiones de reflow, teclado, semántica y movimiento.
- Este informe.

La siguiente entrega es la **Fase 7: QA End-to-End de la saga completa**.
