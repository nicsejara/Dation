# Dation Precision — Visual Product Upgrade

Estado: **Completed**. Base: `0adc473`. Rama: `ux-ui/visual-product-upgrade`. Ocho commits por fase; baseline visual previo a la implementación. Main y producción no se publican desde esta etapa.

## Dirección y sistema

La cadena datos → Case → Decision → Run → evidencia → aprobación es la firma de Dation Precision: estructura lineal, planos de grafito mineral y selección mediante borde teal. Inter, contenido y comportamiento se conservan. No se crean datos, métricas, navegación ni dependencias.

Taste: existing app redesign; `data-terminal`, seed `2039572090`. Se adopta selección lineal y precisión tabular. Se adapta el rail propuesto a la navegación etiquetada y destinos existentes. La marca mineral/teal, heroes y estados exigidos por el brief prevalecen sobre el negro puro, nuevas fuentes y patrones genéricos. UI UX Pro Max: resultado verificado `data-dense-dashboard`; se descarta Enterprise Gateway de marketing.

El sistema evoluciona en tokens → primitivas → componentes → composición. Base `#10161c`, panel `#19242d`, grupo `#202e39`, overlay `#22323e`; texto principal/secundario conservado, borde de control más visible. Radios por rol 4/6/8/12/16. Títulos operativos 28–36, bienvenida de Home 32–46, secciones 20, cuerpo 14, metadatos 12. Cifras tabulares, header discreto; sombras en overlays.

## Preguntas por superficie

| Superficie | Pregunta / firma |
| --- | --- |
| Home | ¿Dónde comienzo? Saludo, cadena trazable y Logística protagonista. |
| Overview | ¿Qué resuelve el DDA? Cadena y requisitos progresivos. |
| Datos | ¿Qué falta? Atributos, Owner y archivos independientes. |
| Map | ¿Qué puedo ejecutar/revisar? Nodos conectados y estado por Decision. |
| Config D1 | ¿Cómo distribuir carga? Criterios y recursos, sin calendario. |
| Config D2 | ¿Cuándo ejecutar? Fuente aprobada, ventana y reglas. |
| Dashboard D1 | ¿Cómo se distribuyó? Resultado, comparación y evidencia. |
| Dashboard D2 | ¿Cuándo y con qué SLA? Calendario, ocupación y excepciones. |
| Center | ¿Qué requiere acción? Agregados globales y portfolio. |
| Hub | ¿Qué datos tengo? Inventario, calidad y trazabilidad. |
| Team | ¿Quién tiene acceso y responsabilidad? Identidad, roles y elegibilidad. |
| Settings/Profile | ¿Qué puedo editar? Preferencias y guardado actual. |

## Baseline visual

28 capturas BEFORE: 13 superficies a 1440×900 y 375×812, más dashboards expandidos a 1440. Harness local con assets reales y APIs interceptadas por fixtures existentes, sin escrituras productivas. Artefactos: `/workspace/work/visual-product-upgrade/before/`.

## Integridad funcional

DDA → Case → Decision → Run; Data Pack inmutable; cuatro requisitos independientes; Apply sin CSV; un Data Owner por Case y un Decision Owner por nodo; aprobación humana por Run; invalidación al admitir, historia e idempotencia. D1 no temporal, D2 sobre Assignment aprobado, D3 disabled. Backend, motores, API, SQL, persistencia, tenancy, permisos, exportaciones, fingerprints, rutas y sesión congelados.

## Ejecución

Phase 1: sistema de planos, jerarquía y geometría en tokens/primitivas existentes. QA: 7 browser de primitivas pasan. Commit `33b11dc`.

Phase 2: shell con marca y selección lineal; Home editorial con cadena Data Pack/Case/Run, accesos en una banda y Logística como capacidad protagonista. 6 browser pasan (filtros, 11 viewports, teclado, fallback, Viewer e historia); 22 checks Node pasan. Cinco capturas de Home sin overflow ni fallos de contraste muestreado. La prueba anterior exigía píldoras iguales/hover translate y dos CTAs aunque el baseline ya tenía uno; se actualiza la expectativa visual manteniendo verificaciones de labels, guards, navegación y foco. Se corrigió el skip instantáneo y scroll-margin de accesos para no quedar bajo el topbar.

