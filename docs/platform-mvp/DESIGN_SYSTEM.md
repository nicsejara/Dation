# Platform foundation v1 · Contrato de componentes

Implementado en Fase 1. Foundation optativa sobre la identidad dark existente: Inter, superficies navy, teal/cyan, violet secundario y colores semánticos. No reemplaza el Hero ni los controles propios del workflow D1/D2.

## Ownership y adopción

| Capa | Archivo | Contrato |
|---|---|---|
| Tokens | `backend/app/static/css/tokens.css` | Roles `--platform-*` para tipo, spacing, controles y tabla; aliases anteriores intactos |
| Primitives | `backend/app/static/css/dation-design-system.css` | Tipografía, button, field/input/select/textarea y elecciones nativas |
| Components | `backend/app/static/css/platform-components.css` | Page, header, superficies, estados, tabla, filtros, overlays y navegación visual |
| Interacción | `backend/app/static/js/platform/components.mjs` | Dropdown/disclosure y native dialog, sin API ni lógica de negocio |

Todo consumidor nuevo debe estar dentro de `.d-platform`. Cargar components después de design system. El scope no cambia display/visibilidad del contenedor ni aplica resets globales. No envolver todo el shell o un dashboard existente para adoptar una única primitive.

Primer consumidor: el panel técnico de Configuración ya existente. Conserva contenido, IDs, consultas y navegación, y adopta header/cards/texto/badge y ayuda contextual. No es la página futura de Workspace Settings de Fase 9. No se añade autenticación ni administración de workspace.

## Geometría y tipografía

`.d-page` controla máximo `--content-width` (1320 px), ancho disponible y gap entre secciones. El host conserva su gutter: no aplicar padding de página dos veces. `--platform-page-gutter` usa 32 px y 16 px en móvil; `--platform-section-gap`, 24/20 px. Se conserva escala 4/8, radios y sombras existentes.

| Uso | Clase | Rol |
|---|---|---|
| Eyebrow | `.d-eyebrow` | 11 px, uppercase y tracking, color accent |
| Page title | `.d-page-title` o `.d-page-header__title` | clamp 24–32 px, peso 700 |
| Descripción | `.d-page-description` o `.d-page-header__subtitle` | 14 px, texto secundario |
| Section title | `.d-section-title` | 20 px |
| Card title | `.d-card-title` / `.d-card__title` | 16 px |
| Body | `.d-body` | 14 px |
| Metadata | `.d-metadata` | 12 px |
| Caption | `.d-caption` | 11 px |
| ID | `.d-id` | 12 px, monoespaciada y números tabulares |

Header: `.d-page-header`, `__copy`, `__actions` y breadcrumbs opcionales `__breadcrumbs`. Desktop coloca acciones a la derecha; hasta 760 px las baja y hasta 520 las apila. Una sola acción primaria por contexto. Títulos largos pueden crecer.

## Botones

Componer `.d-button` con `--primary`, `--secondary`, `--ghost`, `--danger` o `--icon`, y tamaños `--sm/--md/--lg`. Base 40 px; small 36 px desktop, al menos 40 en móvil; large 46 px. Icon-only requiere `aria-label` y SVG decorativo con `currentColor`, registry existente y viewBox 24.

Estados: hover, active, focus-visible, disabled y loading. Para una operación pendiente usar **ambos** `disabled` y `aria-busy="true"`, más texto comprensible. El caller controla la petición, bloqueo y resultado; CSS no autoriza ni evita una petición por sí solo. `.d-button--workflow` conserva íntegro su contrato anterior de tamaño/anchos/spinner.

Usar `<button type="button">` para comandos y `<a href>` para navegación. Para una navegación no disponible, retirar href y usar `aria-disabled`/tabindex apropiado o un botón nativo disabled; `aria-disabled` por sí solo no bloquea un handler o URL. No usar una primitive visual como autorización.

## Formularios

`.d-field` agrupa label, control, helper/error. `.d-field__label` usa `for`; el control conserva `id`, `name`, `type`, `required`, `autocomplete` y validación nativa. Feedback real con `aria-describedby`; error visible con `aria-invalid="true"`. No usar placeholder como label. Estados disabled, readonly y autofill respetan dark mode.

```html
<div class="d-platform">
  <div class="d-field">
    <label class="d-field__label" for="label">Nombre</label>
    <input class="d-input" id="label" name="label" required
           aria-invalid="true" aria-describedby="label-help label-error">
    <p class="d-field__help" id="label-help">Un nombre reconocible para el equipo.</p>
    <p class="d-field__error" id="label-error">Ingresá un nombre.</p>
  </div>
</div>
```

Text/password/search/date usan `.d-input`; select `.d-select`; textarea `.d-textarea`. Tamaños `--sm/--lg`; ancho fluido, texto largo y resize vertical. `--platform-form-width` define el máximo disponible para una composición de formulario; no impone ancho a todos los inputs.

Iconos opcionales dentro de `.d-field__control`, `.d-field__icon` y `--trailing`, con el modificador de input `.d-field--leading-icon`/`--trailing-icon` para reservar espacio. No colocar un password manager propio encima del input nativo.

