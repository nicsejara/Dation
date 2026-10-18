# Fase 1 · Identidad y Platform foundation

Base: Fase 0 `2f82015c1477fb0c8f247c94b18637ccc19a6c71`, integrada mediante PR #73 (`ebe82937960fdd9198417459f0e1fb807450f843`) con CI verde. Fecha de referencia: 2026-10-17, America/Buenos_Aires.

## Resultado

Foundation visual implementada sobre el stack actual, sin reescribir el framework, el DDA o el shell. Se conservan todos los valores y reglas anteriores de tokens/design system y se añaden roles/primitives optativos bajo `.d-platform`. El catálogo, las category pills, los Hero/toolbar/Contexto/KPI D1/D2 y sus métricas conservan su contrato.

Primer consumidor real: panel técnico de Configuración existente, con header/card/type/status y ayuda contextual. Sus IDs, textos técnicos, consultas y handlers de actualización se preservan. No es la nueva página de settings de workspace, ni incluye administración, Auth, sidebar o rutas nuevas. La ayuda usa el mismo helper accesible comprobado en la galería y se libera mediante el scope de la vista.

## Archivos y decisiones

| Archivo | Cambio |
|---|---|
| `backend/app/static/css/tokens.css` | Roles nuevos de tipo, spacing, controles, formularios y tabla; aliases/valores históricos intactos |
| `backend/app/static/css/dation-design-system.css` | Type, buttons, fields, native choices, estados, autofill y motion/forced colors bajo scope optativo |
| `backend/app/static/css/platform-components.css` | Page/header, surfaces, badges, table/filter, empty/error, skeleton, modal/drawer/popover/menu/tooltip/toast/sidebar item |
| `backend/app/static/js/platform/components.mjs` | Dropdown/disclosure y native dialog con keyboard, foco, posición y cleanup; sin fetch ni estado de negocio |
| `backend/app/static/js/app.js` | Montar únicamente la ayuda contextual de Settings dentro del lifecycle existente |
| `backend/app/templates/app.html` | Link de componentes y adopción acotada en Settings; las vistas DDA no optan por el nuevo scope |
| `backend/tests/browser/fixtures/platform-foundation.html` | Galería sintética interna, sin ruta productiva ni API |
| `backend/tests/browser/test_platform_foundation.py` | Siete pruebas de geometría, semántica, interacción, contraste y lifecycle |
| `backend/tests/browser/test_platform_settings.py` | Consumidor real, estados/refresco, ayuda, navegación, cinco widths y contexto DDA intacto |
| `docs/platform-mvp/DESIGN_SYSTEM.md` | Contrato reusable, ejemplos, semántica, límites y ownership |
| `docs/platform-mvp/README.md`, `04-design-system.md`, `IMPLEMENTATION_STATUS.md` | Registro de avance y próximo gate |

No se modifican motores, API, Supabase, schemas, Storage, dependencia o workflow. No se crean capacidades futuras ni una galería visible al cliente. Se mantiene la UI dark actual; la mayor parte de la foundation queda disponible para las páginas de fases siguientes.

## Geometría, estados y accesibilidad

- Page header responsive y copy largo; scale 4/8, type jerárquica y superficies existentes.
- Botones primary/secondary/ghost/danger/icon y tamaños, con hover/active/focus/disabled/loading. Workflow conserva su geometría propia.
- Labels nativos, helpers/error y ARIA; inputs text/password/search/date/select/textarea y checkbox/radio/switch nativos. Target de labels/controles ≥40 px en móvil.
- Tabla dentro de región desplazable accesible, sticky headers, sort y estados; sin overflow de página.
- Dropdown con flechas/Home/End/Tab/Escape/outside, foco de retorno y remount limpio. Modal/drawer nativo con trap/close/scroll; reapertura antes de un close pendiente no pierde el foco.
- Contraste mínimo medido en la galería: texto 5,82:1, bordes de inputs 4,34:1 y foco 8,34:1. Estados disabled se distinguen sin prometer contraste de controles activos. Se conserva reduced motion y se modela reflow de zoom 200%.