Phase 2 commit: `e1ebb98`.

Phase 3: Overview editorial, preparación en dos zonas (atributos/Owner) y archivos tipados, Map en carriles conectados con evidencia y Owner separados. Encabezado y contexto del workflow abiertos. CTA de Datos en flujo normal para no cubrir Aplicar. Misma semántica nodal y todos los controles. QA: 11 browser + 5 unitarios pasan; refuerzo posterior de foco (incluye Aplicar dirty) y paso actual: 2 pasan; 15 observaciones en cinco anchos sin overflow/contraste muestreado fallido.

Phase 3 commit: `f89b4d3`.

Phase 4: Config en secciones abiertas con columna de criterio y controles; selección lineal en presets, fuente D2 como banda de evidencia y revisión nativa refinada. 7 archivos JS de configuración/reglas idénticos al baseline. QA: 73 unitarios y 6 browser pasan (pesos/foco, cinco anchos, reglas D2, review y doble envío); 10 observaciones visuales sin overflow/contraste muestreado fallido.

Phase 4 commit: `11d9e43`.

Phase 5: hero analítico sin fotografía en las superficies de trabajo (assets conservados), KPI como bandas tipográficas, D1 comparación junto a explicación y D2 calendario junto a excepciones. Se mueve sólo el markup de timeline/insights de D2; todos los hooks/binders y contenido se conservan. Cifras monetarias ajustadas al ancho de la celda, con regresión browser de límites pintados en cinco anchos. QA: 7 browser distintos verificados, 29 checks Node y 11 observaciones visuales sin overflow/contraste muestreado fallido. La aserción histórica “Assignment bloqueada” ya contradice el baseline y se actualiza al copy aprobado/fijo vigente. Exportación JSON exacta y aprobación por Run pasan.

Phase 5 commit: `9c64b2f`.

Phase 6: headers operativos de Center/Hub, métricas en bandas compartidas, filtros/inventarios con bordes de lectura comunes, Team y Settings/Profile integrados al mismo sistema. Settings separa explicación y formulario. Se preservan filtros, totales globales, paginación, drawers, read-only y save/CAS. QA: 9 browser, 383 Python y 124 checks Node (18 archivos) pasan; 25 observaciones sin overflow/contraste muestreado fallido. Se actualiza la expectativa de sombra del CTA y se mantiene el sizing en la primitive compartida, limitando sólo su contenedor del Map.

Phase 6 commit: `9bd5577`.

Phase 7: se eliminan las entradas decorativas de Overview y el desplazamiento hover de los filtros KPI del Hub; Map declara propiedades explícitas y foco por teclado responde sin transición. Busy/ejecución y cleanup permanecen intactos. improve-animations produjo un plan acotado y una auditoría delegada read-only; review-animations: **Approve**, sin hallazgos pendientes en el diff. QA: 7 browser pasan; feel check con preferencia normal/reduce, 12 ciclos de revisión/Escape con foco restaurado, seis secciones sin animación, KPI sin desplazamiento y reproducción a 0.2×. Se actualizan dos expectativas históricas: el baseline ya tenía diálogos instantáneos y no contenía data-select-case; se preservan asserts de teclado, preferencia, navegación y exclusividad.

Phase 7 commit: `f9c3a46`.

Phase 8: comparación visual, pruebas adversas y cierre. Se corrigen el marcador móvil de siguiente decisión, cifras medianas del Center, contraste de ID bajo hover y altura del CTA de entrada mediante la variante compartida. Se amplía la fixture de Team con árabe y nombre vacío. La prueba de contexto/CTA de Saga 5 pasó al repetirla aisladamente tras un fallo de arranque sin error JavaScript; no requirió cambios funcionales. La antigua prueba Home/Center exigía heroes idénticos y un enlace que ya no existía en el baseline. Ahora verifica legibilidad, tamaño de objetivo, ausencia de overflow y el mismo recorrido al catálogo, conservando foco e historia.

## Commits

| Fase | Commit | Resultado |
| --- | --- | --- |
| 1 | `33b11dc` | Dation Precision: tokens y primitivas |
| 2 | `e1ebb98` | Shell y Home |
| 3 | `f89b4d3` | DDA y workflow del Case |
| 4 | `11d9e43` | Configuración de Assignment y Scheduling |
| 5 | `9c64b2f` | Dashboards de decisiones |
| 6 | `9bd5577` | Superficies de plataforma |
| 7 | `f9c3a46` | Interacción y motion |
| 8 | Este commit | Visual QA, break-ui y documentación |

