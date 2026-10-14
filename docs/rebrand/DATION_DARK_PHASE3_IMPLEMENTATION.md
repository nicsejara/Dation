# Dation — Fase 3: Data Pack y Workflow Action Bar

14 de octubre de 2026. Base productiva: `976a2b88ba182454c046bd4b9f3cec51091a86c8` (Fase 2). Alcance: secciones 40–44 del prompt Dark Rebrand / Product UX Grow-Up y frontera Datos/Action Bar del inventario.

## A. Diagnóstico

Upload conservaba superficies claras y dos sistemas de continuación: `makeFinalBar()` y `makeSticky()`. Un observer alternaba entre ambos según el scroll. Los controles genéricos del renderer histórico imponían botones blancos, links violetas y texto de poco contraste. Los contextos Data Pack de Map y Config aún usaban colores claros, aunque su disclosure y geometría ya estaban corregidos.

## B. Wireframe / intención

Hero compacto → dos archivos con carga/reutilización y validación → compatibilidad real → una única Workflow Action Bar. Cada archivo conserva plantilla, guía, validación, reemplazo, cancelación, historial y recuperación. La barra distingue pendiente, validando, error y listo; sólo el estado listo utiliza el `onNext` existente.

El contexto compartido mantiene el disclosure cerrado por defecto y su orden: identidad → encabezado Data Pack/Cambiar datos → archivos. Se migran sus colores sin alterar progresos, selección de casos, grid o confirmación de impacto.

## C. Implementación

- `workflow-action-bar.mjs`: patrón compartido con un botón estable y estados explícitos; iconos SVG de archivo/flota, check, alerta y flecha; mensaje anunciado y descrito por el CTA. Pendiente o servicio no disponible deshabilita continuar; validando mantiene espera; error enfoca la card del problema; listo llama al callback existente. Los avisos opcionales no bloquean.
- Barra sticky dentro del ancho de contenido, separación inferior de 16 px, superficie dark translúcida, blur y borde. En escritorio mide 80 px; en pantallas estrechas crece con el texto. ResizeObserver registra su altura para el margen de scroll de controles y se elimina con el scope. No hay segunda barra ni observer de alternancia.
- Upload: hero y panel de ayuda compactados, cards oscuras con acentos por archivo, estados con etiquetas, switch de origen, dropzone, progreso, archivo guardado, validación y compatibilidad sobre roles dark. Su hoja propietaria sustituye las versiones superpuestas. Los selectores genéricos del renderer histórico excluyen Upload y siguen aplicándose a sus consumidores pendientes.
- Guía, historial y reporte: drawers dark con foco, Escape, restauración y cleanup existentes; tablas con scroll local accesible por teclado. El selector de historial tiene nombre accesible. La descarga de validación utiliza el botón compartido. Los tres overlays abandonan el bridge claro.
- Contexto Data Pack de Map y ambas Config: clase acotada `.d-data-context`, roles propios e aislamiento del foco heredado. Los colores se migran en sus dueños existentes. Se conservan los reset de layout del PR #47, el badge Validado condicional, archivos en dos columnas/una móvil, Copy ID, columnas y Cambiar datos. El resto de esas páginas mantiene su migración pendiente.
- Caché: assets CSS afectados versionados como `dark-data-pack-v1`; los módulos mantienen el contrato no-cache/ETag del servidor. No se cambian contratos API, parsing CSV, límites de archivo, persistencia, preflight, motor ni esquema.

## D. Archivos exactos

| Área | Archivos bajo `backend/` |
|---|---|
| Barra y ciclo de vida de Upload | `app/static/js/dispatch/workflow-action-bar.mjs`, `upload/index.mjs` |
| Drawers | `app/static/js/dispatch/upload/guide-drawer.mjs`, `library.mjs`, `validation-report.mjs` |
| Contexto compartido | `app/static/js/dispatch/decision-config-ui.mjs`, `decision-map.mjs` |
| Primitivas y boundaries | `app/static/css/dation-design-system.css`, `dation-legacy-surfaces.css` |
| Upload | `app/static/css/dda-logistics-upload.css` |
| Dueños de contexto e historial de estilos | `app/static/css/dispatch.css`, `assignment-config-v2.css`, `decision-map-case-v2.css`, `decision-trace-v3.css` |
| Assets y vista | `app/templates/app.html` |
| Regresión | `tests/browser/test_navigation.py`, `theme_audit.js`, `tests/test_frontend_contract.py`, `tests/test_assignment_config_visual_consistency.py` |