## Baseline y regresión

Se capturó el árbol de aplicación de Fase 0 desde Git para evitar contaminar el antes con cambios concurrentes. Misma pareja de datasets/case/runs sintéticos, 1440/1280/1024/768/390 px y nueve vistas: Inicio, Overview, Data Pack, mapa, configuración D1/D2, dashboard D1/D2 y Settings.

45 estados antes/después sin overflow ni errores JS. Se compararon exactamente 310 elementos en 40 estados fuera de Settings: cero diferencias de geometría, tipografía, padding, border/radius, color/background y contenido capturado. Settings es la adopción visual intencional, con prueba de consumidores/refresco/contexto aparte. Capturas y JSON de medidas se guardan en `/workspace/dation-audit/platform-mvp-phase1`.

Pruebas locales de esta fase:

| Suite | Resultado |
|---|---:|
| Python unittest | 350 aprobadas |
| Funciones Python fuera de discover | 13 aprobadas |
| Node focalizado | 59 aprobadas |
| Chromium foundation | 7 aprobadas |
| Chromium Settings real | 1 aprobada, cinco widths |
| Chromium regresión DDA/catálogo | 16 aprobadas |

Se conserva el workflow normal de CI, que ejecuta también la suite browser completa, PostgreSQL y E2E reales. La CI de Fase 0 se identifica por separado; el resultado del nuevo commit debe consultarse en su PR/checks. No se usa una CI anterior como prueba del código nuevo. No se repiten manualmente SQL/LLM real para una foundation sin cambios de backend; el workflow habitual sí conserva sus gates automáticos.

Durante verificación se detectaron y corrigieron tres problemas concretos: área táctil pequeña de sort, aspecto hover de sidebar nativa disabled y ausencia inicial de consumidor runtime para el módulo de interacción. El import graph vuelve a pasar; la ayuda de Settings es un uso real, no un import vacío para silenciar esa prueba.

## Comandos

Desde `backend`, con Python del backend, Node y Chromium configurados:

```bash
python -m unittest discover -s tests -v
node --test tests/test_home_dda_catalog.mjs tests/test_navigation.mjs \
  tests/test_lifecycle.mjs tests/test_assignment_dashboard_v2_selectors.mjs \
  tests/test_assignment_executive_kpis.mjs tests/test_scheduling_dashboard_v21_selectors.mjs \
  tests/test_dispatch_upload_selectors.mjs
.browser-venv/bin/python -m unittest discover -s tests/browser -p 'test_platform*.py' -v
```

Las 13 funciones se ejecutan con el runner explícito documentado en [baseline](05-baseline-and-ci.md). Las 16 regresiones reutilizan métodos de `NavigationTests`: geometría D1/D2, herramientas/approve/export/details, config/map en cinco widths, catálogo y navegación, contexto Data Pack, review/confirm y viewport bajo/teclado. La suite completa de CI las incluye.

`DATION_FOUNDATION_ARTIFACTS` permite elegir carpeta de capturas y mediciones. La galería toma el orden CSS real del template. La prueba de Settings usa API sintética, verifica status refresh/ayuda y rechaza mutaciones de negocio; no genera runs en producción.

## Seguridad, límites y siguiente fase

Auth/tenancy siguen pendientes de Fase 2. Los estilos no conceden permisos. La aplicación conserva su workspace privado actual. LLM comercial, Golden externo y acceso administrativo GCP mantienen las limitaciones de Fase 0; no se inventa su validación por cambiar la foundation.

Siguiente gate: instrucción para Fase 2 y diseño de JWT/membership, migración de las 11 tablas tenant, acceso a objetos/RPC/Storage y prueba A/B. No iniciar Fase 2 automáticamente. Esta entrega no cambia credenciales, actores de aprobación ni datos históricos.
