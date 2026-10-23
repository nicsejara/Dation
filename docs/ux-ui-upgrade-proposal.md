# Dation · UX/UI upgrade proposal

Fecha: 2026-10-23 · Base: `1477b41` · Estado: propuesta conceptual, pendiente de aprobación.

Esta propuesta deriva de los 24 hallazgos de la [auditoría](ux-ui-upgrade-audit.md). No constituye un Design System definitivo y no añade tokens, CSS, componentes, dependencias ni cambios funcionales.

## Dation Design Principles

1. **El Case orienta.** Nombre, datos, responsables y Decision actual deben poder reconocerse sin recorrer grandes bloques introductorios. Cada navegación conserva su responsabilidad.
2. **La evidencia merece el primer plano.** Los valores, excepciones y contexto que sustentan la decisión tienen más peso que los marcos, la fotografía o el texto promocional.
3. **Cada número dice qué mide.** Unidad, denominador, alcance y estado acompañan al dato. Participación de carga propia, utilización y disponibilidad temporal son conceptos distintos.
4. **Densidad con legibilidad.** Se compactan superficies y repeticiones antes de reducir el tamaño del texto. La interfaz sirve para uso frecuente, también con cuentas pequeñas y estados vacíos.
5. **Estado, selección y autoridad son distintos.** Estar seleccionado no significa estar aprobado; estar data-ready no equivale a poder ejecutar; una entrada fija no es una dependencia bloqueada.
6. **Los componentes comparten comportamiento probado.** Se mejoran primitivas y componentes existentes; Assignment y Scheduling mantienen sus propios contenidos y storytelling.
7. **La interacción respeta el ritmo de trabajo.** Foco visible, respuesta inmediata y recuperación clara. El movimiento sólo se usa cuando explica una transición y no retrasa la acción.
8. **La sofisticación surge de la precisión.** Marca, contraste, alineación y vocabulario consistente aportan confianza. No hace falta una estética de startup IA ni una nueva capa de efectos.

## Visual Direction

**Claridad operacional sobre una base oscura mineral, con identidad teal contenida.** Conservar el carácter actual de Dation y reducir el peso de marcos, glows y capas que compiten con información. La continuidad visual debe venir de bordes compartidos, niveles tipográficos claros, densidad por tarea y estados semánticos estables.

La firma propia de Dation es la trazabilidad visible **datos → Case → Decision → Run → evidencia → aprobación**. Esa estructura ya existe y debe reconocerse en el contexto y el relato de resultados. No se propone convertirla en una nueva visualización, otra navegación o un componente decorativo.

Las pantallas de trabajo deben sentirse como una herramienta analítica madura. Overview conserva su función explicativa; Config y dashboards necesitan llegar antes a criterios y evidencia. Home mantiene hero, accesos y catálogo actuales. Las fotografías de camión pueden conservarse: su sustitución es P3 y debe decidirse comparando variantes, después de resolver densidad.

### Decisiones de criterio de las Skills

| Fuente | Se adopta | Se adapta o descarta |
| --- | --- | --- |
| UI UX Pro Max | Jerarquía, tipografía por rol, contraste, foco, errores, tablas y responsive | El resultado genérico de marketing, nueva paleta azul/amber, otra pareja de fuentes y GSAP no corresponden al producto existente |
| Taste, app/existing review | Pregunta operativa por pantalla, marcos discretos, alineación numérica, densidad y datos honestos | No se eliminan heroes, Case Context, KPIs o información necesaria por una regla estética; tampoco se impone negro puro ni un máximo arbitrario de colores |
| Emil | Decidir motion por frecuencia, feedback de input, foco y propósito | No se aplican springs, blur, stagger o escala en todos los controles por defecto; no se añade framework de animación |

Tampoco se adoptan las sugerencias de recalcular totales desde importes redondeados, cambiar KPIs globales para que sigan un filtro local, elegir por defecto una nueva visualización o modificar el flujo para lograr una composición. Los contratos de Dation tienen prioridad.

## Recommended Design System evolution

Evolucionar el sistema existente en `tokens.css`, `dation-design-system.css`, `platform-components.css` y `workflow-context.css`. Registrar primero qué rol cumple cada valor y qué consumidores dependen de él. El orden es **token → primitive → shared component → ajuste de página**.

Las bandas siguientes son criterios para comparar propuestas, no nuevos tokens aprobados ni una especificación CSS para aplicar automáticamente.

