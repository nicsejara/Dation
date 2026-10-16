# Workflow UI / Design System — Fase 5: Execution Review Dialog

Base: `6ab27912609b0efc505fd329950ee378ff7edcf3`, con las Fases 0–4 integradas. Assignment y Scheduling ahora renderizan su revisión con `executionReviewDialog()` en `decision-config-ui.mjs`. La estructura y los estilos pertenecen al componente compartido; cada decisión conserva su contenido y sus hooks de ejecución.

## Arquitectura y comportamiento

El renderer recibe título, nombre accesible, filas de etiqueta/valor, nota opcional y atributos de integración. Todo el texto y los valores de atributos se escapan. Los valores nulos se muestran como «—» y el valor cero se conserva. Una revisión sin nota no genera un bloque vacío.

Se conserva el `<dialog>` nativo con `form method="dialog"`, `showModal()`, botón «Volver» y primario de tipo `button`. El controlador existente `bindConfigReview()` sigue gestionando validación, apertura, confirmación, bloqueo de ejecuciones repetidas, error y reintento. También se conservan el foco atrapado en ambas direcciones, Escape, retorno al disparador y cierre al abandonar la pantalla. No se incorpora otro controlador ni framework.

Assignment conserva Decision Case, Alcance, Objetivo, Prioridades, Recursos y su nota sobre la planificación posterior. Su actualización de prioridades reemplaza el contenido del mismo nodo de diálogo, como antes. Scheduling conserva Decision Case, Entrada con Run de origen, Ventana, Reglas por foco, Objetivo y Recursos heredados; mantiene su hook adicional de error y su ruta de ejecución alternativa.

## Contrato visual

`.d-execution-review` en `dation-design-system.css` define el contrato para ambos consumidores:

- Ancho máximo de 650 px, margen exterior de 16 px y altura limitada al viewport con scroll interno.
- Padding de 24 px, reducido a 16 px en móvil; radio de 20 px, superficie oscura, borde y sombra mediante tokens existentes.
- Encabezado con eyebrow común y H2 de 22 px; filas de dos columnas y separadores compartidos. A 760 px o menos, etiqueta y valor pasan a una columna.
- Footer común con «Volver» secundario y «Ejecutar decisión» primario, ambos del sistema de botones existente. En móvil se apilan y ocupan el ancho disponible. El primario conserva la flecha y los estados del workflow.
- Apertura breve compartida, desactivada con movimiento reducido. No se añade animación de cierre que retrase la restitución del foco.

Se retiran los overrides de revisión de Assignment y Scheduling, incluidos los `!important` anteriores de radio y nota. El alias `dispatch-review-summary` se conserva para compatibilidad; sus reglas legacy excluyen explícitamente este componente. Los otros diálogos de filtros y cambio de datos mantienen sus estilos. No se añaden tokens duplicados ni `!important`.

## Verificación

Las auditorías antes/después recorren 30 estados cada una en 1440, 1280, 1024, 768 y 390 px, con capturas, consola, red, contraste, wrapping y controles nativos. No ejecutan decisiones reales.

Se añaden tres regresiones de Chromium:

1. Comparación de estilos computados de ambos consumidores en esos cinco anchos y en 360 × 250. Comprueba contenido particular, ancho compartido, contraste, ausencia de overflow, modalidad, Tab, Shift+Tab, Escape, foco visible sin obstrucciones y ausencia de navegación o solicitudes al abrir/cerrar.
2. Texto HTML literal, atributos con comillas, notas opcionales y valores extensos sin espacios; comprueba escape, cero/nulo, scroll y ajuste al viewport.
3. Rechazo asíncrono del callback, feedback, desbloqueo para reintentar, exclusión de confirmaciones repetidas y respuesta tardía tras liberar el propietario. Utiliza el renderer y el controlador reales con un callback local.

Se mantiene la regresión que abre/cancela ambas revisiones y confirma una sola ejecución ante doble evento, junto con las suites de payloads, recuperación y aprobación. Antes de integrar se exigen las suites completas y CI del head exacto, incluidos PostgreSQL 17 y el E2E con API, worker y base desechables.

La publicación verifica el commit de Cloud Build, revisiones y tráfico; luego compara plantilla y hashes de assets con el checkout. La QA de producción abre y cancela las revisiones de un caso existente, comprueba ambos estilos y teclado en seis viewports y compara los registros consultados antes/después. La ejecución se valida con datos sintéticos y en el E2E desechable.

## Archivos

- `backend/app/static/js/dispatch/decision-config-ui.mjs`: renderer compartido.
- `backend/app/static/js/dispatch/assignment-config.mjs` y `scheduling-config-v2.mjs`: consumidores.
- `backend/app/static/css/dation-design-system.css`: contrato visual del componente.
- `backend/app/static/css/assignment-config-v2.css`, `scheduling-config-v2.css` y `scheduling-config-shared-phase2.css`: retirada de estilos duplicados.
- `backend/app/static/css/dispatch.css`: aislamiento de estilos legacy.
- `backend/tests/browser/test_navigation.py` y `test_decision_config_ui_foundation.py`: regresiones y contratos de consumidores.
- Este informe.

No se modifican motores, API, payloads, estado, persistencia, aprobación ni navegación. Esta fase no requiere SQL ni cambios de configuración del entorno. Continúan la **Fase 6: responsive y accesibilidad integral** y la **Fase 7: validación E2E de la saga**.