## Transformación revisada

| Before | After | Por qué |
| --- | --- | --- |
| Shell con bloques redondeados y varias capas azules | Rail mineral, marca más clara, selección lineal y cuenta abierta | Un marco común que deja protagonismo a la decisión |
| Home con ilustración genérica y siete tarjetas equivalentes | Bienvenida editorial, cadena Data Pack/Case/Run y Logística destacada | Explica el producto y hace evidente la capacidad disponible |
| Overview como secuencia de tarjetas | Introducción y proceso en composición editorial, requisitos y FAQ abiertos | Mejora el ritmo y la lectura sin cambiar contenido ni destinos |
| Atributos/Owner dentro de una única tarjeta y CTA superpuesto | Dos zonas de preparación, archivos tipados y CTA en flujo normal | Se distinguen los cuatro requisitos y Aplicar queda expuesto |
| Map con tres columnas de tarjetas anidadas | Carriles conectados con estado, evidencia y Owner separados | Se reconoce la dependencia entre decisiones y su responsable |
| Config con bloques de controles poco diferenciados | Columna de criterio y plano de controles, selección lineal | Permite escanear alcance, objetivo, recursos y reglas |
| Resultados con foto de fondo y KPI como tarjetas grandes | Marco analítico, bandas numéricas, comparación/calendario junto a explicación | El resultado y su evidencia dominan; la aprobación sigue vinculada al Run |
| Center/Hub con heroes altos y métricas en cajas | Headers operativos, KPI en bandas e inventarios coherentes | Lleva filtros y datos al área de trabajo |
| Settings/Profile con formularios genéricos | Explicación y formulario separados, plano de edición consistente | Hace visible qué puede editarse y dónde guardar |

El gate visual se revisó con capturas lado a lado de las 13 superficies, en escritorio y teléfono, además de las hojas de contacto. Cambian composición, jerarquía, geometría de paneles y distribución; no se limita a ajustes de hover o foco. Las cifras y nombres de las capturas pertenecen a fixtures sintéticas existentes y no representan datos productivos.

## Capturas Before / After

Raíz de artefactos en este entorno: `/workspace/work/visual-product-upgrade/`. `before/` conserva las 28 capturas iniciales; `after/` contiene 67 observaciones finales. `comparisons/` contiene 26 comparaciones lado a lado, con el mismo prefijo de archivo. `screenshots.json` enumera rutas y hashes. No se incorporan imágenes de QA como assets del producto.

| Superficie | Archivos comparados en before/, after/ y comparisons/ |
| --- | --- |
| Home | `home-1440.png`, `home-375.png` |
| DDA Overview | `overview-1440.png`, `overview-375.png` |
| Case Data | `data-1440.png`, `data-375.png` |
| Decision Map | `map-1440.png`, `map-375.png` |
| Assignment Config | `config-d1-1440.png`, `config-d1-375.png` |
| Scheduling Config | `config-d2-1440.png`, `config-d2-375.png` |
| Assignment Dashboard | `dashboard-d1-1440.png`, `dashboard-d1-375.png` |
| Scheduling Dashboard | `dashboard-d2-1440.png`, `dashboard-d2-375.png` |
| Decision Center | `center-1440.png`, `center-375.png` |
| Data Hub | `hub-1440.png`, `hub-375.png` |
| Team | `team-1440.png`, `team-375.png` |
| Settings | `settings-1440.png`, `settings-375.png` |
| Profile | `profile-1440.png`, `profile-375.png` |

Se revisaron también `dashboard-d1-advanced-1440.png` y `dashboard-d2-advanced-1440.png`. `reflow/` registra otros 67 estados en viewports extremos. `break-ui/` conserva Empty/One/Worst case, Team multilingüe y Case/Map con contenido largo. El flujo E2E real deja screenshots y traces en `e2e-verified/golden-v2/`.

## QA final

