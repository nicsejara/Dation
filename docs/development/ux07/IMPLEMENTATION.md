# UX07 — implementación focal

Baseline: main `0e5e7c93e942822aaf8a38d1c60fd7db332b9f5d`, PR122 integrado. Rama `feat/saga-ux07-visual-refinement`. Sin merge ni despliegue.

|Bloque|Owner de markup/estado|Owner de presentación|
|---|---|---|
|01 Home|home-dda-catalog.mjs; shell.mjs sólo estado Home|home-dda.css|
|02 Landing/nav|app.html sólo copy; destinos existentes intactos|dda-logistics-landing.css; platform-shell.css|
|03 Core|wizard-ui.mjs layout de footer; planning-model.mjs copy contextual; core-preparation.mjs copy|ultimate-foundation.css scoped a unified-journey|
|04 Rails|navigation.mjs sólo wrapper de copy Studio|ultimate-foundation.css familia común Core/Studio|
|05 Intro/Graph|node-graph.mjs sólo dibujo; estados existentes|ultimate-foundation.css intro; ultimate-graph.css círculos/conectores|
|06 Panel|command-center.mjs toggle; decision-popover.mjs SVG local|ultimate-graph.css cierre|

## Resultado por bloque

1. **Home:** colección de presentación `HOME_DDA_CATALOG` de seis entradas. `DDA_CATALOG` y el registro compartido conservan siete. Tarjetas equivalentes, grilla 3/2/1 y filtros de seis categorías con columnas iguales. Se oculta solamente la topbar contextual de Home; vuelve al salir de esa vista. El entitlement sigue determinando la disponibilidad de Logística.
2. **Landing y navegación:** cuatro tracks estables, sin elementos ficticios para completar los dos niveles iniciales; reflow a dos columnas cuando falta espacio. Hero con título hasta 48px y dos acciones iguales de 48px de alto. El secundario dice «Ir al Decision Center»; su handler y filtro logistics no cambian.
3. **Core:** headers con la misma escala, tiles y altura mínima; descripción larga con reflow. Footers con Previous, progreso y acciones en tres zonas. Se mueven los elementos existentes conservando formulario, referencias, callbacks y Files. Previous tiene SVG y nombre accesible del destino real. Se cambian únicamente los copys aprobados de creación/avance; publicación pendiente, retries y «Guardar contexto» conservan su semántica. El flag `unified` limita el nuevo copy de Model al Journey nuevo.
4. **Rails:** familia compartida Core/Studio de 216px y tarjetas de 136px en escritorio. En tablet se distribuyen tres columnas; en contenedores menores de 440px se apilan, evitando fragmentar los nombres de etapas. Studio conserva tres destinos y sus permisos, estados y `aria-current`.
5. **Intro y Graph:** divisor y tipografía compartidos, sin añadir `d-platform` al Graph ni cambiar sus controles globalmente. Tres círculos del mismo diámetro, tracks y centros equidistantes. Conectores CSS sin glifos ni ResizeObserver de alineación. En contenedores estrechos se disponen verticalmente. La dependencia y sus colores/mensajes conservan la fuente de estado anterior; el futuro sigue siendo inerte.
6. **Panel:** SVG local centrado en un cierre de 44px. Un segundo click en el nodo abierto invoca el cierre existente, con devolución de foco y disposición de scope. Otro nodo sigue conmutando el panel. No se agregan rutas, persistencia, peticiones ni listeners globales.

## Archivos y justificación

Los owners de la tabla anterior reúnen todos los cambios de producto: cinco hojas de estilo, diez módulos de presentación y un copy en `app.html`. `ultimate-case-setup.mjs` pasa el contexto unified y recoloca el footer existente; no cambia serialización, validación ni creación. `core-preparation.mjs` mantiene los botones reales dentro del nuevo wrapper de acciones, incluso al adjuntar contratos tardíamente.

Pruebas: `test_home_dda_catalog.mjs` separa explícitamente seis visibles de siete compartidos; `wizard_helpers.py` selecciona el copy correcto según el Journey; `test_navigation.py`, `test_final_polish.py` y `test_home_hero.py` actualizan expectativas visuales aprobadas. `test_journey_navigation_ux06.py` adapta selectores al wrapper y sigue midiendo todos los controles. `test_visual_refinement_ux07.py` añade geometría responsive, flujo real de publicación/CSV/creación y cierre local del panel.

## Verificación y correcciones focales

- Home y landing usan el fixture sintético existente, sin iniciar SQL para medir CSS.
- Core/Graph usan el fixture funcional existente porque la prueba también publica un Model, guarda dos CSV y crea un Case real local. No hay conexión a datos productivos.
- Se corrigieron una diferencia real de 3px en el footer de Contract por especificidad heredada y un solapamiento de Previous/progreso a 200% por la misma causa en la regla responsive.
- La nueva prueba se ajustó para medir el footer efectivamente visible, en lugar del primero cuyo padre estaba oculto. El clic exterior selecciona el heading accesible de Studio, sin ambigüedad entre vistas desmontadas/ocultas.
- La revisión visual final detectó que el H1 sin clases de Landing seguía en 36px por `.d-page-hero h1`. Se corrigió el selector dentro del contenedor real `.dda-landing` y se agregó una assertion del tamaño computado 32–48px en seis anchos. La CI anterior 43971848532 fue cancelada; no se completó otra suite integral para ese candidato.
- La expectativa anterior que igualaba la altura del CTA Home con Landing ahora exige explícitamente 48px para Landing; conserva las restantes comprobaciones de frame, copy, ink, padding y Home. El nuevo test exige igualdad entre ambos CTA de Landing en seis anchos.

No se editan `foundation-v2.json`, callbacks de publicación/carga, router, permisos, progreso real, backend, SQL, motores, infraestructura ni workflows. El clasificador vigente se conserva: el test unitario compartido es una ruta R3 y exige FULL además de FAST. No se evita ni se fuerza una degradación del riesgo.

Inicio de implementación: 2026-11-16 18:56:24 ART (21:56:24 UTC). Resultado terminal, SHA y duración final se registran en el PR y sus checks para evitar un nuevo commit/suite sólo para actualizar un contador. Véanse [QA](QA.md), [evidencia](evidence/) y [activación futura](ACTIVATION.md).
