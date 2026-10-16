# Normalización UX/UI Pre-Dashboard — Fases 0–6

Base: `28fddcbfb00117832957c1d74e0d33cd3bbfaace`. Implementa los cuatro bloques del documento maestro: revisiones D1/D2, geometría de toolbars, copy del Hero de configuración D2 y catálogo de Inicio. El rediseño de dashboards pertenece a otra saga.

## Auditoría y causas

| Área | Owner / causa | Solución compartida |
| --- | --- | --- |
| Review D1/D2 | Ya usan `executionReviewDialog()` y footer derecho; cinco filas con nota frente a seis sin nota generan alturas distintas | Mínimo de escritorio común, form flexible y acciones al pie; nota breve en D2 |
| Toolbar D1 | El ID `#dispatch-dashboard-root` en lifecycle prevalece sobre el máximo de 1220 px de Assignment | Máximo del shell definido por el componente compartido, respetado por lifecycle |
| Toolbar D2 | `.dispatch-focus-main` limita sólo su interior; la toolbar usa todo el root | Mismo shell y mismo ancho interior que D1 |
| Herramientas | Button y summary tienen padding, peso y anchos diferentes | Selector y variables compartidos; la acción primaria conserva su contrato |
| Hero D2 | La frase de entrega es innecesariamente larga | Únicamente el copy solicitado |
| Inicio | Dos tarjetas estáticas, sin categorías ni filtros; copy técnico y versión | Registro frontend, renderer local y fallback navegable |

En el baseline a 1680 px, Assignment tiene toolbar/contenido de 1320/1320 px y Scheduling de 1320/1220 px. A 1440 px las revisiones miden aproximadamente 493.56 y 457.13 px de alto. Los secundarios miden 127.36, 121.36 y 95.34 px de ancho. Se guardaron mediciones y capturas locales/productivas antes de editar. Los handlers no dependen de esas medidas.

## Fase 1 — Review dialogs

El primitive existente conserva el markup canónico, native dialog, atributos de ejecución, validación, trapFocus, Escape, error alert y restore. El Design System define una silueta mínima común de 34rem en escritorio, acotada por la altura disponible; el contenido puede crecer y scrollear. El formulario flexible deja las acciones a la derecha y al pie sin hacks por número de filas. En tablet/móvil se conserva el contenido natural, filas en una columna y botones apilados.

Scheduling añade la nota: «La planificación conserva los viajes y recursos aprobados en Assignment. Esta decisión sólo define fechas y secuencia». Usa el mismo slot y estilo de Assignment. A 1440 px ambos diálogos miden 650 × 544 px; el mínimo no fija la altura de contenido extenso.

## Fase 2 — Toolbar geometry

`dashboard-toolbar.css` define `--decision-content-max:1220px`, `--dashboard-toolbar-bleed:24px` y el máximo de shell derivado. El ID de lifecycle consume esa variable en lugar de anularla con su máximo genérico. Se retira el máximo redundante del root de Assignment. Los interiores y rails de ambos dashboards siguen una única regla centrada. El bleed baja a 12 px en tablet y a 0 en móvil.

Map, Exportar y Más usan un selector común para button/summary: mínimo 136 px, alto 38 px, padding, radio, fuente, iconos y gap iguales. El primario conserva su gradiente, alto mínimo de 46 px y padding mayor. La cuadrícula móvil ajusta sus columnas al ancho disponible. No cambian labels, menús ni callbacks.

Sticky, ResizeObserver, variables de altura/top, scroll-margin, cálculo de posición de menús y drawer conservan sus owners. Al apilar herramientas, los menús despejan el grupo completo cuando hay espacio; en pantallas bajas conservan el anclaje al control. Se mantienen el clamp lateral, altura disponible y elección arriba/abajo. Esta extensión geométrica evita que Exportar tape Más y permite cambiar entre ambos sin cerrar primero. El modo de flujo normal existente en pantallas bajas sigue activo.