Checkbox/radio/switch son inputs nativos `.d-check/.d-radio/.d-switch`. Un switch usa checkbox + `role="switch"`. Envolver en `<label class="d-choice">`, con `.d-choice__copy`: el target táctil se mide por el label completo, no por los 20 px del glifo. Conservar names, checked, disabled, indeterminate y teclado del navegador. No simular elección con divs.

## Estados y superficies

`.d-status` siempre contiene texto. Tonos: `--neutral` (default), `--info`, `--success`, `--warning`, `--danger`, `--brand`. Elegir por significado, sin inventar un color por página.

| Estado conceptual | Presentación recomendada |
|---|---|
| Active, Approved, Completed | success |
| Invited, In progress | info |
| In review | warning |
| Failed | danger |
| Disabled, Archived, Coming soon | neutral |

Esta tabla es una guía visual, no una nueva máquina de estados. Case/node/run siguen teniendo sus contratos y derivaciones de dominio propios. Estados que cambian pueden usar `role="status" aria-live="polite"`; no anunciar decoraciones como notificaciones.

Superficies: `.d-card`, `.d-panel`, `.d-panel--raised`; `__header`, `__title`, `__description`, `__body`, `__footer` para composición. Empty/error: `.d-empty-state` / `.d-error-state` y sus title/description/actions; error accionable puede usar `role="alert"`. Skeleton `.d-skeleton`, `--line` y `--circle`: `aria-hidden="true"` en la decoración y estado textual en el wrapper. No convertir un skeleton en información ficticia.

Toast: `.d-toast` y `__body/__title/__description`, con región live según urgencia. Tooltip: `.d-tooltip` aporta superficie; el caller conserva asociación `aria-describedby`, `role="tooltip"`, acceso teclado y política de mostrar/cerrar. No usarlo para información esencial ni asegurar que CSS implementa por sí solo comportamiento accesible.

## Tablas, filtros y navegación visual

Contenedor `.d-table-container`, tabla `.d-table`, headers `scope`, caption y filas semánticas. Overflow queda dentro de la región, no de la página. Si hay desplazamiento, contenedor con `tabindex="0" role="region" aria-label="…"`. Header sticky; hover de fila, selected, columnas numéricas `__number`, nowrap/wrap y row actions. Sort usa button `d-table__sort` y `aria-sort` en el th; el caller hace el ordenamiento real.

`.d-filter-bar`, `__search`, `__controls` componen búsqueda y selectores con labels. El caller administra queries, conteos y paginación; no se añade un query builder.

`.d-sidebar-item` es sólo la primitive visual: icono, label, estado actual `aria-current="page"` y disabled nativo/ARIA. No añade rutas ni una segunda sidebar. Usar el registry SVG actual; no un carácter emoji como icono productivo.

## Interacciones y lifecycle

```js
import {mountDropdown, mountDialog} from './platform/components.mjs';

const menu = mountDropdown({trigger, panel});
const review = mountDialog({dialog, trigger: openButton, initialFocus: '#first-field'});
// Si no existe un scope padre, el caller debe liberar explícitamente:
menu.dispose();
review.dispose();
```

`mountDropdown({trigger,panel,closeOnSelect=true})` retorna `open({focus:'first'|'last'|false})`, `close({restoreFocus=true})`, `toggle()`, `dispose()` y `isOpen`. Roles `menu` reciben flechas/Home/End, roving focus y salida Tab. Popovers de contenido mantienen tabulación nativa y usan disclosure (expanded/controls), sin anunciar un menú inexistente. Escape restaura foco; outside click/focus conserva el destino elegido. Posición se recalcula en scroll/resize y queda dentro del viewport. El caller provee labels, roles y acciones.

`mountDialog({dialog,trigger,initialFocus,closeSelector='[data-dialog-close]',closeOnBackdrop=false})` comparte modal y drawer nativos. Retorna open/close/dispose/isOpen. Usa showModal, Tab trap, Escape, retorno al origen y limpieza al desmontar. Caller provee `aria-labelledby`/label, descripción, contenido y acciones reales. `.d-modal` y `.d-drawer` cambian presentación, no crean un flujo de negocio.

Ambos usan `createScope` existente. Un scope padre de página posee a los hijos; navegación/pagehide libera listeners y cierra overlays. Un remount sobre el mismo nodo dispone primero el anterior. No instalar listeners globales sin cleanup ni reutilizar el helper para autorizar acciones.

## QA y límites

Galería sólo de tests: `backend/tests/browser/fixtures/platform-foundation.html`, servida por un servidor loopback del test. No existe ruta productiva, no se empaqueta en Docker y no llama APIs de negocio. Ejercita nueve familias con la cascada real extraída del template.

Ver [implementación y comandos](09-phase1-foundation.md). Se verificaron Chromium, cinco widths, teclado, contraste, targets móviles y reducción de movimiento. El layout de 640 px modela reflow al 200% sobre 1280; no constituye certificación WCAG ni prueba de todas las extensiones de password managers.
