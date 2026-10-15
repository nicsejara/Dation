# Workflow UI / Design System — Fase 1

## Resultado y alcance

Esta fase establece el contrato visual compartido sobre `main` base `c4a2e2de8fc4d34422b08f4ca937e01b33a98522`. Amplía las primitivas existentes; conserva navegación, validación, callbacks, ejecución, API y persistencia.

La normalización de grupos de controles corresponde a Fase 2; la migración de todos los CTA, a Fase 3; la composición completa del Hero, a Fase 4; y la extracción visual de los review dialogs, a Fase 5.

## Fuente de verdad

- `backend/app/static/css/tokens.css`: incorpora los roles `--workflow-action-height`, `--workflow-action-radius`, `--workflow-action-padding-x`, `--workflow-action-min-width`, `--workflow-context-control-height` y `--workflow-context-control-min-width`. Reutiliza la escala de controles, radios y espaciados existente. El mínimo contextual de `12ch` es un piso tipográfico, no el ancho fijo del grupo; el mínimo del CTA se deriva de ese piso y su padding. La Fase 2 determinará los anchos de cada grupo por su mayor contenido.
- El mismo archivo define `--hero-panel-width`, `--hero-panel-gap` y `--hero-meta-gap`, preparados para la migración del Hero en Fase 4. El ancho del panel utiliza `clamp()`; todavía no reemplaza las reglas de las pantallas.
- `backend/app/static/css/dation-design-system.css`: `.d-button--workflow` agrega dimensiones, radio y ajuste de texto a `.d-button`. Se combina con las variantes primaria/secundaria; hereda sus colores, tipografía, iconos, foco, hover, disabled, busy y movimiento reducido. No duplica esos estados. `.d-page-hero--copy-only` permite un Hero de una columna cuando no hay panel.
- `backend/app/static/js/dispatch/workflow-action-bar.mjs`: la fábrica existente conserva `.d-button--workflow` al actualizar estados, sin reemplazar el nodo del botón ni cambiar sus callbacks. La acción de corregir errores conserva su variante secundaria.
- `backend/app/static/js/dispatch/decision-config-ui.mjs`: `decisionHero()` omite la pill de decisión si no recibe índice y omite el panel si no tiene elementos. Conserva sus clases y hooks actuales cuando recibe esos contenidos.

El CTA de Data Pack ya consume las nuevas dimensiones: pasa de 40 a 46 px de alto y mantiene texto legible, gradiente y foco. Las configuraciones D1/D2 consumen la clase compartida, pero conservan los overrides de sus propietarios hasta las migraciones de las fases 2–3. No se añaden reglas `!important` para competir con ellos.

Los Heroes de las cuatro pantallas actuales conservan sus medidas porque sus consumidores ya proporcionan índice y panel. La variante opcional corrige el resultado «DECISIÓN undefined DE 3» observado al probar la primitiva sin índice durante la Fase 0.

## Archivos modificados

1. `backend/app/static/css/tokens.css`
2. `backend/app/static/css/dation-design-system.css`
3. `backend/app/static/js/dispatch/workflow-action-bar.mjs`
4. `backend/app/static/js/dispatch/decision-config-ui.mjs`
5. `backend/tests/browser/test_navigation.py`
6. Este informe.

## Pruebas y QA

Se añaden dos regresiones de Chromium que comprueban comportamiento observable:

- Actualización pending → ready → busy → error → ready: misma identidad de botón, callbacks correctos, acción correctiva secundaria, `aria-busy`, descripción accesible y adaptación a tokens sobrescritos. Incluye texto largo y cinco anchos: 1440, 1280, 1024, 768 y 390 px.
- Hero con índice omitido, nulo, vacío, numérico o textual: metadata correcta, ausencia del panel vacío, una columna, contenido escapado y conservación de un panel informado. Se comprueba en escritorio y móvil sobre los estilos reales de configuración.

Suites requeridas antes de integrar, desde `backend` con el entorno activado:

```bash
python -m unittest discover -s tests -v
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium \
DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
  .browser-venv/bin/python -m unittest discover -s tests/browser -p test_navigation.py -v
```

La auditoría visual adicional recorre 30 estados en los cinco anchos: Data Pack, mapa, configuración y revisión D1, configuración y revisión D2. Comprueba consola, red, desbordamiento, contraste reportado por el auditor HTML integrado y teclado de los diez diálogos. Utiliza API sintética y no ejecuta runs reales.

El CI oficial conserva también sus gates de dependencias, PostgreSQL y E2E con API, worker y base desechables. La publicación debe verificar el SHA exacto con CI verde y comprobar después los assets servidos y los flujos de producción sin confirmar ejecuciones.

## Regresiones y límites

La auditoría de 30 estados no detectó regresiones de consola, red, contraste reportado ni desbordamiento. Los diez diálogos conservan modalidad nativa, Tab/Shift+Tab, Escape y devolución del foco; abrirlos no cambia URL ni solicita una ejecución.

No se modifica el esquema ni se ejecuta el kit de reinicio de Supabase. Los estados finales de la entrega, los identificadores de CI/build y las evidencias de publicación se registran al completar la validación y el despliegue de esta fase.