## Fase 3 — Hero D2

Se reemplaza únicamente `Calendario operativo + secuencia de despachos.` por `Calendario operativo + secuencia`. No cambian pregunta, tercer punto, iconos, tamaño del panel ni renderer del Hero.

## Fase 4 — Catálogo de capacidades

`home-dda-catalog.mjs` define el registro de siete DDAs y seis filtros: Todos, Supply Chain, Operaciones, Producción, Comercial y Activos. Los contadores se derivan del registro. Sólo Logística está disponible y conserva `logistics-overview`, stage `dda` y el handler de navegación actual.

Las tarjetas son artículos con headings. Logística tiene un único botón semántico cuyo área de clic se extiende a toda la tarjeta. Las seis próximas no tienen links, botones, tabindex ni navegación; usan «Próximamente» y «En desarrollo». Iconos SVG existentes e inline, con texto legible y sin opacidad global reducida. Se retiran versión del motor y copy técnico únicamente del catálogo.

El montaje ocurre una vez antes del bind de navegación. Los filtros actualizan `hidden`, `aria-pressed` y un estado anunciado; conservan los nodos y listeners. No escriben workspace ni storage y no llaman API. Un WeakSet evita duplicar el montaje. El HTML base conserva Logística navegable si el módulo del catálogo no está disponible.

Se mantiene el Hero principal de Inicio, sidebar, topbar, DDA landing, Data Pack y rutas existentes.

## Fases 5–6 — Accesibilidad y regresión

- Filtros por teclado, selección textual/visual, foco visible y anuncio de resultados. Los controles de Inicio reservan margen para la topbar al recibir foco; Tab y Shift+Tab se comprueban en todos los tamaños, también con movimiento normal una vez finalizado el desplazamiento.
- Hover y contraste diferenciados; movimiento reducido conserva cambios de color sin desplazamiento.
- Grid adaptable con alturas homogéneas por fila, filtros con wrap y estado de portfolio que puede bajar de línea.
- Revisión de tamaños desde 1680 px hasta 320 px, incluyendo pantallas bajas y orientación horizontal.
- Prueba de fallback que bloquea el módulo del catálogo y abre Logística mediante el markup base.
- Menús de ambas toolbars dentro del viewport y Escape con restore; revisión de sticky y bleed en ambos dashboards.
- Regresiones existentes de aprobación, exportación, drawer, error/reintento, temporales, inputs, comparativos e historial.
- E2E con API, worker, PostgreSQL 17, PostgREST y motores reales: escritorio y móvil verifican el catálogo, toolbars, carga, Assignment, Scheduling y aprobaciones. Las ejecuciones de QA usan exclusivamente la infraestructura local desechable.

Desde `backend`, usando las herramientas ya instaladas:

```bash
python -m unittest discover -s tests -v
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
  .browser-venv/bin/python -m unittest discover -s tests/browser -p test_navigation.py -v
DATION_SQL_TEST_CONTAINER=<postgres17-desechable> python -m unittest discover -s tests/integration -v
DATION_BROWSER_PYTHON=/workspace/Dation/backend/.browser-venv/bin/python \
  CHROMIUM_EXECUTABLE=/usr/bin/chromium python tests/e2e/run_suite.py
```

La entrega exige suites completas y CI verde del head exacto. Después del merge se valida CI de main y el despliegue automático, plantilla, assets, salud, acceso privado y QA productiva de lectura con hashes de los registros consultados antes/después.

## Límites del cambio

Los dashboards sólo cambian en geometría de toolbar y shell necesario para su bleed. No cambian contenido, KPI, gráficos, tablas, timelines, IA, comparativos, exportación de datos ni renderers de resultados. No hay cambios de solver, API, esquema de Supabase, rutas, validación de datasets, lifecycle de casos, lógica de configuración o semántica de aprobación. No se añaden dependencias ni nuevos `!important`.