| Verificación | Resultado y alcance |
| --- | --- |
| Python | 383 tests pasan; ejecución completa al cerrar Phase 6. Los cambios posteriores de aplicación son CSS |
| Node | 124 checks en 18 archivos pasan; sintaxis de los dos módulos JS modificados verificada |
| Browser crítico | 33 casos distintos verificados entre la ejecución conjunta y las repeticiones afectadas; incluye atributos antes de CSV, Saga 3/5, componentes, plataforma, Settings, UX y los cuatro stress tests |
| Interacción | 7 browser de motion/menús/foco/disposal pasan; feel check normal/reduce aprobado |
| Home/Center | Recorrido al catálogo y regreso por las cinco anchuras pasa; metadata bajo hover pasa en 1024 y 1440 |
| E2E real | 11 casos distintos verificados: los 10 casos de contrato/Saga pasan y el golden completo pasa tras las correcciones visuales |
| Responsive | 13 superficies en 1440×900, 1280×800, 1024×768, 768×1024 y 375×812; además 320×640, 812×375, 720×450, 375×420 y 2560×1440 |
| Geometría/contraste | 134 observaciones finales sin overflow de página; 130 auditorías de contraste muestreado sin fallos. Las cuatro capturas advanced adicionales verifican geometría |
| Zoom y teclado | Test existente de zoom/reduced-motion pasa; teclado, Tab/Shift+Tab, Escape, restauración de foco, scrollers locales y alturas reducidas verificados |
| Integridad | 812 archivos del baseline contrastados; los 120 protegidos conservan SHA-256; sin cambios inesperados de alcance |

El golden usa backend, base de datos aislada y motores reales con usuarios distintos. Verifica seis Runs, cuatro eventos de aprobación, actores, vínculos upstream, nueva corrida y stale downstream; también la navegación entre Home, Data, Map, Config, Dashboard, responsabilidades, Case completado, Center y Hub. Las otras pruebas E2E comprueban aislamiento entre workspaces, Viewer y ejecución/aprobación por el Owner asignado. Ninguna prueba escribe en producción.

La ejecución inicial de cierre detectó dos problemas visuales reales y un arranque fallido de fixture; se conservaron esos logs y se repitieron los casos afectados. No se declara verde la suite monolítica histórica completa de NavigationTests: las incompatibilidades anteriores están registradas en `docs/ux-ui-upgrade-implementation-summary.md`. Las expectativas visuales modificadas aquí mantienen verificaciones de contenido, permisos, navegación, exportaciones y foco.

## break-ui

El toggle **Demo data / Worst case / Empty / One** sigue siendo exclusivo de tests: `backend/tests/browser/fixtures/ux-upgrade-stress-toggle.js`. No se añade una ruta ni un control al producto. Se aplicaron las correcciones dentro de la autorización de implementación del master.

| Campo | Fuente / límite | Valor probado |
| --- | --- | --- |
| Case | `app/models/case_identity.py`: label 120, descripción 1000 | Nombre operativo largo y textarea real de 1000 caracteres |
| Identidad | Perfil: 100 caracteres por nombre; email 254 | Apellidos compuestos, email extenso, emoji ZWJ, árabe, CJK, vietnamita, Jo, J y nombre vacío en Team |
| Team | API paginada: 25 por defecto, máximo 50 | 25 filas, total 1284, tres roles de acceso, responsabilidades presentes/ausentes y estados active/disabled |
| KPI | Enteros publicados por API, sin límite visual específico | 0, 1, 1284, 1.000.000 |
| Dataset | Filename y row_count publicados; sin límite visual de filename | CSV operativo largo y 1284 registros |
| Valores | Formateadores existentes, sin cambiar cálculo | Moneda 12345678.9, negativo, cero, uno, decimal y null |
| Estados | Fixtures existentes y golden | Vacío, carga, error, disabled, aprobación, stale, Viewer, Owner y Admin; salida de Team durante fetch |