| Área | Dirección recomendada | Preservación y aceptación |
| --- | --- | --- |
| Typography | Familia actual como primera opción. Títulos de trabajo normalmente 24–32 px; títulos de sección 16–20; cuerpo operativo 13–14; labels/meta 12–13; captions de 11 sólo cuando corresponda. Altura de línea según rol: encabezados compactos, lectura sostenida más abierta. | Evitar los 9–10 px actuales en estado/ownership. Verificar fuente efectiva y cifras tabulares. Sin límite rígido de dos líneas que corte contenido necesario. UX-005/023. |
| Numeric typography | Tabular-nums y borde derecho común para valores comparables; precisión estable por métrica. Unidades junto al dato y un espacio coherente entre valor/unidad. | No recalcular solver, redondeo contable ni fingerprints; un cero no sustituye un dato ausente. UX-007/009/017/018. |
| Spacing | Mantener la base de 4 px y sus roles actuales. Distinguir separación dentro de grupo, entre grupos y entre secciones. Reducir padding y alturas mínimas vacías antes de reducir letras. | Reservar espacio dinámico para sticky y foco. No reemplazar globalmente todos los espacios por un valor compacto. UX-002/003. |
| Surfaces | Fondo, panel y overlay con responsabilidades claras. Superficie opaca en contenido de trabajo; una diferencia tonal o borde discreto como separación principal. | Mantener tema oscuro y contraste. Un borde estructural no exige por sí mismo 3:1; un borde necesario para identificar un control sí requiere evaluación no textual. UX-013. |
| Radii | Usar los roles existentes para control, card, hero y overlay; resolver valores locales sin significado propio. | No imponer 8 px a todos los componentes ni cambiar radios por gusto como requisito MVP. UX-013. |
| Borders | Discretos para agrupación; inequívocos para control, foco y selección. Evitar varios bordes fuertes anidados alrededor de un mismo dato. | Distinguir hover, selección y foco sin depender sólo del color. Preservar hooks de CSS y orden de estilos. UX-013. |
| Shadows | Profundidad útil para menú, dialog y drawer; reducir sombras repetidas sobre paneles en reposo si compiten con datos. | No eliminar señales de overlay o confirmación. UX-013. |
| Semantic colors | Mantener teal de marca/selección, verde de aprobación/success, amber de atención, rojo de error y neutrales de metadatos. Mantener los estados canónicos y añadir claridad de etiqueta cuando el significado cambia. | Ningún color habilita una acción. No homogeneizar aprobación, readiness y resultado con excepciones. UX-010/012. |
| Primary actions | Una familia visual coherente por rol y contexto; variantes compactas para listas y cómodas para formularios. Comparar fill plano frente al gradiente actual sin convertir esa preferencia en una regla de negocio. | Conservar Apply, Revisar y ejecutar, Ejecutar y Aprobar como acciones distintas. UX-012. |
| Interaction states | Normal, hover, active, focus-visible, selected, disabled, busy, success y error definidos por componente y rol. | No mover el layout al presionar; mantener disabled real, motivo del bloqueo y prevención de doble envío existentes. UX-011/014/016. |
| Widths and density | Alinear gutters y bordes de lectura. Permitir diferentes anchos por tarea: formulario, portfolio y evidencia no tienen que compartir un único máximo. | Mantener regiones de scroll local, datos completos y layout específico D1/D2. UX-003/007/015. |

La validación de la tipografía y los estados debe hacerse sobre contenido real largo, vacío y de error. La dirección no incluye un tema claro nuevo ni una nueva biblioteca de componentes o charts.

## Shared Components to upgrade

| Orden | Componente existente | Evolución propuesta | Hallazgos | Riesgo |
| ---: | --- | --- | --- | --- |
| 1 | Workflow action bar + coexistencia con formularios | Altura y reserva reales; foco completamente visible; cuatro requisitos legibles | UX-002/003/005 | MEDIUM |
| 2 | Tipografía, métricas y primitives de acción | Roles legibles, alineación de números, hit areas, estados y variantes | UX-005/007/012/016/018 | LOW–MEDIUM |
| 3 | Context Navigation + Case Flow | Misma información y destinos con menos ocupación; paso actual visible en móvil | UX-003/004 | MEDIUM |
| 4 | Workflow Hero / page header / Case Context | Densidad por tarea, variantes copy-only, títulos y contexto proporcionados | UX-003/005/013 | MEDIUM |
| 5 | Shell y controles globales | Iconos SVG locales, bypass al main y foco de vista sin competir con restauración de dialog | UX-019/020 | MEDIUM |
| 6 | Search/filter row y tablas | Identificación visible compacta, columnas numéricas por rol, scroll con contexto | UX-007/015/016 | LOW |
| 7 | Result summary, toolbar y launcher IA | Precisión de relato, zona segura, acciones y contexto de aprobación legibles | UX-008/009/010/018 | MEDIUM |
| 8 | Error/loading/empty presentation | Estados humanos y geometría útil, conservando clasificación y reintentos | UX-011/014 | MEDIUM |
| 9 | Dialog, dropdown, accordion y tooltip | Consolidar foco, anchors y feedback; motion sólo después de resolver la base | UX-016/024 | LOW–MEDIUM |

