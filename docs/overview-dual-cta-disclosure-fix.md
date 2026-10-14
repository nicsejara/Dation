# Overview Dual CTA y Decision Case Disclosure

Implementación del adjunto `Dation_PROMPT_PRO_Overview_DualCTA_Disclosure_Fix.md`, 14 de octubre de 2026.

## A. Causa

El Overview resolvía un único botón contextual entre Datos y Map. Esto impedía elegir una decisión nueva cuando ya había casos y omitía el selector si existía un caso seleccionado.

En Config, el `<details>` ya tenía `display:block`, pero su cuerpo conservaba una grilla horizontal. Los hijos reutilizados heredaban `grid-area:identity/action/pack` de `decision-trace-v3.css`: generaban columnas implícitas, padding de la card anterior y márgenes del botón. A 1440 px, el cuerpo medía 1122 px pero el Data Pack sólo 649.5 px; cada archivo quedaba en unos 292 px. Cambiar sólo el wrapper no solucionaba esa herencia.

La misma hoja agregaba etiquetas de validación absolutas y reservaba 90 px del encabezado de archivo. Además, el párrafo informativo del Overview tenía `white-space:nowrap` desde 901 px; el nuevo test detectó overflow en 1280 y 1024 px. Se retiró esa restricción.

## B. Overview

- Dos botones estáticos en el Hero: **Iniciar nueva decisión →** y **Ir al Decision Map →**. No se agregan botones inferiores ni copias móviles.
- Nueva decisión siempre habilitado; llama al `startNewDecision()` existente, que guarda el draft anterior y limpia el contexto antes de abrir Datos. El fallback a Datos sólo se usa si no existe ese método.
- Map siempre visible, con `disabled`, `aria-disabled`, cursor y apariencia correspondientes cuando no hay caso seleccionado ni casos disponibles. Un error de lectura mantiene el estado prudente y explica que no se pudo comprobar disponibilidad.
- `syncHeroActions()` consulta el workspace y `listDecisionCases()`, ignora respuestas antiguas y actualiza al entrar, recibir cases-ready o restaurar BFCache. Las etiquetas no cambian.
- Map usa `openDecisionMap({trigger:map})`: un caso abre directamente; varios muestran el selector existente, incluso con un caso seleccionado. Se elimina el resolver contextual anterior.
- Desktop conserva los botones contiguos; móvil los apila a todo el ancho.

## C. Disclosure compartido

`decisionCaseCard()` conserva `<details>/<summary>` nativos, cerrado por defecto y operable con Enter/Space. El cuerpo tiene tres niveles: identidad del caso; encabezado de Data Pack con Cambiar datos; cards Orders/Fleet.

El wrapper es bloque sin padding. Summary y cuerpo ocupan todo el ancho; los resets de área, padding y margen se limitan al disclosure, sin cambiar las cards legacy. Las cards existentes se reutilizan en una grilla `repeat(2,minmax(0,1fr))`, que pasa a una columna debajo de 720 px. Los nombres largos conservan nombre completo en `title`, elipsis central y truncamiento CSS; el contenido usa `min-width:0`.

Las etiquetas `Validado` utilizan el markup inline existente y un perfil con cero errores. Se desactivan los pseudo-elementos absolutos que afirmaban validación sin mirar el perfil. No se cambia validación de datos ni sus motores. Copiar ID, feedback y Cambiar datos mantienen sus handlers y no alternan el summary.

Assignment y Scheduling comparten la corrección. El Map pasó la revisión en los cinco anchos con su layout actual; no necesitó cambios. No se modifican API, backend funcional, engine, Supabase, migraciones, dependencias o infraestructura.

## D. Archivos modificados

1. `backend/app/templates/app.html`
2. `backend/app/static/js/dda-logistics-landing.js`
3. `backend/app/static/css/dda-logistics-landing.css`
4. `backend/app/static/js/dispatch/decision-config-ui.mjs`
5. `backend/app/static/css/assignment-config-v2.css`
6. `backend/tests/browser/test_navigation.py`
7. `backend/tests/e2e/browser_journey.py`
8. `backend/tests/test_frontend_contract.py`
9. `backend/tests/test_landing_navigation_contract.py`
10. `backend/tests/test_traceability_phase3.py`
11. `docs/overview-dual-cta-disclosure-fix.md`

## E. Validación

Activar `/workspace/.dation-cloud/activate.sh`. Desde `backend`:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.js tests/test_*.mjs
DATION_RUNTIME_PYTHON=/workspace/Dation/.venv/bin/python CHROMIUM_EXECUTABLE=/usr/bin/chromium .browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_navigation.py'
DATION_BROWSER_PYTHON=/workspace/Dation/backend/.browser-venv/bin/python CHROMIUM_EXECUTABLE=/usr/bin/chromium DATION_E2E_ARTIFACTS=/tmp/dation-e2e-artifacts python tests/e2e/run_suite.py
python -m compileall -q app main.py worker.py
python -m pip check
```

Resultados: 349 pruebas Python, 37 Node, 66 Chromium y 7 E2E reales. Compilación, sintaxis de todos los módulos JavaScript, consistencia de dependencias y `git diff --check` pasan. CI añade las 46 pruebas SQL y las auditorías de los locks; la evidencia de CI y publicación queda en el PR.

El E2E inicia desde Overview sin casos, carga archivos, ejecuta/aprueba Assignment, recupera un Scheduling fallido con otra corrida y verifica historial. Después abre Map con un único caso e inicia una decisión nueva: contexto limpio, draft retenido, caso sin cambios y ningún POST adicional de ejecución. El harness usa PostgreSQL, PostgREST, API, worker y Chromium reales aislados; no utiliza credenciales productivas.

Se prueban y capturan Overview sin casos, con caso activo y selector múltiple; Assignment/Scheduling abiertos y cerrados; y Map. Anchos: 1440, 1280, 1024, 768 y 390 px. Los archivos tienen nombres deliberadamente largos. Los tests verifican ancho, orden, columnas, ausencia de overflow, teclado, copia del ID completo, cambio de datos, validación basada en perfil, respuestas fuera de orden, BFCache y conservación de drafts.

| Ancho | Archivo en Assignment/Scheduling | Columnas |
|---|---|---|
| 1440 | 533 px | 2 |
| 1280 | 453 px | 2 |
| 1024 | 342 px | 2 |
| 768 | 301 px | 2 |
| 390 | 252 px | 1 |

Evidencia local: `/workspace/dation-audit/dual-cta-*`. Las capturas son de fixtures propias. La revisión productiva posterior usa assets/API reales y casos existentes con sólo lecturas y previews de cálculo; no crea casos, corridas, aprobaciones ni modifica datos de negocio. La fuente, CI, Cloud Build, revisiones al 100 %, hashes, readiness y resultados de esa revisión se registran en el PR.

## F. Confirmaciones

- Nueva decisión = siempre disponible.
- Decision Map = visible y disabled sin cases.
- Decision Map = enabled con cases.
- Disclosure = sin superposición entre identidad, acción y archivos.
- Assignment config = OK.
- Scheduling config = OK.