Documentación: este informe y la nota de estado de `DATION_DESIGN_SYSTEM_V1.md`.

## E. Tests

Desde `backend/`, activar primero `/workspace/.dation-cloud/activate.sh`:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium .browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_navigation.py'
DATION_BROWSER_PYTHON="$PWD/.browser-venv/bin/python" CHROMIUM_EXECUTABLE=/usr/bin/chromium python tests/e2e/run_suite.py
python -m compileall -q app main.py worker.py
python -m pip check
```

Gate de publicación: **349 Python + 37 Node + 75 Chromium + 46 SQL en CI + 7 E2E reales = 514 casos**. Sintaxis JavaScript y `git diff --check` también deben pasar. Las dependencias permanecen sin cambios.

Los cuatro casos nuevos de navegador comprueban una sola barra/CTA estable, pending→ready con reutilización, geometría y último control visible, contraste compuesto, error de archivo con foco, validación pendiente/cancelación, servicio no disponible, incompatibilidad entre archivos y recuperación con avisos opcionales. También verifican guía/historial/reporte, nombre accesible, contexto nativo cerrado/abierto y foco dark de Copy ID a cinco anchos. Los estados visuales no crean casos ni ejecuciones.

El E2E real conserva CSV/upload, creación, ejecución, aprobación, reemplazo, historial y recuperación, con PostgreSQL/PostgREST, storage y worker desechables. No usa Supabase productivo. La CI debe pasar en el head exacto y en main; el comprobante de publicación se registra en el PR y `/workspace/dation-audit/rebrand-phase3-production-final.json`.

## F. Visual QA

Anchos: **1440, 1280, 1024, 768 y 390 px**. Se revisan vacío, listo/reutilizado, guía, error de archivo, reporte, historial, servicio no disponible y contextos de Map/Assignment/Scheduling. Capturas y geometría en `/workspace/dation-audit/rebrand-phase3-visual/`, `rebrand-phase3-states/` y `rebrand-phase3-context/`.

| Ancho | Hero Upload | Barra vacía |
|---|---:|---:|
| 1440 / 1280 | 261.4 px | 80 px |
| 1024 | 226.7 px | 117.4 px |
| 768 | 223.6 px | 117.4 px |
| 390 | 286.9 px | 166.4 px |

Son mediciones de contenido, sin alturas fijas que lo recorten. El hero de escritorio baja de aproximadamente 325 px de Fase 1 a 261 px. La barra queda dentro del contenido y mantiene libre el último control al terminar el scroll. En móvil las tablas usan scroll interno; no se genera scroll horizontal del documento al completar la transición responsive.

El helper mide WCAG AA sobre colores renderizados, transparencias y gradientes: 4.5:1 normal y 3:1 grande. Los estados vacío/listo y guía alcanzan como mínimo 5.97:1. Se verifican también errores, avisos y contextos; los resultados finales se guardan en el PR. Esto no certifica gráficos ni páginas pendientes.

La QA productiva comprueba template y 20 assets por hash, ETag/no-cache, privacidad, readiness, dependencias y heartbeat del worker. Usa casos existentes y validación local de un archivo no CSV; bloquea escrituras persistentes y compara hashes de casos, runs y comparativas revisados antes/después. Las ejecuciones y aprobaciones se prueban en el E2E desechable.

## G. Deuda / riesgos

Los formularios de Config y el resto de Map/dashboard continúan con su boundary temporal. Fase 4 debe adoptar la barra compartida para Config y retirar la UX de profundidad según el contrato documentado, conservando históricos, comparative y el valor técnico essential explícito para nuevas Assignment. Esta fase no cambia `analysis_depth` ni payloads.

Las geometrías y colores del contexto permanecen bajo hojas que también contienen estilos legacy. La consolidación de loaders y reglas demostradas sin uso pertenece a Fase 7. No se habilita ninguna decisión o control futuro. Rollback: revertir el merge y publicar ese commit mediante Cloud Build; no requiere rollback de datos.

## H. Gate

**FASE 3 COMPLETA — LISTA PARA FASE 4**, una vez verificadas las suites y publicación registradas en el PR. No iniciar Fase 4 automáticamente.
