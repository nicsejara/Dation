# Dation Design System V1

**Especificación de Fase 0, 14 de octubre de 2026.** La paleta y los contratos de este archivo son el destino de las fases 1–7; no están aplicados a producción. Baseline: `bcda3e55f80ec216711e428c9451ac6ef8d86756`.

> Estado de implementación: la base dark, el shell, los botones y el contrato de heroes se aplican en [Fase 1](DATION_DARK_PHASE1_IMPLEMENTATION.md). Las secciones de páginas, workflow y dashboards siguen siendo el destino de las fases siguientes. El diagnóstico y baseline de este documento corresponden a Fase 0.

Consultar los [wireframes](DATION_DARK_WIREFRAME_V1.md) y el [inventario](DATION_COMPONENT_INVENTORY_V1.md) para rutas, implementaciones y secuencia de migración.

## Diagnóstico y decisiones

Los tokens globales son light. Numerosos componentes fijan colores sin tokens: `app.css` tiene 577 literales hex, `dispatch.css` 833 y `assignment-config-v2.css` 154. Son ocurrencias textuales, no colores únicos ni prueba de que cada regla esté activa. La última hoja tiene 135 `!important`; añadir un override oscuro global aumentaría la dependencia de especificidad y orden de carga.

Se conserva navy/graphite con teal, cyan y violet. La jerarquía se expresa con luminancia, borde y sombra contenida. Los gradientes se reservan para marca, hero, CTA y estados seleccionados; las cards ordinarias son superficies sólidas. No se usa inversión de colores.

## Capas y propiedad

| Capa | Propietario objetivo | Responsabilidad |
|---|---|---|
| Valores y roles | `tokens.css` | Única fuente de color, tipografía, espacio, radios, alturas y motion |
| Shell | `app.css` | Body/main/sidebar/topbar/journey/workspace nav; conservar contratos de visibilidad |
| Primitivas | `dation-design-system.css`, desde Fase 1 | Button, field, card, status, hero base, focus y overlays comunes |
| Workflow | helper en `decision-config-ui.mjs` + estilos comunes | Hero de Config, contexto, secciones, summary y Action Bar |
| Específico de página | Hojas y renderers activos del inventario | Composición, charts y estados propios, consumiendo roles |

El archivo de primitivas tiene un propósito acotado. No será un `dark-overrides.css`. Las reglas que se migren deben retirarse o convertirse en aliases en su dueño; un estilo específico no compite indefinidamente con una base duplicada.

## Tokens de color propuestos

### Valores

```css
/* Especificación; se implementa en Fase 1. */
--d-bg-0: #071015;
--d-bg-1: #0A141B;
--d-bg-2: #0D1820;
--d-surface-1: #0F1B24;
--d-surface-2: #13222C;
--d-surface-3: #182A35;
--d-surface-hover: #1B303B;
--d-surface-overlay: #172731;

--d-text-primary: #F3F8FA;
--d-text-secondary: #B8C8CF;
--d-text-muted: #91A5AF;
--d-text-disabled: #6D838D;

--d-border-subtle: rgba(145, 189, 199, .12);
--d-border: rgba(145, 189, 199, .18);
--d-border-strong: rgba(145, 189, 199, .28);
--d-border-control: #67838F;

--d-brand-teal: #1C9499;
--d-brand-teal-bright: #39BCC0;
--d-brand-cyan: #43A6C7;
--d-brand-violet: #6556B3;
--d-brand-deep-violet: #3B2B78;
--d-success: #45C994;
--d-warning: #F0B95A;
--d-danger: #F27C70;
--d-info: #69A9E8;
```

Se ajusta el muted sugerido `#80959F`: sobre hover sólo da 4.383:1. `#91A5AF` deja margen para texto normal. El faint original no se usa como copy informativo. Los tokens de borde alpha son decorativos; un input o estado distinguible por borde necesita `--d-border-control`, focus o un indicador adicional contrastado.

### Roles semánticos

