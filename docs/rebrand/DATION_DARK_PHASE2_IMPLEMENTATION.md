# Dation — Fase 2: Home y Overview

14 de octubre de 2026. Base productiva: `9eb1d2c498459ab5e9833981862e80582f7c3298` (Fase 1). Alcance: secciones 34–39 del prompt Dark Rebrand / Product UX Grow-Up y wireframes de Fase 0.

## A. Diagnóstico

Home y Overview aún tenían el boundary claro temporal. Home repartía reglas entre `app.css` y su hoja específica; Overview acumulaba varias versiones de las mismas superficies. Oscurecer sólo el hero dejaba cards claras y copy de apoyo incompatible con los tokens globales. La caja final de Overview repetía la invitación del hero.

## B. Wireframe / intención

Home presenta una explicación breve y dos cards DDA: Logística disponible y Producción próxima. Overview presenta su hero compacto con los dos CTA, cuatro pasos, variables del motor, cadena informativa, datos/resultados/límites y FAQ. La identidad Dation permanece. No hay alturas fijas que recorten contenido.

## C. Implementación

- Home: tiles y cards dark; Logística usa superficie elevada, borde teal y glow cyan tenue. Producción conserva texto legible, fondo oscuro y disponibilidad explícita; no se atenúa la card completa ni se convierte en control. La card activa conserva su botón y hooks de navegación.
- Heroes: contrato común de Fase 1, copy reducido y paneles laterales compactos. A 1100 px o menos se ocultan los visuales de apoyo redundantes; la explicación y acciones permanecen. En móvil, los CTA ocupan filas completas.
- Overview: superficies nativas dark para pasos, chips, cadena, resumen y FAQ. Las seis variables tienen etiquetas visibles: tres optimizan hoy y tres están en consolidación. La cadena no muestra estados ni acciones de un caso.
- Se elimina `.dda-landing__final`, su copy y sus estilos. Se conservan los dos CTA y su contrato: Map deshabilitado sin casos, apertura directa con un caso y selector existente con varios, incluso con caso seleccionado. Nueva decisión limpia el contexto actual y conserva drafts. No se altera la lógica de generaciones, disponibilidad, BFCache ni navegación.
- FAQ: cuatro `details/summary` nativos, foco visible, apertura con Enter/Espacio y respuesta legible. La entrada visual respeta reduced motion; no se oculta contenido por falta de IntersectionObserver.
- Propiedad y caché: Home queda en `home-dda.css`; se retiran sus reglas duplicadas de `app.css`. Overview queda en `dda-logistics-landing.css`, sin acumular overrides. Sólo estas dos vistas abandonan el bridge claro. URLs de assets afectados versionadas como `dark-home-overview-v1`.

## D. Archivos exactos

| Propósito | Archivo |
|---|---|
| DOM, copy y assets versionados | `backend/app/templates/app.html` |
| Composición Home | `backend/app/static/css/home-dda.css` |
| Retirada de reglas Home duplicadas | `backend/app/static/css/app.css` |
| Composición Overview | `backend/app/static/css/dda-logistics-landing.css` |
| Rol decorativo de glow | `backend/app/static/css/tokens.css` |
| Etiquetas de variables | `backend/app/static/js/dda-logistics-landing.js` |
| Contratos de copy y assets | `backend/tests/test_frontend_contract.py` |
| Regresiones de interacción y responsive | `backend/tests/browser/test_navigation.py` |
| Auditoría de contraste renderizado | `backend/tests/browser/theme_audit.js` |
| Estado y aceptación | Este informe y `docs/rebrand/DATION_DESIGN_SYSTEM_V1.md` |

## E. Tests

Desde `backend/`, tras activar `/workspace/.dation-cloud/activate.sh`:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_*.js tests/test_*.mjs
CHROMIUM_EXECUTABLE=/usr/bin/chromium .browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_navigation.py'
DATION_BROWSER_PYTHON="$PWD/.browser-venv/bin/python" CHROMIUM_EXECUTABLE=/usr/bin/chromium python tests/e2e/run_suite.py
python -m compileall -q app main.py worker.py
python -m pip check
```

Resultado esperado y exigido antes de publicar: **349 Python, 37 Node, 71 Chromium y 7 E2E reales**, más **46 SQL en CI: 510 casos**. Se verifica también sintaxis de JavaScript y `git diff --check`.

Los dos casos nuevos de Chromium comprueban contraste de texto renderizado, superficies, densidad del hero, responsive de CTA, foco y activación de la card, Producción informativa, etiquetas de variables, cadena sin estado operativo y FAQ por teclado. El helper calcula luminancia sRGB sobre colores computados, compone transparencias y muestrea gradientes de acción; excluye controles nativos inactivos y contenido no renderizado, pero incluye el texto informativo de Producción. Las regresiones anteriores cubren cero/uno/varios casos, generaciones obsoletas, drafts, BFCache y recuperación.

El E2E ejecuta API, worker, base de datos, storage y navegador sobre infraestructura desechable; no escribe en Supabase productivo. La comprobación posterior al merge exige CI del head exacto, Cloud Build correcto y CI de main; la evidencia de ejecución y tráfico se registra en el PR y `/workspace/dation-audit/rebrand-phase2-production-final.json`.

## F. Visual QA

Cinco anchos: **1440, 1280, 1024, 768 y 390 px**. Se registran Home, Overview y FAQ abierta; las capturas y mediciones están en `/workspace/dation-audit/rebrand-phase2-visual/`. El estado final exige cero desbordamientos horizontales y cero errores JavaScript.

Alturas observadas (px), sin fijar el alto en CSS:

| Ancho | Home | Overview |
|---|---:|---:|
| 1440 / 1280 | 234.8 | 220 |
| 1024 / 768 | 220 | 220 |
| 390 | 286.8 | 309.2 |

Home ocupa un 6.7 % más de alto que Overview en escritorio. En móvil se preserva el contenido, con ambas acciones dentro de la primera pantalla de 844 px. El contraste mínimo de texto observado es **5.517:1 en Home** y **6.141:1 en Overview**, incluida la FAQ abierta; no se detectan fallos AA, errores JavaScript ni desbordamientos en los 15 estados.

La auditoría exige WCAG AA para cada texto renderizado: 4.5:1 normal y 3:1 grande. No equivale a una certificación de gráficos o páginas pendientes. La QA productiva verifica por hash el template y 15 assets, privacidad, readiness, dependencias y heartbeat del worker; bloquea escrituras persistentes y compara hashes de casos, ejecuciones y comparativas antes/después.

## G. Deuda / riesgos

El bridge claro continúa en Data Pack, Map, Config, dashboards y vistas auxiliares. Su migración pertenece a fases posteriores. No se modifica `analysis_depth`, Action Bars, menús de toolbar ni charts. Los visuales de apoyo de hero son redundantes y se ocultan en pantallas pequeñas; las instrucciones operativas permanecen en las secciones siguientes.

No hay cambios de dependencias, backend, esquema, permisos ni datos. Rollback: revertir el merge y publicar ese commit mediante Cloud Build; no requiere rollback de base de datos.

## H. Gate

**FASE 2 COMPLETA — LISTA PARA FASE 3**, una vez superadas las comprobaciones registradas en el PR. La fase siguiente corresponde a Data Pack: composición, superficies y Action Bar según la especificación. No iniciar Fase 3 automáticamente.
