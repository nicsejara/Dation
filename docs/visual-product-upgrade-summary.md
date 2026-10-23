# Dation Precision — Visual Product Upgrade

Estado: en implementación. Base: `0adc473`. Rama: `ux-ui/visual-product-upgrade`.

## Dirección y sistema

La cadena datos → Case → Decision → Run → evidencia → aprobación es la firma de Dation Precision: estructura lineal, planos de grafito mineral y selección mediante borde teal. Inter, contenido y comportamiento se conservan. No se crean datos, métricas, navegación ni dependencias.

Taste: existing app redesign; `data-terminal`, seed `2039572090`. Se adopta selección lineal y precisión tabular. Se adapta el rail propuesto a la navegación etiquetada y destinos existentes. La marca mineral/teal, heroes y estados exigidos por el brief prevalecen sobre el negro puro, nuevas fuentes y patrones genéricos. UI UX Pro Max: resultado verificado `data-dense-dashboard`; se descarta Enterprise Gateway de marketing.

El sistema evoluciona en tokens → primitivas → componentes → composición. Base `#10161c`, panel `#19242d`, grupo `#202e39`, overlay `#22323e`; texto principal/secundario conservado, borde de control más visible. Radios por rol 4/6/8/12/16. Títulos 28–36, secciones 20, cuerpo 14, metadatos 12. Cifras tabulares, header discreto; sombras en overlays.

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
