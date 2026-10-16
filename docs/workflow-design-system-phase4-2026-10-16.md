# Workflow UI / Design System — Fase 4: Hero System

Base: `59b90e9d0dd483fde05ea542421bb042ed66e196`, con las Fases 2 y 3 publicadas. Esta entrega consolida los Heroes de Data Pack, Decision Map, configuración Assignment y configuración Scheduling. La extracción de los review dialogs sigue pendiente de Fase 5.

## Arquitectura

Los cuatro consumidores usan `decisionHero()` de `decision-config-ui.mjs`. Se amplía el renderer existente con título de panel, nota final, clases de compatibilidad y revelado opcionales. Conserva índice de decisión opcional, ausencia de panel vacío y escape de texto. Data Pack conserva sus chips contextuales y el nodo/binding de «Reutilizalos»; el mapa conserva sus clases y atributo de revelado.

`.d-page-hero--workflow` en `dation-design-system.css` es el propietario de columnas, alineación, metadata, panel y responsive. El modificador limita el alcance a estas cuatro pantallas; los Heroes de Inicio y Overview conservan su composición. Se retiran las reglas de Hero duplicadas en las hojas de carga, Assignment, mapa y trazabilidad, incluidos los dos `!important` de wrapping anteriores. No se incorpora biblioteca ni framework.

Los tokens existentes del panel y metadata se reutilizan. Se añaden `--hero-workflow-min-height` y `--hero-copy-gap`, para distinguir el mínimo del workflow de los otros Heroes y compartir la separación del contenido.

## Metadata

`.d-hero-meta` coloca Paso y Decisión en una columna. Paso usa 11 px, peso 750 y mayor contraste de texto/borde; Decisión usa 10 px y peso 600. Ambos se alinean arriba a la izquierda. El espacio se controla con `--hero-meta-gap`. Los chips contextuales «Órdenes» y «Flota» conservan su disposición independiente.

## Panel y altura

En escritorio, el panel usa `--hero-panel-width: clamp(20rem,32vw,25rem)`, frente a los 280 px anteriores. Se unifican iconos, padding, gap y tipografía de sus filas. El copy de D1/D2 y la introducción del mapa se condensan conservando conceptos, nombres de decisiones y secuencia.

La altura usa un mínimo compartido de 260 px, sin `height`, límite máximo ni recorte. En 1440 y 1280 px, los cuatro Heroes miden 260 px y las doce descripciones de panel quedan en una línea. Assignment y Scheduling medían aproximadamente 275 px; Data Pack 261 px y mapa 255 px. La metadata vertical no aumenta la altura de configuración.

A 1100 px o menos, el panel pasa debajo del texto, con tres columnas de tarjetas. A 700 px o menos, las tarjetas pasan a una columna. Antes, la clase compartida de carga ocultaba el panel de las cuatro pantallas; ahora su contenido permanece accesible en tablet y móvil. El Hero puede crecer verticalmente. Los textos largos y sin espacios pueden envolver, incluso en metadata, título y nota final.

## Verificación

Se añaden dos regresiones de Chromium:

- Veinticuatro combinaciones de pantalla/ancho: las cuatro pantallas en 1440, 1280, 1024, 768, 390 y 360 px. Comprueban altura y columnas de escritorio, panel visible y debajo del texto en responsive, metadata vertical y jerarquía, alineación, tamaño de texto, wrapping, ausencia de recortes y movimiento reducido. No ejecutan runs.
- Renderer con una decisión futura, cinco elementos de panel, títulos/metadata/notas extensos sin espacios y texto HTML literal. Comprueba crecimiento sin desbordamiento, escape del contenido y uso del token de separación. Se mantienen las regresiones de índice opcional y panel opcional de Fase 1.

El contrato Python de wrapping se actualiza para apuntar al Design System; la hoja de trazabilidad ya no controla el Hero. Se conservan las regresiones de barras y CTA de las Fases 2 y 3.

Las auditorías antes/después recorren 30 estados cada una: los cuatro Heroes y ambas revisiones en cinco anchos. Incluyen consola, red, contraste, desbordamiento, modalidad nativa, Tab, Shift+Tab, Escape y recuperación de foco. Las capturas permiten comparar las composiciones.

Antes de integrar se requieren las suites completas, CI sobre el head exacto y los gates de PostgreSQL y E2E con API/worker/base desechables. La publicación comprueba fuente de Cloud Build, revisiones y tráfico; luego plantilla, hashes de assets, acceso privado, salud y navegación sobre un caso existente, cancelando revisiones y comparando los registros comprobados antes y después.

## Archivos

- `backend/app/static/js/dispatch/decision-config-ui.mjs`: renderer compartido.
- `backend/app/static/js/dispatch/upload/index.mjs` y `decision-map.mjs`: migración de consumidores.
- `backend/app/static/js/dispatch/assignment-config.mjs` y `scheduling-config-v2.mjs`: copy condensado.
- `backend/app/static/css/tokens.css` y `dation-design-system.css`: contrato visual.
- `backend/app/static/css/dda-logistics-upload.css`, `assignment-config-v2.css`, `decision-trace-v3.css` y `dispatch.css`: retirada de reglas locales.
- `backend/tests/browser/test_navigation.py` y `backend/tests/test_assignment_config_visual_consistency.py`: regresiones.
- Este informe.

No se modifican API, motores, payloads, persistencia, DecisionCase, aprobación ni navegación. No requiere migración de Supabase ni cambios de configuración del entorno. La siguiente fase es la **5: Execution Review Dialog compartido**; luego siguen las Fases 6 y 7 de validación integral de la saga.