No se propone un mega-componente que configure todos los dashboards, otro store ni un segundo selector global de Case. Se reutilizan `createScope`, cleanup, aborts, binder de presentación y componentes de revisión/toolbar.

## Page-specific upgrades

| Pantalla | Pregunta principal | Evolución propuesta |
| --- | --- | --- |
| Home / catálogo | ¿Dónde empiezo o a qué área voy? | Conservar saludo, hero, quick access y catálogo actuales. Mejorar ritmo y texto pequeño; explorar menor énfasis de futuros DDAs sólo como P3. No agregar métricas ni actividad ficticia. |
| Decision Center | ¿Qué Case o decisión requiere que actúe? | Reparar labels KPI móviles; clarificar filtros, cifras y estados. Mantener atención accionable, agregados globales, historial, archivo y acceso exacto al Run elegido. No cambiar el agregado para que siga la página o filtro. |
| DDA Overview | ¿Qué resuelve hoy y con qué datos? | Resolver UX-001: explicar núcleo mínimo, etapas actuales, capacidades condicionadas y límites reales. Preservar iniciar Case/ver casos y D3 futuro. |
| Datos del Case | ¿Está preparado este contexto para decidir? | Reducir hero vacío, exponer formulario y Data Owner, reparar sticky y mantener validación/compatibilidad con cuatro requisitos independientes. No registrar un Case vacío para simplificar la UI. |
| Decision Map | ¿Qué decisión puedo revisar o ejecutar? | Hacer más compactos hero y progreso; dar prioridad a nodos y responsabilidades. Mantener D1/D2 y D3 visible deshabilitado. Explicar que el total de aprobaciones corresponde a decisiones implementadas. |
| Config D1 | ¿Qué carga, prioridad y política quiero ejecutar? | Llevar alcance, objetivos y recursos antes a la lectura; mejorar presets/selección y revisión sin cambiar defaults ni capacidades habilitadas. Las fechas siguen en D2. |
| Config D2 | ¿Cómo quiero secuenciar los viajes aprobados? | Resaltar fuente aprobada, ventana y reglas temporales; mejorar claridad de controles y validación. Conservar viajes, vehículo y carga fijos; no volver a ofrecer asignación de recursos. |
| Execution | ¿Qué está ocurriendo y cómo recupero el trabajo? | Mantener etapa real y progreso indeterminado; jerarquía de espera, recuperación y error coherente con otras vistas. No introducir ETA, porcentaje, cancelación o retry automático no existentes. |
| Dashboard D1 | ¿Cómo se distribuyó la carga y qué evidencia respalda aprobar? | Corregir cuota propia, alinear comparación y priorizar plan, restricciones y evidencia; fotografías opcionales. |
| Dashboard D2 | ¿Cuándo se ejecuta y qué excepciones tiene? | Aclarar upstream fijo, SLA y margen; mantener timeline, ocupación con retorno y fechas. La calidad del plan y la aprobación se muestran como dimensiones distintas. |
| Data Hub | ¿Qué datos tengo, con qué calidad y dónde se usan? | Consistencia de filtros, tablas y detalle; conservar preview, uso, descarga protegida y ciclo de vida actuales. No incorporar carga global ni redefinir Data Packs. |
| Team | ¿Quién tiene acceso y responsabilidad? | Hacer más claros rol/responsabilidad/estado; normalizar fallo de invitaciones y reforzar scroll de tabla móvil. Mantener Invitar como entrada principal y aclaración de que no envía correo. |
| Settings / Profile | ¿Qué puedo editar y cómo se guarda? | Alinear tipografía, formularios y carga; mantener labels, tabs, guardado y readonly actuales. Perfil no debe convertirse en un nuevo modelo de permisos. |

En la versión actual, Home y catálogo comparten la superficie. La documentación histórica de Home V2 no autoriza reinstalar automáticamente secciones anteriores. Del mismo modo, un detalle de Center que hoy se abre como modal no debe cambiarse a aside únicamente para igualar un documento de fase anterior.

## Dashboard direction

### Assignment

Mantener una narrativa de **distribución y recursos abstractos**, sin calendario:

