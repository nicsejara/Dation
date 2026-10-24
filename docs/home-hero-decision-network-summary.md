# Home Hero — Dation Decision Network

Estado: H1–H6 PASS. Baseline real `main` / `origin/main`: `39906b3092aa919deedbabc91f9ad0eba87e87bf`. Branch: `ux-ui/home-hero-decision-network`.

Se leyó completo el master adjunto y se consultó la arquitectura, navegación, mapa de componentes y los resúmenes visual/final-polish. No se hizo una auditoría global ni se rediseñó el resto del Home.

## Implementación

Hero mineral con eyebrow definitivo, saludo secundario dinámico, headline blanco/teal y supporting copy exactos. El h1 representa ahora el mensaje del producto; el saludo conserva íntegro el algoritmo anterior, perfil, zona horaria y listeners de identidad/vista. Inter y tokens existentes, sin cambios globales.

`Explorar DDA` conserva `focusDdaCatalog()` y el destino del catálogo. `Ir a Decision Center` usa el mismo helper `link()` y callback de navegación que el acceso rápido existente; se conserva su URL canónica y parámetros. No hay router nuevo, API ni state adicional.

La banda inferior pertenece al mismo Hero y muestra Data Pack / Decision Case / Decision Run con los tres textos universales indicados. Es informativa, sin selección ni hotspots. En mobile se apila y el visual decorativo se oculta para priorizar copy y acciones. No se incorporó motion ornamental; hover/focus usan el Design System y active no mueve el layout.

## Asset provisional — reemplazo pendiente

No había un render final aprobado de Decision Network en el repositorio ni en el adjunto. Se aplicó la alternativa explícita de la sección 9: **placeholder premium local, no asset final aprobado**.

`backend/app/static/assets/home-decision-network-placeholder.svg`: 4.763 bytes, 640×480 (4:3). Composición isométrica estática con hub y cinco módulos —datos, Case, Run, evidencia y gobernanza—, sin vehículos, brain/robot, dashboards falsos, texto incrustado ni dependencias. SVG externo con formas/gradientes físicos propios del arte; no modifica la paleta de la aplicación. Decorativo con `alt=""`, no interactivo, dimensiones reservadas y decode asíncrono; una sola variante local, sin hotlink, bitmap grande o filtro de blur.

Al disponer del render final aprobado, reemplazar este asset conservando el contenedor 4:3 y tratamiento decorativo, y volver a comprobar peso, contraste, dimensiones y layout shift. Esta limitación se comunica en el reporte final; no se afirma contar con arte final aprobado. El fallback está expresamente permitido por el master y no exige cambios funcionales.

## Aceptación

| Criterio | Estado | Verificación |
| --- | --- | --- |
| H1 · Copy | PASS | Eyebrow, headline y supporting copy exactos; teal en la segunda frase |
| H2 · CTA | PASS | Catálogo, foco, Decision Center y back/history con navegación existente |
| H3 · Visual | PASS | Placeholder isométrico de Decision Network según sección 9; sin truck/cliché AI/collage |
| H4 · Banda | PASS | Tres conceptos y textos universales; jerarquía informativa |
| H5 · Responsive | PASS | Seis viewports, sin overflow, contraste AA muestreado, teclado y zoom 200% |
| H6 · Preservación | PASS | Saludo, identidad, rutas, permisos, catálogo y Quick Access actuales |

## QA

- BEFORE/AFTER en 1440×900, 1280×800, 1024×768, 768×1024, 375×812 y 320×640; evidencia fuera del repositorio: `/workspace/work/home-hero-decision-network/`. Se revisaron visualmente desktop/mobile; la red aporta contexto sin competir con la lectura. No se afirma QA en hardware móvil físico.
- Doce casos browser distintos aceptados en corridas y repeticiones focalizadas: cinco de aceptación nuevos y siete de regresión Home/catálogo/Viewer/Quick Access/Overview. Copy, dos CTA por teclado, foco, back, saludo en tres horarios y zona BA, cambio de nombre/nombre vacío, mobile, 200%, asset lento/fallido y entitlements pasan. No se admite ningún Run ni Case desde estas pruebas.
- 34 tests Python de frontend y Home PASS. Suite Node de catálogo PASS (5 casos declarados), sintaxis del módulo PASS.
- Contraste muestreado y overflow: seis de seis observaciones PASS, cero errores JS. La banda y las dos acciones siguen legibles sin imagen. La carga demorada no modifica el bounding box del Hero; no se presenta esta medición local como un benchmark LCP de producción.
- Actualizadas sólo expectativas directamente afectadas: saludo deja el h1, ahora hay dos CTA y el hero ya no tiene límite histórico de 250px. Se eliminó la lectura de altura obsoleta del inspector. El test nuevo compara destinos canónicos incluyendo los parámetros existentes, sin exigir una URL inventada.
- Taste: lint del CSS añadido en modo app, 0 FAIL / 0 WARN; inspector de seis observaciones sin FAIL. WARN de bordes, densidad tipográfica y bloques bajo el fold corresponden a la dirección existente y al hero editorial solicitado; no motivan cambios del catálogo o shell. No se sortea otra dirección: la Skill permite omitir draw en un componente con dirección definida, y el master fija Dation Precision, Inter y énfasis teal.
- Comparación del DOM normalizando únicamente el origen del servidor local: Quick Access, catálogo y sidebar idénticos en los seis tamaños. Comparación de fuente: algoritmo de saludo, construcción de Quick Access, montaje del catálogo y handler primario intactos.
- Sólo cambian dos archivos existentes de aplicación: `platform/home.mjs` y `platform-home.css`. Los demás archivos de aplicación del baseline conservan sus hashes. Sin cambios de backend, auth, API, base, permisos, router, infraestructura, fuentes, dependencias ni resto de pantallas.

## Integración

El master autoriza fast-forward y push a `main` tras el gate H1–H6, árbol limpio y referencia remota compatible. Commit: `Upgrade Home hero to Dation Decision Network`. Sin squash, force, cambios de infraestructura ni deploy manual. El resultado exacto de integración/push y observación del pipeline se informa al finalizar, fuera del árbol validado.
