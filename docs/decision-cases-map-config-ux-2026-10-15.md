# Decision Cases, mapa y confirmación — implementación del 15/10/2026

## Resultado

Se implementaron los cinco cambios del documento `Dation_PROMPT_PRO_Codex_Mapa_Decision_Cases_UX_2026-10-15.md` sobre `main` limpio, commit base `7c1141221f3782c133b11136420307cdd3bb035e`. La intervención conserva el router, el motor, los payloads de ejecución y el esquema de Supabase.

El botón DC abre siempre el selector existente; el caso actual no se puede reabrir desde ese picker. Los casos activos y completados se obtienen de la API, con paginación y deduplicación; los archivados quedan fuera del selector normal. Las confirmaciones de D1/D2 usan el mismo controlador y aparecen sobre la configuración.

## Causa raíz encontrada

- **Selector DC:** el acceso explícito y la navegación global compartían la optimización `cases.length === 1 → openCase(...)`. En Chromium, un click con un solo caso repetía la hidratación de ese caso aunque la URL final pareciera igual. Ahora `forceSelector` separa ambas intenciones; la navegación global conserva sus atajos.
- **Aviso nuevo caso:** bastaba un `stale_predecessor` truthy. Una referencia local obsoleta podía producir un aviso sin transición real. Además, reemplazar los dos archivos podía encadenar un caso local intermedio, y los casos no se persistían hasta ejecutar D1. Ahora el mapa registra el nuevo caso con la API existente, conserva el último predecessor durable y verifica ID y firma mediante una lectura del servidor. El aviso requiere además el evento de sustitución actual; reabrir un histórico no lo genera. La relación de lineage queda persistida, aunque el aviso transitorio ya no se muestre.
- **Highlight:** el `summary.decision-config-case__summary` medía radio `0px`, frente a `24px` del contexto, y recibía un outline de foco de 3 px. D1/D2 también mantenían resaltados propios con desplazamiento. Ahora el contexto y su summary comparten una propiedad de radio del componente; usar solamente `inherit` en el summary nativo no produjo el radio del host en Chromium. El resaltado de secciones usa un pseudo-elemento con radio heredado, sin transformar el card ni interceptar clicks. Reduced motion conserva el borde sin pulso y usa scroll inmediato.
- **Review D1/D2:** ambos ya eran dialogs nativos y ninguno cambiaba view/URL antes de confirmar. El fondo de D2 era opaco (`rgb(15, 27, 36)`), lo que ocultaba por completo la configuración. Se eliminó ese override y la geometría duplicada; ambos usan el backdrop común `rgba(0,0,0,.64)`. El controlador compartido restaura foco, cierra al desmontar y bloquea doble confirmación antes de llamar al owner de ejecución.
- **Hero:** los tokens exteriores ya coincidían: mínimo 220 px, padding 26 px, gap 24 px y radio 24 px en desktop. Los overrides del panel derecho del mapa elevaban su altura real a **397,44 px**, frente a **261,42 px** del Data Pack. Se retiraron esos overrides y se compactó el copy de ayuda. El mapa pasa a **255,42 px** sin altura fija; la diferencia natural restante es de 6 px. En móvil el contenido crece sin recortes.

## Archivos modificados

Rutas relativas al repositorio:

- `backend/app/static/js/dispatch/traceability-controller.mjs` — modo picker explícito, consulta de activos/completados, paginación, deduplicación y error sin navegación.
- `backend/app/static/js/dispatch/traceability-ui.mjs` — caso actual deshabilitado, estado real, mensaje de caso único y modal compacto.
- `backend/app/static/js/dispatch/decision-case.mjs` — lineage entre sustituciones y función pura de aviso verificado.
- `backend/app/static/js/dispatch/workspace.mjs` — registro temprano mediante API, actualización de URL con History API, verificación del predecessor e integración del picker.
- `backend/app/static/js/dispatch/decision-map.mjs` — copy del hero y banner informativo con referencias a ambos casos.
- `backend/app/static/js/dispatch/decision-config-ui.mjs` — controlador compartido de revisión y primitive de atención.
- `backend/app/static/js/dispatch/assignment-config.mjs` — resumen con caso, revisión compartida y confirmación protegida.
- `backend/app/static/js/dispatch/scheduling-config-v2.mjs` — mismo contrato de revisión y atención, conservando configuración y opciones de Scheduling.
- `backend/app/static/css/dispatch.css` — eliminación de overrides internos del hero del mapa.
- `backend/app/static/css/decision-map-case-v2.css` — banner de transición con roles informativos dark.
- `backend/app/static/css/decision-trace-v3.css` — composición compacta del selector con un solo caso.
- `backend/app/static/css/dation-design-system.css` — borde de atención que hereda el radio y respeta reduced motion.
- `backend/app/static/css/assignment-config-v2.css` — radio compartido del contexto y geometría común de dialogs.
- `backend/app/static/css/scheduling-config-v2.css` — retirada del backdrop opaco y del layout duplicado de revisión.
- `backend/app/static/css/scheduling-config-shared-phase2.css` — retirada del resaltado con transform y del ancho duplicado.
- `backend/tests/test_decision_case.mjs` — reglas de transición, primer caso, histórico, predecessor inexistente y reemplazo de ambos archivos.
- `backend/tests/test_traceability_phase3.py` — contrato actualizado para ambos estados del listado.
- `backend/tests/browser/test_navigation.py` — ocho regresiones nuevas y fixtures paginadas con estados reales; adaptación de los tests del selector al caso actual deshabilitado.
- `backend/tests/e2e/browser_journey.py` — caso durable antes de D1, selector único, foco y ambos reviews sin navegación ni admisión anticipada, sobre API/worker/DB reales desechables.
- Este informe.