| Token público | Valor / referencia | Uso |
|---|---|---|
| `--color-bg` / `--color-bg-raised` | bg-0 / bg-1 | Canvas y shell |
| `--color-surface` | surface-1 | Card y panel |
| `--color-surface-raised` | surface-2 | KPI, controles y selección secundaria |
| `--color-surface-overlay` | surface-overlay | Popover, drawer, dialog |
| `--color-surface-hover` | surface-hover | Hover de elementos habilitados |
| `--color-text` / `--color-text-secondary` | text-primary / text-secondary | Contenido y descripción |
| `--color-text-muted` / `--color-text-disabled` | text-muted / text-disabled | Apoyo legible / controles inactivos |
| `--color-border` / `--color-border-strong` | border / border-strong | Separación decorativa |
| `--color-control-border` | border-control | Límite de campos y controles |
| `--color-focus` | brand-teal-bright | Anillo exterior de foco |
| `--color-brand` / `--color-brand-hover` | brand-teal / brand-teal-bright | Acento y links, con foreground evaluado |
| `--color-brand-gradient` | Gradiente de marca decorativo | Radiales/visual de hero; no asumir AA con texto |
| `--color-action-primary-bg` | Gradiente AA de acción | Fondo del botón principal |
| `--color-action-primary-hover` | Gradiente AA hover | Hover principal |
| `--color-action-primary-text` | text-primary | Texto/icono de CTA |
| `--color-success/warning/danger/info` | Estados de la paleta | Icono y texto, siempre con etiqueta |

Conservar aliases actuales como `surface-subtle`, `surface-strong`, `brand-dark/soft/faint`, `sidebar-*`, `decision-*`, `current-*` y `neutral-bg` hasta migrar sus consumidores. Deben mapear a roles dark o a un bridge explícito; no borrarlos por no aparecer en una pantalla.

### Dos gradientes con funciones distintas

```css
/* Marca: decoración, sin garantía para texto pequeño superpuesto. */
linear-gradient(135deg, #137D83 0%, #43A6C7 52%, #5C4AA5 100%);

/* Acción: foreground #F3F8FA. */
linear-gradient(135deg, #0D5D63 0%, #1C6482 52%, #50418A 100%);

/* Acción hover: mismo foreground. */
linear-gradient(135deg, #146C72 0%, #267491 52%, #5C4AA5 100%);
```

El primer gradiente no es válido con texto blanco de 12–13 px: su mínimo medido es 2.610:1. No reutilizarlo directamente como fondo de CTA con ese foreground. Los dos gradientes de acción conservan la familia de marca con luminancia suficiente.

## Contraste verificado de la propuesta

Se calculó luminancia relativa sRGB de WCAG 2.x sin redondear antes de comparar. Superficies evaluadas: bg-0, surface-1, surface-2, surface-hover y surface-overlay. La tabla informa el peor par; el JSON contiene cada combinación.

| Elemento / foreground | Mínimo | Criterio |
|---|---:|---|
| Texto principal `#F3F8FA` | 12.801:1 | AA normal |
| Texto secundario `#B8C8CF` | 7.961:1 | AA normal |
| Muted ajustado `#91A5AF` | 5.354:1 | AA normal |
| Disabled `#6D838D` | 3.446:1 | Sólo control inactivo; no copy normal |
| Focus `#39BCC0` | 5.956:1 | Indicador no textual ≥3:1 |
| Borde de control `#67838F` | 3.406:1 | Límite de control ≥3:1 |
| Success / warning | 6.548 / 7.695:1 | Etiqueta sobre superficie base |
| Danger / info | 5.150 / 5.508:1 | Etiqueta sobre superficie base |
| CTA AA, texto principal | 6.136:1 | Mínimo en interpolación del gradiente |
| CTA AA hover, texto principal | 4.913:1 | Mínimo en interpolación del gradiente |

Los gradientes se muestrearon en 257 posiciones por segmento en sRGB, sin opacidad; las posiciones 52 % sólo afectan la distribución, no los pares interpolados. Es una verificación de la propuesta, no una certificación de pantallas implementadas. Radiales, alpha, overlays, series, autofill y estados se medirán sobre la composición renderizada en sus fases y Fase 6. No asumir que el contraste de un badge con alpha es igual al de su color sobre el canvas.

## Tipografía, ritmo y forma

Mantener `Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`; usar el fallback real del entorno si Inter no está disponible. No agregar descargas de fuentes para esta fase.

| Rol | Tamaño / line-height | Peso |
|---|---|---|
| Page Hero H1 | `clamp(28px, 3vw, 40px)` / 1.12–1.18 | 750–800 |
| H2 de sección | 19–22 / 1.25 | 700–750 |
| H3 de card | 14–16 / 1.35 | 650–750 |
| Body | 13–14 / 1.5 | 400–500 |
| Support | 11–12 / 1.45 | 500–600 |
| Eyebrow | 10–11 / 1.3 | 700; tracking moderado |

Espaciado: **4, 8, 12, 16, 20, 24, 32, 40, 48 px**. Radios: **8, 10, 12, 16, 22/24 px y 999 px**. Un radio pill se reserva para chip/badge; las cards no cambian de radio por color.

