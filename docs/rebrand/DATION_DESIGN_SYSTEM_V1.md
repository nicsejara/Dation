# Dation — Design System V1

Estado de implementación al cierre de Dark Rebrand / Grow-Up, fases 0–7. Este documento describe los propietarios y contratos vigentes; las auditorías y wireframes de Fase 0 se conservan como baseline histórico. El resultado del gate y el commit publicado se registran en el PR de Fase 7.

## Arquitectura y propietarios

| Capa | Fuente de verdad | Responsabilidad |
|---|---|---|
| Tokens | `backend/app/static/css/tokens.css` | Colores semánticos, aliases, espacios, radios, tipografía y motion |
| Shell | `app.css`, shell de `app.html` | Sidebar, topbar, journey, navegación, biblioteca y configuración técnica |
| Primitivas | `dation-design-system.css` | Botones, hero, cards, campos, foco, autofill y Action Bar |
| Workflow | `workflow-action-bar.mjs`, `decision-config-ui.mjs`, `dashboard-toolbar.mjs` | Un footer de acción compartido; contexto y toolbar con contratos estables |
| Páginas | Hojas Home/Overview/Upload/Map/Config/Dashboard | Composición y estados propios, sobre los roles semánticos |
| Analytics | `dispatch/chart-theme.mjs`, `shared.chart()` | Theme SVG/richText, paleta, resize, motion y dispose de ECharts |

Los CSS de esta tabla viven en `backend/app/static/css/`; los módulos abreviados, en `backend/app/static/js/dispatch/`. No se crea un segundo renderer para modificar la apariencia. Las reglas de visibilidad de los roots modernos siguen en `dispatch.css`: aún hay markup de compatibilidad en el template y no se elimina su ocultación.

## Tokens y superficies

`<meta name="color-scheme" content="dark">` y `:root { color-scheme: dark }` son el default. No hay toggle light ni boundary `legacy-light`. Biblioteca (`traceability`/`library`) y `settings` también heredan los roles dark; sus tablas, tabs, evidencia JSON y estados técnicos tienen colores semánticos en su propietario.

| Rol | Token | Valor |
|---|---|---|
| Canvas | `--d-bg-0` | `#071015` |
| Fondo elevado / secundario | `--d-bg-1` / `--d-bg-2` | `#0A141B` / `#0D1820` |
| Card / control | `--d-surface-1` / `--d-surface-2` | `#0F1B24` / `#13222C` |
| Superficie fuerte / hover | `--d-surface-3` / `--d-surface-hover` | `#182A35` / `#1B303B` |
| Overlay | `--d-surface-overlay` | `#172731` |
| Texto principal / secundario | `--d-text-primary` / `--d-text-secondary` | `#F3F8FA` / `#B8C8CF` |
| Texto muted / disabled | `--d-text-muted` / `--d-text-disabled` | `#91A5AF` / `#6D838D` |
| Borde de card | `--d-border` | `rgba(145,189,199,.18)` |
| Borde de control | `--d-border-control` | `#67838F` |
| Foco / acento | `--d-brand-teal-bright` | `#39BCC0` |
| Teal / cyan / violet | `--d-brand-teal`, `--d-brand-cyan`, `--d-brand-violet` | `#1C9499`, `#43A6C7`, `#6556B3` |
| Success / warning | `--d-success` / `--d-warning` | `#45C994` / `#F0B95A` |
| Danger / info | `--d-danger` / `--d-info` | `#F27C70` / `#69A9E8` |

Los aliases `--color-*` apuntan a estos roles. Se conservan porque los consumen shell, históricos y módulos actuales; eliminarlos por búsqueda textual rompería contratos compartidos. Los estados usan también sus fondos/bordes oscuros `--color-*-bg/border`, con icono y texto además de color.

El gradiente de marca es decorativo (`--color-brand-gradient`). Un CTA con texto principal usa `--color-action-primary-bg`: `#0D5D63 → #1C6482 → #50418A`, con parada central al 52%; hover `#146C72 → #267491 → #5C4AA5`. No usar el cyan brillante de marca como fondo de texto pequeño blanco.

Sombras: `--shadow-xs-dark` 0 1px 2px / negro .16; sm 0 4px 12px / .20; md 0 12px 32px / .28; overlay 0 20px 60px / .40. Los aliases existentes apuntan a ellas. La separación por borde permanece visible sin depender de sombra.

## Espaciado, radios y tipografía

Escala de espacio: **4, 8, 12, 16, 20, 24, 32, 40, 48 px**, expuesta en `--space-1/2/3/4/5/6/8/10/12`. Radios: sm 8, control 10, md 12, lg 16, xl 20, hero 24 y pill 999 px. Los componentes existentes pueden conservar geometrías justificadas; no añadir overrides globales para uniformarlos por fuerza.