| Severidad | Qué se rompió | Causa | Corrección verificada |
| --- | --- | --- | --- |
| Broken | Marcador siguiente decisión sale del Map a 390 px | Regla móvil de ancho 100% también alcanzaba al marcador absoluto | Ancho intrínseco limitado al carril en decision-map-case-v2.css; test a 320/375/390/1440 |
| Ugly | 1284 se parte en dos líneas a 320 px | El valor de tamaño 36 quedaba en una celda estrecha | Tamaño según container query y nowrap; se conserva precisión y formato del workspace |
| Broken | ID del Case bajo hover mide 4,40:1 | Texto muted sobre superficie hover más clara | Metadata de tabla usa texto secundario; auditoría de contraste y golden pasan |
| Fragile | CTA de entrada queda a 40 px en teléfono | La primitive lógica min-block-size prevalece sobre min-height local | Variante compartida de hero usa control-height-lg; recorrido browser pasa con objetivo ≥44 px |

Resistieron sin cambios funcionales: nombres y archivos largos, email, avatar emoji, valores nulos, formateadores, los estados 0/1/empty, paginación y desmontaje durante fetch. Los nombres sin valor mantienen el email identificable. No se modifica schema para imponer límites nuevos ni se añade virtualización a una lista ya paginada. No hay findings funcionales pendientes que requieran una decisión de producto.

## Skills y revisión de criterio

- `ui-ux-pro-max`: contraste, densidad, formularios, estados, tablas y objetivos táctiles; se contrastó la recomendación con la arquitectura actual.
- `design-taste-frontend`: direction draw existente, seed registrado, adaptación por restricciones, revisión de composición y probe app sobre las pantallas reales.
- `emil-design-eng`: estados activos, foco, presión, consistencia y ausencia de movimiento decorativo durante trabajo frecuente.
- `improve-animations`: auditoría read-only delegada, tres hallazgos concretos, plan y ejecución acotada.
- `review-animations`: veredicto **Approve** sobre los cuatro CSS del pulido; complementado con verificación browser.
- `break-ui`: valores plausibles y límites reales mediante fixtures, toggle exclusivo de tests, reporte y correcciones verificadas.

Los artefactos de Taste conservan salida cruda y revisión. El harness corrige tres limitaciones de medición del probe, sin cambiar Skills ni reglas: el primer h1 del DOM puede pertenecer a una vista oculta, el walker contaba texto sin caja visible y los offsets transparentes del timeline se contaban como colores pintados. Se filtran esos casos en el harness, conservando contenido y estilos de la aplicación. Las 65 observaciones app finales registran **0 FAIL**; las advertencias repetidas se revisaron por patrón. El timeline conserva sus colores de Programado/Margen/Fuera de fecha y los neutros de ejes y fondo; no cambia series ni leyendas para satisfacer una heurística de conteo de color.

El lint de las declaraciones CSS añadidas registra **0 FAIL / 13 WARN**. El lint de archivos completos mantiene coincidencias de gradients heredados que la cascada actual oculta o reemplaza. Se revisaron en render, no se borró CSS histórico ajeno al alcance. Las advertencias de tamaño de título, borde, radios, iconos y densidad se evaluaron contra el brief: bienvenida editorial y títulos operativos; bordes de controles accesibles; estados semánticos conservados; tabla compacta; formulario Profile de ancho legible. Las secciones inferiores siguen en scroll natural, sin esconder información ni inventar datos para rellenar el canvas.

## Preservación y límites

Los únicos cambios de aplicación son 18 CSS existentes y dos módulos de presentación: Home sustituye una ilustración por una cadena estática; Scheduling intercambia el orden de timeline/insights conservando IDs, binders y contenido. No hay nuevos archivos CSS, dependencias, assets, fuentes, stores ni framework.

Case, Data Pack, Decisions, Runs, aprobación humana, invalidación downstream, motores, APIs, persistencia, tenancy, permisos y rutas conservan sus contratos. Tampoco cambian defaults, opciones, payloads, exportaciones, fingerprints ni sesión. La documentación funcional y los cuatro documentos del upgrade anterior permanecen intactos.

Las capturas principales usan APIs interceptadas y se complementan con el golden de motores reales; no equivalen a comprobar todos los datos posibles de producción ni todos los navegadores. QA de render realizada en Chromium. Los archivos de evidencia están fuera del repositorio y corresponden a este entorno. Quedan fuera de esta etapa nuevos features, cambios de dominio, localización RTL completa y cualquier rediseño que exija cambiar contratos.

## Publicación

Se mantiene la implementación en `ux-ui/visual-product-upgrade`, con un commit por fase. **No se hace merge ni push a main, despliegue manual o cambio de infraestructura/configuración productiva.**