Sombras dark propuestas: xs `0 1px 2px rgba(0,0,0,.16)`; sm `0 4px 12px rgba(0,0,0,.20)`; md `0 12px 32px rgba(0,0,0,.28)`; overlay `0 20px 60px rgba(0,0,0,.40)`. Exponer `--shadow-*-dark` y mapear los aliases vigentes. El borde sigue separando superficies cuando la sombra no es visible.

Motion: fast 140 ms y base 220 ms; controles frecuentes no superan 300 ms. `prefers-reduced-motion` elimina desplazamientos y animaciones decorativas, preservando feedback de estado.

## Buttons e iconos

Primitiva objetivo: `.d-button`, variantes primary, secondary, ghost, danger, icon y menu item. Las clases actuales se migran por propietario; no se resuelven con nuevos inline styles ni reglas universales `!important`.

| Tamaño | Alto | Radio | Texto / icono |
|---|---:|---:|---|
| sm | 36 px | 8–10 px | 12 / 16 px |
| md, default | 40 px | 10 px | 13 / 16 px |
| lg | 46 px | 10–12 px | 13–14 / 18 px |
| icon | 40 × 40 px | 10 px | SVG 18 px, nombre accesible |

Gap 8 px; padding horizontal 12–16 px. En móvil se amplía el área de interacción cuando haga falta, sin achicar iconos/labels para hacerlos entrar. No depender de hover para descubrir una acción.

- Primary: gradiente AA; hover definido arriba, desplazamiento máximo −1 px y glow discreto.
- Secondary: surface-raised, texto principal y borde de control; hover surface-hover más acento.
- Ghost: transparente con texto secundario; hover con superficie visible.
- Danger: texto e icono danger con fondo oscuro; una acción irreversible requiere su confirmación existente.
- Disabled: atributo nativo cuando corresponda, `aria-disabled` coherente, fondo/borde muted, sin hover ni desplazamiento. No reducir toda la card a 20 % de opacidad.
- Loading: bloquear repetición, conservar ancho/nombre accesible y comunicar estado con `aria-busy`/status.

Reutilizar `iconSvg()` y sprite actual. Tamaño 16–18 px y stroke coherente; iconos decorativos `aria-hidden`, icon-only con label. Reemplazar las variantes Unicode de toolbar en Fase 5, preservando hooks de exportación y navegación.

## Heroes y secciones

Primitiva `.d-page-hero`, aplicable a `.d-home__hero`, `.dda-landing__hero`, `.dispatch-pro-hero`, `decisionHero()` y el hero de Map. Adaptar los dueños existentes; no construir otro renderer por pantalla.

Desktop: min-height orientativo **210–230 px**, padding 24–28 px, gap 24–28 px, radio 24 px. La altura no es fija: el texto, zoom y localización pueden aumentarla. No usar clipping para cumplir una cifra. Home admite hasta 10 % más de contenido con el mismo sistema.

Eyebrow → título → explicación breve → acciones si corresponden. Visual lateral pequeño y no interactivo; panel «Cómo funciona/Esta decisión» usa iconos compactos y no repite la explicación. Móvil apila el contenido y reduce el visual decorativo a una fila compacta o lo omite, manteniendo la explicación funcional en copy/Cómo funciona. No apilar tres grandes tarjetas decorativas ni relegar el CTA a otra pantalla. No se oculta información operativa para compactar el hero.

Section header comparte número, eyebrow, H2, descripción y contexto actual; cards/panels usan superficie-1, borde sutil y radio 16 px, con padding 16–24 px.

## Workflow Action Bar

Un patrón compartido para Upload, Assignment y Scheduling, con propietario en `decision-config-ui.mjs`. Mantener `configSummaryBar()` como adaptador mientras sus consumidores migran. Upload convierte su composición DOM a la misma salida común; no implementa otra versión visual.

Contrato: nombre de proceso, estado/razón, summary items con destinos opcionales y un primary con label, icono, estado y hooks del flujo existente. Las actualizaciones de preflight no deben reemplazar un botón que mantiene foco ni perder callbacks. El componente representa estado; la página sigue siendo dueña de validar, confirmar y ejecutar.

Desktop: alto orientativo 76–88 px, padding 12–14 por 14–16 px, radio 16 px, ancho del contenido, offset inferior 14–18 px. Fondo dark translúcido con fallback opaco, blur y borde sutil. La altura real se reserva en el page root mediante medida/variable compartida, más safe area y gap; no un padding fijo basado sólo en desktop.