- Resultado persistido y estado vigente del Run claramente asociados al Case.
- Carga total, viajes, participación de carga propia y utilización con denominadores precisos.
- Costo y CO₂ sólo cuando estén habilitados por los datos y contrato efectivo; no habilitarlos desde diseño.
- Comparación de escenarios con cifras alineadas y seleccionado inequívoco; referencias sintéticas nunca se convierten en ahorro real observado.
- Vista rápida y plan completo conservados, con vehículos/cargas/órdenes y explicación del solver cuando corresponda.

La frase ejecutiva propuesta cambia el lenguaje de la métrica, no su valor: “Mover [carga] en [viajes], con [cuota] de la carga en flota propia”. El texto se construirá desde la misma evidencia actual.

### Scheduling

Mantener una narrativa de **calendario, servicio y ocupación**, con upstream explícito:

- Run Assignment fuente aprobado, mismo Case y Data Pack.
- Ventana/horizonte, nivel de servicio, espera y recurso crítico como medidas temporales distintas.
- Timeline por recurso que incluya retorno; leyenda próxima y tabla equivalente accesible.
- Excepciones visibles con fecha objetivo, llegada y margen claramente nombrado.
- Mismos viajes, cargas, rutas y vehículos del handoff; ningún control o gráfico debe sugerir que D2 los reasigna.

### Disciplina BI común

Una pregunta principal por bloque; ejes con unidad, leyendas que expliquen las marcas, semántica estable del color y detalle equivalente para teclado/lector de pantalla. No dibujar nuevas curvas, deltas o benchmarks si no hay evidencia persistida. Conservar tablas y CSV/JSON. El disclosure visual avanzado mantiene su estado por Run y no sustituye la configuración de profundidad de cálculo.

El estado de aprobación debe seguir mostrando al actor histórico real. Cambiar el Decision Owner actual nunca reescribe esa atribución. El frontend no deduce vigencia desde una etiqueta verde ni desde `state_json` cacheado.

## Interaction / motion direction

Feedback de color/borde inmediato para controles frecuentes. Los estados busy indican la operación real, mantienen label comprensible y respetan el guard de doble envío existente. Hover sólo complementa la interacción y no es el único acceso a información; en touch no debe quedar un efecto decorativo pegado.

Para dropdown, popover o drawer ocasional, comparar una transición corta —aproximadamente 120–200 ms según distancia— frente a apertura inmediata. El origen sigue al trigger si aporta continuidad. No se obliga a escalar todos los botones ni se anima el teclado por decoración. Reduced motion mantiene información y elimina desplazamientos innecesarios.

Se conservan dialogs nativos, Escape, trap/restauración de foco, cancelación por ruta y cleanup. No se añaden pantallas de transición, skeletons que inventen avance, stagger de filas, spring, blur o una librería nueva para este MVP.

## Accessibility upgrades

UX-002 se corrige al comienzo, no al cierre del proyecto. En cada lote verificar foco y semántica, names/labels, status legible y controles con área adecuada. No declarar conformidad sólo con un escaneo de contraste.

Mantener los pares de texto que ya funcionan y comprobar los compuestos finales al cambiar fondos, sombras o imagen. Conservar texto/icono para estado, regiones de scroll nombradas y alternativas a gráficos. Los datos que sólo aparecen en hover deben tener un acceso equivalente. Respetar zoom, password managers, nombres largos y lectores de pantalla sin rediseñar Auth.

## Responsive priorities

1. **375 px:** despejar el campo enfocado, reducir la altura del preámbulo y barra, revelar paso actual, reparar KPIs y separar launcher IA de datos/acciones.
2. **768 px:** sostener labels y pistas en grillas estrechas; revisar sticky, formularios y tablas sin reducir texto necesario.
3. **1024 px:** ajustar convivencia de sidebar, toolbar y canvas; conservar contexto y acciones al envolver controles.
4. **1440 px:** aprovechar ancho para comparación y evidencia, con ritmo más compacto y formularios de medida legible.

En cada ancho mantener todas las funciones existentes; si una tabla necesita scroll local, identificarlo y conservar acceso por teclado. No sustituir la navegación por tabs inferiores ni diseñar una aplicación móvil distinta.

## Acceptance boundary

La propuesta se considera concretada únicamente cuando exista evidencia de mejora visual y paridad funcional. Permanecen iguales Case/Decision/Run, Data Pack, ownership, aprobación, invalidación, rutas, sesiones, API, motores y resultados. Los tres documentos de esta entrega son planificación; el próximo trabajo requiere aprobación del alcance y se ordena en el [roadmap](ux-ui-upgrade-roadmap.md).