## Cambios funcionales

1. Click en DC abre un picker incluso con un único caso. Cerrar no cambia URL, view, Data Pack ni historial de navegación, y devuelve foco al trigger.
2. Elegir otro caso guarda el borrador actual y usa `openCase(target, 'logistics-map', null)`. La hidratación restaura el Data Pack y los nodos desde el servidor; Back/Forward mantienen el contexto.
3. El primer caso validado se registra al abrir el mapa, antes de crear cualquier corrida. El registro usa el mismo UUID y endpoint ya disponibles; no se crea una lista paralela en almacenamiento local.
4. El banner explica un cambio real de Data Pack y menciona sucesor y predecessor. Un histórico o una referencia inválida no simula un caso recién creado.
5. Hero, foco contextual, atención de secciones y dialogs siguen sus contratos compartidos. D1/D2 muestran el caso y su resumen específico; sólo **Ejecutar decisión** inicia el flujo existente de ejecución/dashboard.

## Tests ejecutados

Comandos desde `backend`, con el entorno Python 3.13/Node 22 activado:

```bash
python -m unittest discover -s tests -v
node --test tests/test_*.mjs tests/test_*.js
CHROMIUM_EXECUTABLE=/usr/bin/chromium DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python \
  .browser-venv/bin/python -m unittest discover -s tests/browser -p test_navigation.py -v
DATION_SQL_TEST_CONTAINER=<contenedor PostgreSQL 17 desechable propio> \
  python -m unittest discover -s tests/integration -v
CHROMIUM_EXECUTABLE=/usr/bin/chromium python tests/e2e/run_suite.py
python -m compileall -q app main.py worker.py
python -m pip check
```

También se verificaron sintaxis de los 56 módulos/scripts de `static/js`, import graph y `git diff --check`. Los comandos oficiales y las auditorías de dependencias se mantienen en `.github/workflows/backend-tests.yml`; no se deshabilitó ningún gate.

La entrega se valida con **554 casos**: 350 Python, 41 Node, 110 Chromium, 46 PostgreSQL y 7 E2E reales. La primera pasada local de Chromium tuvo un timeout de arranque de 6 s mientras E2E ejecutaba optimización concurrentemente; se conservó el fallo para diagnóstico y se repitió la suite completa sin ese proceso concurrente, sin retirar aserciones.

## QA en navegador y revisión visual

- Caso único: picker, badge actual, CTA deshabilitado, mensaje sin otros casos, Escape y foco; ninguna llamada redundante a `openCase`.
- Activo + completado: cambio único, hidratación, Data Pack correcto, Back/Forward, borrador separado y ningún hard reload.
- Archivados y error de listado: exclusión o error local en el modal; el mapa permanece abierto.
- Plataforma limpia y sustitución real: registro previo a la corrida, ausencia de banner inicial, lineage conservado y aviso sólo durante la transición verificada.
- D1/D2: cancelar y Escape conservan configuración; URL/view no cambian al revisar; doble click confirma una sola ejecución. El E2E real incluye carga de CSV, D1, aprobación, D2, error temporal, reconfiguración e historial móvil.
- **60 estados visuales** a 1440, 1280, 1024, 768, 390 y 360 px, incluyendo viewport bajo de 360 × 250: Data Pack, mapa, pickers de uno/varios casos, contexto, atención y review de ambas decisiones. Sin overflow ni fallos de contraste del auditor HTML utilizado.
- Capturas revisadas del hero, picker y revisión D2: geometría consistente y configuración reconocible detrás del modal.
- La comprobación productiva usa los casos y corridas que existan en ese momento, con GET y preflight/preview computacional. La ejecución final se prueba en el entorno desechable; en producción se cancela el review y se comparan hashes de los registros leídos antes/después.

## Riesgos / deuda residual

- El registro del caso ocurre ahora al abrir el mapa. Si esa escritura falla, se muestra el error recuperable de la vista; reintentar conserva el UUID. No requiere migración.
- El aviso de transición no se repite después de reabrir o recargar un caso persistido; la referencia al predecessor sigue conservada en el estado durable.
- Las pruebas visuales y de teclado acreditan Chromium y reflujo equivalente. No constituyen certificación de otros motores, lectores de pantalla o interfaces nativas de todos los sistemas operativos.
- El QA de cambio entre varios casos usa datos sintéticos y E2E desechable; si producción sólo tiene un caso, no se inventan casos de negocio para realizar esa comprobación.

## Commits y despliegue

El SHA del commit funcional, PR, CI de head y main, build y revisiones productivas se entregan junto con este informe al terminar la publicación. Se exige CI verde sobre el head exacto antes de integrar y se verifica el contenido real de los assets después del despliegue. El kit de reinicio de Supabase generado previamente no se ejecuta como parte de esta tarea.