Móvil: chips con scroll local o dos filas compactas y CTA de ancho completo. Conserva `aria-label` de resumen, destinos de secciones, foco y errores. Un único punto de ejecución; no incluye profundidad/Dashboard en el objetivo final.

## Toolbar, menús y capas

`dashboard-toolbar.mjs` permanece compartido. Identidad: decisión + estado + corrida. Primary: Aprobar o Continuar. Secondary: Map, Exportar y Más. Se elimina el badge/fila de profundidad en la fase prevista, manteniendo lineage y detalles técnicos históricos.

Menús: al abrir uno cerrar los demás, click exterior cierra, Escape cierra y devuelve foco al summary activo. Usar el scope existente para limpiar listeners al navegar. Abrir drawer primero cierra menús; click dentro del drawer/dialog no dispara el cierre exterior de otro componente. El panel se limita al viewport y se reposiciona si no cabe.

Escala de capas objetivo: contenido 0; footer 30; topbar/journey 40; toolbar 44; popover 60; backdrop 80; modal/drawer 90; toast 100. Evitar stacking contexts accidentales de blur/transform; probar toolbar bajo la altura real de topbar, no asumir siempre 76 px.

Dialogs nativos conservan top layer. Drawer modal conserva trap de foco, Escape y restore. Backdrop `rgba(0,0,0,.55)`, superficie overlay, borde visible, scroll de contenido y header de cierre accesible. El chat usa la misma familia, sin abrir dos sesiones/listeners por ruta.

## Datos, formularios y analytics

- Inputs text/number/search/select/date: fondo bg-raised, borde de control, texto principal; label persistente, ayuda muted, error textual asociado. No usar placeholder como único label.
- `color-scheme:dark` en meta y root desde Fase 1; revisar date picker nativo y autofill. Un estado invalid agrega icono/mensaje además de borde. Range y checkbox mantienen teclado, `aria-valuetext` y selección perceptible.
- Tablas: surface-1, separadores sutiles, header sticky opaco dark, hover de fila y scroll local con nombre accesible. No ocultar columnas operativas esenciales sin alternativa.
- KPI: surface-raised, número principal, label muted; deltas semánticos con signo/unidad. Conservar el cálculo canónico; el tema no cambia los denominadores.
- Charts: el helper `shared.chart()` hoy inicializa ECharts sin tema y reemplaza `textStyle` del caller con familia/tamaño. La migración debe combinar opciones y alimentar texto, ejes, grilla, leyenda, tooltip, series y background. Scheduling y Assignment usan SVG con tooltip richText; no asumir que sus defaults ya son dark.
- Series: teal/cyan/violet con trazos, símbolos, labels o patrón que distingan categorías sin depender sólo del color. Usar rojo/ámbar para semántica, no para identificar recursos arbitrarios.
- Tooltips sobre overlay, texto principal y borde; SVG/richText recibe opciones del gráfico, no un selector CSS HTML. Mantener tabla alternativa y formatter/fechas actuales.
- Empty, error, warning, success y loading: icono + label + acción real. Skeleton de luminancia oscura y motion reducido. No introducir confirmaciones falsas, warnings genéricos ni estados «Validado» puramente decorativos.

## Transición y compatibilidad

Fase 1 migra shell y primitivas; las páginas restantes se migran en fases 2–5. Un componente todavía light debe conservar un par explícito fondo/texto y, si corresponde, su esquema nativo, mediante un bridge pequeño en su dueño. No cambiar sólo el foreground global y dejar white cards con texto blanco. Identificar el bridge y su fase de retiro; no adoptarlo como arquitectura permanente.

No eliminar `analysis_depth` del backend ni de JSON históricos. En Fase 4 las nuevas Assignment envían `essential` explícito como compatibilidad; Scheduling retira sólo su opción visual. Los placeholders avanzados quedan fuera de estado/payload. La normalización del Dashboard preserva comparative original y artefactos derivados.

## Validación y gate

Esta fase valida la especificación y los cálculos, con 70 capturas del estado actual en cinco anchos y suites existentes de 349 Python/37 Node. No aplica ni certifica todavía los tokens en componentes reales.

Cada fase visual debe comprobar normal/hover/focus/disabled/error, cold y warm navigation, nombres largos, contraste sobre superficies compuestas, keyboard y última acción visible sobre footer. Fase 6 añade zoom, focus sin clipping, reduced motion, pickers nativos, autofill y E2E completo; Fase 7 elimina bridges y reglas sin consumidores demostrados.

**FASE 0 COMPLETA — especificación lista para Fase 1.** No se inicia implementación dark por la existencia de estos snippets.