Stack: `Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`; no se descarga otra fuente. Hero H1 `clamp(28px,3vw,40px)`; H2 19–22; H3 14–16; body 13–14; support 11–12; eyebrow 10–11 px. Las tablas técnicas históricas conservan su densidad y scroll, sin ocultar columnas.

Motion: fast 140 ms y base 220 ms. `prefers-reduced-motion` elimina el desplazamiento decorativo, el scroll suave de recuperación y las animaciones de ECharts. El gráfico escucha cambios de preferencia y libera ese listener al disponer su scope.

## Buttons y controles

`.d-button` proporciona la variante secundaria por defecto: alto mínimo 40 px, radio 10, gap 8 y padding horizontal 16 px. Variantes: primary, ghost, danger, icon y menu; tamaños sm 36, md 40 y lg 46 px. Icon button 40×40 y SVG 18 px, con nombre accesible. Los botones de propietarios antiguos mantienen sus hooks y adoptan los mismos roles.

Primary usa el gradiente AA; secondary usa superficie elevada, texto principal y borde de control; ghost usa texto secundario y superficie al hover. Disabled usa atributo nativo/`aria-disabled`, opacidad 1, sin hover ni desplazamiento. Loading conserva nombre, ancho y bloqueo de repetición. No agregar operaciones destructivas al utilizar el estilo danger.

`iconSvg()` es el catálogo compartido. Decoración con `aria-hidden`; icon-only con label. Foco visible teal de 3 px con offset; enlaces, summary, tabindex y controles nativos reciben tratamiento compartido. Los owners reservan márgenes de scroll para que barras sticky no cubran el foco.

Inputs text/number/search/select/date usan superficie dark, borde de control y label persistente. Range y checkbox conservan teclado y estado seleccionado. Autofill conserva valores y semántica nativa con text-fill/caret y relleno interior oscuro; no se deshabilita. Error usa explicación textual además del borde.

## Heroes, cards y superficies

`.d-page-hero` comparte fondo dark, radio 24, padding base 26, gap 24 y altura base orientativa 220 px. Home, Overview, Upload, Map y `decisionHero()` componen ese sistema con contenido propio. El alto crece con el texto y reflujo; no se recorta información para cumplir una cifra. Mobile usa padding/gap 20 px, apila contenido y compacta decoración.

Orden: eyebrow → título → explicación breve → acciones del owner. Cards y panels usan surface-1, borde semántico y radio 16. El contexto de caso es un disclosure, con ID copiable, archivos y acciones reales; no duplica la navegación del flujo. Map conserva conexiones, estados y jerarquía.

## Workflow Action Bar

`workflow-action-bar.mjs` es el único propietario DOM del footer de Upload y ambas Config. `configSummaryBar()` y `mountConfigActionBar()` adaptan el contrato de Config; los owners validan, confirman y ejecutan. No existe otro footer de ejecución en paralelo.

Contrato: nombre del proceso, estado/razón, resumen con destinos opcionales y un primary. Alto desktop orientativo 76–88 px; altura real medida y reservada en el root, con safe area y gap. Una actualización no reemplaza el botón enfocado ni pierde callbacks. ResizeObserver y variables se liberan al rerender/salir.

En móvil los chips tienen scroll local y el CTA ocupa el ancho disponible. Al enfocar un chip se desplaza su contenedor, sin mover toda la página. No aparecen profundidad ni opciones futuras en resumen o payload. A altura ≤540 px las barras dejan de ser sticky para permitir alcanzar el contenido.

## Toolbar, menús, diálogos y chat

`dashboard-toolbar.mjs` se comparte entre decisiones. Muestra decisión, estado y corrida; Aprobar/Continuar conserva su handler. Map, Exportar y Más usan SVG. La toolbar mide topbar y su propia altura para reservar foco, límites de tabla y scroll.

Los menús son mutuamente excluyentes; click exterior y Escape cierran, con restauración de foco. Abrir un drawer cierra menús. Scope libera listeners al abandonar la ruta. Escala base: footer 30, topbar 40, toolbar 44, popover 60, backdrop 80, modal/drawer/chat 90 y toast 100; los dialogs nativos conservan top layer. Chat 90 queda por encima de su launcher 70 en ambas decisiones.

Los diálogos Config tienen nombre accesible, trap Tab/Shift+Tab, Escape y restore. Drawers conservan header/cierre/scroll y sus callbacks. El chat usa columna flexible, thread con scroll local y composer alcanzable incluso a baja altura; abrirlo no duplica sesiones ni listeners.

## Tablas y analytics

Tablas dark con separadores semánticos, header opaco y scroll local. Tablas/calendario de dashboard limitan altura según el espacio disponible; no se ocultan datos operativos. KPI ejecutivo y comparador comparten las mismas cuatro definiciones y denominadores canónicos.

