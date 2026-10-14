# Dark Rebrand / Grow-Up — Fase 6: QA responsive y accesible

## A. Diagnóstico

La auditoría inicial recorrió ocho pantallas a 1440, 1280, 1024, 768 y 390 px. Encontró nueve textos de Map por debajo de AA, dos botones de navegación sin nombre accesible al compactarse la sidebar y controles tapados al recorrer con Tab. El barrido ampliado detectó filtros guardados con cabeceras light inyectadas por JavaScript, selector de casos e historial todavía light, decisiones superpuestas en la rail móvil de Assignment y el composer de chat recortado por su contenedor. En Scheduling el launcher podía tapar Enviar. Faltaban estilos de autofill y respeto de movimiento reducido en ECharts.

## B. Intención y alcance

La lectura, el foco y la última acción deben seguir disponibles en escritorio, tablet, móvil y alturas reducidas. Se mantienen las pantallas, opciones, cálculos, navegación, aprobaciones, exportaciones, historial y comparativa existentes. No cambia la API, el motor, Supabase, los permisos, las dependencias ni el contrato essential de Fase 4. El workspace sigue siendo privado compartido.

Las barras dejan de ser sticky cuando el viewport tiene 540 px de alto o menos. La rail de Assignment apila las decisiones por debajo de 760 px, con su estado y nombre completos. No se ocultan datos operativos para hacerlos entrar.

## C. Implementación

Map y sus estados usan roles oscuros en sus propietarios actuales. Se migran también los estilos del selector de casos, historial y acciones de trazabilidad; se retiran sus boundaries light demostrados. Los controles de filtro expandido/colapsado se corrigen en `assignment-filter-collapse.mjs`, donde se inyectaba el fondo claro. Se mantienen las jerarquías, conexiones, IDs, fuente aprobada y callbacks.

La toolbar mide su altura y la de topbar para reservar márgenes de foco. Scope libera medidas y observadores al navegar. Upload incluye summary y controles nativos en sus márgenes; Config reserva el espacio de su barra inferior. Los chips del footer desplazan sólo su contenedor horizontal al recibir foco. Los diálogos de Config tienen nombre accesible, Tab/Shift+Tab contenidos y Escape con restauración. Los botones de sidebar conservan nombre aunque su texto deje de mostrarse.

Chat usa una columna flexible con scroll local y thread adaptable; textarea y Enviar quedan alcanzables. En alturas bajas aprovecha el viewport con scroll, conservando su cierre. Chat usa capa 90 y launcher 70 en ambas decisiones. ECharts lee `prefers-reduced-motion`, responde al cambio de preferencia y libera el listener al salir, sin alterar series ni cálculos.

El DS añade foco visible para enlaces, summary y elementos con tabindex, y autofill mediante color de texto, caret y relleno oscuro interior. No se desactiva el autofill del navegador. Los inputs conservan su valor, validación y semántica nativa.

## D. Cobertura y contratos

Ocho regresiones Chromium nuevas verifican: 40 pantallas con contraste/nombres del árbol AX/overflow; Tab y Shift+Tab en todas las pantallas; chips y estado del footer móvil; search, number, checkbox, range y autofill; date picker y select de Scheduling; movimiento reducido y cleanup real del gráfico; reflujo equivalente a 200/400%; chat y modales con teclado. Se conserva la regresión previa de menús exclusivos, historial, JSON/CSV, retry e idempotencia, comparativa, cold/warm navigation y respuestas tardías.

El test de autofill fuerza el pseudoestado Chromium mediante CDP sobre un campo real, sin datos personales. El date input invoca `showPicker()`, conserva su valor ISO y comprueba esquema oscuro e indicador; se comprueba después el error de ventana invertida y la revisión válida. Ninguna de estas pruebas crea corridas productivas.

## E. Validación

Comandos desde `backend`, activando `/workspace/.dation-cloud/activate.sh`:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python .browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_navigation.py'
DATION_BROWSER_PYTHON=/workspace/Dation/backend/.browser-venv/bin/python CHROMIUM_EXECUTABLE=/usr/bin/chromium DATION_E2E_ARTIFACTS=/workspace/dation-audit/rebrand-phase6-e2e python tests/e2e/run_suite.py
```

Gate: 349 Python, 40 Node, 99 Chromium, 46 SQL sobre PostgreSQL 17 y siete E2E reales desechables: **541 casos**. También compilación Python, sintaxis de 64 scripts/módulos frontend, `pip check`, auditorías de dependencias en CI y `git diff --check`. Se exige verde en el head exacto del PR y en el merge de main. Las escrituras, reinicios y recuperación del worker se prueban sólo en API/base/storage desechables.

## F. QA visual y producción

Matriz local: 165 estados en cinco anchos, incluyendo Inicio, Overview, Upload vacío/listo/inválido, Map/contexto, selector de casos, historial, drawers de validación/guía/biblioteca, Config custom/filtros/review/reglas, ambos dashboards/menús/drawer/chat y errores terminales. Capturas de escritorio, tablet y móvil e informe en `/workspace/dation-audit/rebrand-phase6-visual/`. Se revisan alineación, espacio, contraste compuesto, overflow, capas y sticky. La comprobación de foco usa puntos interiores para detectar controles parcialmente tapados, además de outline y viewport.

El reflujo a 200/400% usa CDP con un lienzo físico de 1440 × 1000 y viewport CSS 720 × 500 / 360 × 250, con pixel ratio 2 / 4. Acredita el reflujo y acceso a controles en esas métricas; no certifica la interfaz externa de zoom ni los pickers de todos los sistemas operativos. Esta ejecución corresponde a Chromium en Linux; no sustituye revisión con lectores de pantalla ni otros motores. El resultado no se presenta como una certificación WCAG completa.

La publicación usa Cloud Build enlazado a GitHub. Se verifican source SHA, cuatro pasos, revisiones y tráfico, template y assets por SHA-256, acceso privado, readiness, dependencias, ETag y heartbeat del worker. La QA productiva recorre datos existentes, Map completo, historial/selector y ambos dashboards a cinco anchos, además de comprobar foco, chat y reflujo. Sólo permite GET y preflight/preview de cálculo; compara hashes de casos, corridas y comparativa antes/después. Las solicitudes y resultados concretos quedan en el PR y `rebrand-phase6-production-final.json`.

## G. Deuda y riesgos

Se migraron propietarios que la QA encontró con estilos mezclados; no se borraron reglas ni compatibilidad por su apariencia de antigüedad. La consolidación y eliminación de código sin consumidores corresponde a Fase 7. Se conserva el boundary de review legacy hasta auditar sus consumidores. El estado técnico `analysis_depth` y los históricos permanecen; el efecto de essential medido en Fase 4 sigue vigente.

Rollback: revertir el merge y desplegar ese commit por Cloud Build. No hay migraciones ni cambios de datos que revertir. El entorno reutilizable conserva instalación, red y bindings y fija el commit publicado; guardar el borrador no equivale a publicar el entorno.

## H. Gate

**FASE 6 COMPLETA — LISTA PARA FASE 7** sólo después de suites verdes, integración y verificación productiva del commit exacto registradas en el PR. No iniciar Fase 7 automáticamente.
