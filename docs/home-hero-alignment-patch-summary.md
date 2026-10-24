# Home Hero Alignment Patch

Estado: A1–A5 PASS. Baseline real de main/origin/main: `0c03de5213b485f89f19c9c30ab4bf4125043642`. Branch: `ux-ui/home-hero-alignment-patch`.

Se leyó completo el master definitivo. El cambio es exclusivamente de composición y consistencia del Hero del Home; no es una auditoría ni un rediseño transversal.

## Dirección vigente

La red abstracta/isométrica actual queda adoptada como **dirección definitiva** del Home. Se conserva íntegro el dibujo; sólo se actualiza su comentario interno para reflejar esta decisión. El nombre histórico `home-decision-network-placeholder.svg` se conserva para mantener las URLs de pestañas existentes. La anterior nota de asset provisional en `home-hero-decision-network-summary.md` queda superada por esta especificación: no hay un reemplazo realista pendiente.

## Ajuste

Las mediciones BEFORE mostraron que el ancho exterior ya coincidía con Logística en los seis viewports. El Home mantiene esa alineación, hace explícito su ancho completo y ajusta padding/radio, proporción texto/arte, escala estática de la imagen y separación de la banda inferior. La red gana presencia dentro del marco actual, sin movimiento nuevo. Copy, saludo y contenido de la banda se conservan.

Los CTA del Home medían 148,53 / 186,11 px de ancho y 46 px de alto. Ahora ambos miden **228×40 px** cuando hay espacio, con padding **0×16 px**, radio **6 px**, gap **8 px** y tipografía **13 px / 600 / 1,35**, como los controles de Logística. La referencia de Logística mide 227,69×40 px; la diferencia de ancho es menor a un píxel. En tablet se apilan; en mobile ambos ocupan el ancho disponible: 241×40 a 375 px y 186×40 a 320 px. El grid iguala también las filas si el texto necesita reflow.

Sólo se modifica CSS local del Home. No se cambian clases ni primitivas globales, otros heroes, handlers, rutas, identidad, permisos, backend o infraestructura. La única modificación del SVG es un comentario; todos los módulos JS de aplicación conservan su hash.

## Aceptación y QA

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| A1 · Dirección | PASS | Dibujo abstracto idéntico; mayor presencia mediante layout/escala estática |
| A2 · Marco/presencia | PASS | Mismos bordes horizontales y ancho que Logística en seis tamaños y 1920 px |
| A3 · CTA | PASS | Dimensiones iguales entre sí; altura, padding, radio y tipografía coinciden con Logística |
| A4 · Función | PASS | JS de aplicación intacto; saludo, navegación, historial y Viewer verificados |
| A5 · Responsive | PASS | Seis resoluciones, sin overflow, contraste, zoom 200% y foco visibles |

- 9/9 browser PASS: comparación geométrica real Home/Logística, render/copy, ambos CTA por teclado, back/history, saludo/zonas horarias/cambio de identidad, Viewer, accesos rápidos, imagen lenta/fallida y zoom. Se adapta una expectativa visual del test anterior de 44px mobile al control de 40px solicitado; Decision Center conserva su propia expectativa.
- 34/34 Python de frontend y Home PASS; suite Node del catálogo PASS. Lint del CSS añadido en modo app: 0 FAIL / 0 WARN.
- 12 observaciones BEFORE y 12 AFTER: Home y Logística × 1440×900, 1280×800, 1024×768, 768×1024, 375×812 y 320×640. Sin errores JS, overflow ni fallos de contraste muestreado. Se revisaron capturas desktop/mobile. No se afirma QA en hardware físico.
- DOM de Quick Access, catálogo y sidebar idéntico normalizando sólo el origen del servidor de fixtures. Geometría de Logística BEFORE/AFTER idéntica. Todo archivo de aplicación fuera del CSS local y comentario del SVG mantiene su hash.
- Evidencia local fuera del repo: `/workspace/work/home-hero-alignment/`.

## Integración autorizada

Commit: `Align Home hero with Logistics hero and unify CTA sizing`. El gate exige árbol limpio, main remoto compatible y fast-forward. Sin squash, force ni deploy manual. La integración, push y observación del pipeline se informan al finalizar, fuera del árbol validado.