`chart-theme.mjs` combina opciones sin mutar datos, callbacks o formatos. Ejes, grilla, leyenda, tooltip SVG/richText y series usan roles dark. Categorías se distinguen además mediante trazos, símbolos o labels. Se mantienen tablas alternativas, fechas y dispose/resize. El CSS HTML no tematiza por sí solo un tooltip SVG.

## Responsive y accesibilidad

Matriz de referencia: **1440, 1280, 1024, 768 y 390 px**. Sidebar compacta mantiene nombres accesibles para Inicio y DDA. La rail de Assignment apila decisiones bajo 760 px. Formularios, tablas y diálogos conservan acceso por teclado y scroll local, sin overflow del documento.

Reflujo: lienzo físico 1440×1000, viewport CSS 720×500 / 360×250 y DPR 2/4 vía CDP. Esta equivalencia acredita reflujo y acceso a controles; no certifica la UI externa de zoom, todos los pickers de SO, lectores de pantalla ni otros motores. La evidencia es de Chromium/Linux y no se presenta como certificación WCAG completa.

Contraste de roles verificado desde Fase 1: texto principal ≥12.801:1; secundario ≥7.961; muted ≥5.354; foco ≥5.956 y borde de control ≥3.406 sobre las superficies base evaluadas. CTA normal ≥6.136 y hover ≥4.913, muestreados en 257 posiciones por segmento. Cada matriz visual vuelve a medir la composición real, alpha/gradientes y valores nativos: AA 4.5 normal / 3 grande. Disabled no se usa como copy informativo.

## Carga CSS y compatibilidad auditada

`styles.mjs` deduplica por pathname canónico, espera load, conserva la promesa pendiente y permite reintentar una carga fallida. `ensureDecisionCaseStyles()` comparte ID, URL y versión entre Map, Assignment y Scheduling. Map espera estilos y comprueba que el scope siga activo; una respuesta tardía no restaura una ruta abandonada. Los filtros aplicados reciben estilos de `assignment-config-v2.css`; el JS conserva sólo comportamiento, estado y accesibilidad, sin inyectar otra hoja.

Se retiraron siete módulos sin consumidor en el grafo publicado: `decision-stage.js`, `dispatch/{compare,kpis,plan,selectors,sensitivity}.mjs` y `upload/readiness-panel.mjs`. El test exclusivo del selector genérico retirado también desaparece; se conservan las regresiones de selectores actuales, métricas, comparación, pesos, filtros, exportaciones e históricos. Una comprobación automática resuelve entrypoints/imports, incluidos lazy imports, y detecta módulos huérfanos.

Se retiró `dation-legacy-surfaces.css` tras migrar sus dos páginas restantes. También 159 ramas de selectores de depth, footers antiguos, readiness y el configurador anterior, después de comprobar ausencia de markup consumidor. No se hizo un barrido por `#fff` sobre CSS de compatibilidad.

`decisionDepthCard` y `DEPTH_LABELS` ya no tenían consumidores ni implementación desde Fase 4. **`analysisDepthUi` permanece**: el shell actual lo consume para leer el atributo técnico de históricos essential/comparative/deep. Backend, JSON, motor, aprobaciones, exportaciones, bridges de `dashboard-stage.js`/`interpreter-stage.js` y visibilidad legacy se conservan porque tienen consumidores.

Nuevas Assignment envían `options.analysis_depth: "essential"` explícito desde Fase 4. Ese cambio puede producir planes distintos al default comparative: ver medición y límites en [Fase 4](DATION_DARK_PHASE4_IMPLEMENTATION.md). Retirar un selector visual no demuestra equivalencia del motor. La comparación permanece a demanda, con Generate/Close/Reopen/Restore/Retry y sin recalcular históricos al abrirlos.

## Estado final y gate de la saga

| Contrato | Estado implementado |
|---|---|
| Default, Home, Overview, Upload y Map | Dark |
| Assignment/Scheduling Config y Dashboard | Dark; una composición de Dashboard por decisión |
| Biblioteca y configuración técnica | Dark sin bridge light |
| Heroes / botones / footer / toolbar | Sistema compartido y propietarios documentados |
| Selector de profundidad | Retirado de UX; compatibilidad histórica conservada |
| Comparative | A demanda, con artefacto original o derivado |
| Advanced Options | Futuras y disabled; fuera de estado/payload |
| Menús | Exclusión mutua, cierre exterior/Escape y restore |

Gate de Fase 7: suites verdes en head exacto y main, Cloud Build del source exacto, verificación de revisiones/tráfico/assets, QA productiva de sólo lectura y hashes revisados sin cambios. El informe A–H y los límites concretos están en [Fase 7](DATION_DARK_PHASE7_IMPLEMENTATION.md). La saga consta de fases 0–7; su cierre habilita la validación end to end del usuario y un nuevo plan de ajustes, sin inventar una Fase 8.
