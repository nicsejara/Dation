# Dation · UX/UI upgrade roadmap

Fecha: 2026-10-23 · Base de planificación: `1477b41`.
Estado: **en ejecución autorizada** por el master prompt del 2026-10-23. Base de implementación: `ee404b1`; rama local `ux-ui/commercial-mvp-upgrade`. No incluye publicación.

Fuentes: [auditoría](ux-ui-upgrade-audit.md), [propuesta](ux-ui-upgrade-proposal.md) y contratos funcionales actuales de `/docs`.

## Orden y criterio de alcance

El upgrade sigue las fases 0–8 solicitadas y prioriza **token → primitive → shared component → página**. Se resuelven UX-001 y UX-002 en el primer lote de implementación aprobado; su posición documental en el workflow no obliga a esperar a una fase posterior para corregir un P0.

Accesibilidad y responsive se comprueban en cada fase. Phase 7 es una validación integral y cierre, no el momento de descubrir por primera vez si el foco o el móvil funcionan.

| Categoría | Significado de esfuerzo |
| --- | --- |
| FAST | Ajuste acotado de copy/presentación con consumidores conocidos |
| NORMAL | Cambio de primitive o componente con varios estados/ancho a verificar |
| FULL | Trabajo transversal con múltiples consumidores y regresión de integración |

Son categorías de alcance, no compromisos de duración. LOW/MEDIUM/HIGH expresan riesgo de regresión funcional del cambio previsto. Un trabajo que exija tocar autoridad, datos, motor o navegación funcional queda fuera de este roadmap y requiere un alcance independiente.

## PHASE 0 · Design System foundation

**Scope.** Acordar principios, roles tipográficos y de densidad, superficies, jerarquía de acciones, formatos de métricas y estados. Inventariar los valores actuales y sus consumidores antes de promover una propuesta a sistema definitivo. Definir el primer lote P0: corrección del texto del Overview y exposición del campo enfocado bajo la barra.

**Dependencies.** Aprobación de la dirección conceptual y de un alcance concreto de implementación; baseline del árbol que realmente se vaya a modificar. Releer los contratos si cambió el código desde `1477b41`.

**Risk.** LOW mientras sea especificación; MEDIUM si se convierten roles globales en cambios masivos sin migrar consumidores. Evitar un nuevo sistema paralelo.

**Expected impact.** Un vocabulario común y criterios verificables para que cada pantalla no derive su propia escala o interpretación de estado.

**Components affected.** Matriz de `tokens.css`, `dation-design-system.css`, `platform-components.css`, `workflow-context.css`, formatos de plataforma y resultado.

**Findings.** UX-002/005/007/012/013/018; triage de UX-001. UX-023 permanece opcional.

**Acceptance.** Cada rol tiene consumidores y estado de migración; se preservan las escalas existentes donde ya sirven. Se acuerdan capturas de referencia y umbrales de aceptación a 1440, 1024, 768 y 375 px. No se añade una dependencia ni framework para resolver tokens.

## PHASE 1 · Global shell + primitives

**Scope.** Ejecutar el primer lote P0 aprobado, incluida la corrección de copy UX-001 aunque pertenezca al Overview. Reparar la convivencia de sticky/foco. Consolidar botones, inputs, selects, labels, focus-visible, hit areas, iconos del shell y acceso al main. Resolver los overrides tipográficos que afectan a estado o responsabilidad.

**Dependencies.** Roles de Phase 0, inventario de CSS y medición de altura real de barras/overlays. Mantener orden de estilos y hooks.

**Risk.** MEDIUM: los consumidores son numerosos y un ajuste de tamaño puede afectar wrapping o posición sticky. Los destinos del shell y el modelo de estado permanecen iguales.

**Expected impact.** Eliminar el bloqueo de edición móvil; unificar interacción básica y aumentar legibilidad con mejoras visibles en toda la plataforma.

**Components affected.** Workflow action bar, primitives de acción/formulario, shell, iconos locales, main/foco y copy del Overview.

**Findings.** UX-001/002/005/012/016/019/020; base de UX-013.

**Acceptance.** Reproducir el recorrido Nombre → Categoría → Descripción con Tab a 375×812 y comprobar el campo completo disponible, también con texto largo y teclado virtual. Verificar los cuatro requisitos y Apply sin mutar su lógica. Los estados disabled/busy conservan sus guards. El Overview explica D1/D2 y límites actuales sin habilitar capacidades futuras.

## PHASE 2 · Core workflow

**Scope.** Reducir ocupación de Context Navigation, Case Flow, Workflow Hero y Case Context mediante variantes de densidad. Hacer visible el paso actual móvil. Mejorar Datos y Map: contexto, progreso, tarjetas, responsables y explicación de bloqueo. Conservar D3 visible deshabilitado y el total real de decisiones implementadas.

**Dependencies.** Phase 1 estable y componentes canónicos de `component-map.md`. UX-001 ya debe estar resuelto en el lote inicial; aquí se integra su presentación final.

**Risk.** MEDIUM: navegación y estado se coordinan desde workspace; la modificación se limita a presentación, scroll y foco. No duplicar selectors ni coordinadores.

**Expected impact.** Llegar antes al formulario o decisión disponible y reconocer dónde está el usuario en el Case.

**Components affected.** `decisionHero`, `decisionCaseCard`, `case-flow.mjs`, `dda-navigation.mjs`, upload, Case Attributes, selector Data Owner, Map y Decision Owners.

**Findings.** UX-003/004/005/013/016; continuidad de UX-001/002.

**Acceptance.** Preparación antes de CSV, snapshot aplicado, recarga, inputs válidos y promoción al Case mantienen su contrato. Misma pareja de datasets conserva identidad por el contrato de reemplazo; pareja distinta abre otro Case y conserva evidencia. Archivo y falta de Owner mantienen guards. Volver desde Case Context vuelve al mismo Case; el Map no serializa `node_id`.

## PHASE 3 · Decision configuration

**Scope.** Ajustar jerarquía, alcance, objetivos/presets, recursos y revisión D1. En D2, fuente aprobada, ventana, reglas temporales, validación y revisión. Reducir preámbulo antes del primer control y conservar diferencias de dominio.

**Dependencies.** Phase 2, primitives de selección y roles de formulario. Readiness y opciones continúan viniendo de sus consumidores actuales.

**Risk.** MEDIUM: selección visual, configuración draft y configuración admitida pueden confundirse si se mezclan responsabilidades. Ningún cambio de presentación redefine defaults o pesos.

**Expected impact.** Configuración más fácil de leer, comparar y revisar, con menos scroll introductorio.

**Components affected.** `assignment-config.mjs`, `scheduling-config-v2.mjs`, editor de reglas D2, Decision Navigator, action bar, review dialog y validación existente.

**Findings.** UX-003/004/005/010/012/015/016.

**Acceptance.** Las mismas selecciones producen el mismo payload. Abrir Config o revisión no admite un Run. Escape y Volver restituyen foco; doble envío sigue protegido. D1 no introduce fechas/SLA; D2 no permite reasignar cargas o vehículos. Las condiciones de ejecución por Owner/admin y Viewer no cambian.

## PHASE 4 · Dashboards

**Scope.** Mejorar resumen de resultados, KPIs, tablas y contexto de aprobación. Corregir relato de cuota propia D1, etiqueta de entrada fija D2 y nombre del margen SLA. Ajustar zona del launcher IA, toolbar y densidad del shell. Afinar ejes, leyendas y scroll conservando todas las evidencias.

**Dependencies.** Formatos de métricas de Phase 0, primitives y contexto de Phases 1–3. Datos reales persistidos o fixtures consistentes de cada schema.

**Risk.** MEDIUM: renderer histórico, selección del Run y evidencia son sensibles. Cambiar cálculos, comparaciones de motor o autoridad elevaría el riesgo a HIGH y queda fuera de alcance.

**Expected impact.** La mejora comercial más visible después de la base: resultados más precisos, escaneables y confiables, con relatos distintos para distribución y calendario.

**Components affected.** `result-summary.mjs`, summary/essential/evidence de Assignment, essential/timeline/advanced de Scheduling, chart wrapper/theme, dashboard-presentation, toolbar/actions/approval trace y launcher IA.

**Findings.** UX-005/007/008/009/010/012/013/016/017/018. UX-021 es opcional, no requisito de cierre.

**Acceptance.** Comparar los mismos Runs antes/después: valores, schema, fingerprints, creator y actor histórico intactos. Abrir candidato o histórico conserva su `run_id`; lineage persistido gana al cache. Una nueva admisión D1 retira aprobación e invalida D2 incluso si falla, sin borrar historia; replay no duplica efectos. Esto se verifica en el stack aislado existente al integrar el upgrade, nunca provocándolo en producción.

El disclosure esencial/avanzado se restaura por Run, dibuja contenido lazy y limpia recursos. No se cambia `analysis_depth` del motor para obtener una vista más simple. Exportaciones y explicación IA siguen consumiendo la misma evidencia; no recalculan planes.

## PHASE 5 · Supporting screens

**Scope.** Alinear Home/catálogo, Decision Center, Data Hub, Team, Settings y Profile con la base aprobada. Resolver labels KPI y filtros, estados de carga/error, tabla móvil de Team y presentación de formularios. Mantener los flujos globales actuales.

**Dependencies.** Shell/primitives estables y política de error/formato acordada. Conservar contratos de resource por superficie y de búsqueda, paginación y selección.

**Risk.** LOW–MEDIUM. Presentación simple es LOW; focus/detail, CAS, loading o recuperación es MEDIUM. No redefinir funcionalidad de Data Hub ni responsabilidades de Team.

**Expected impact.** Que las pantallas de soporte tengan el mismo nivel de cuidado que la cadena logística.

**Components affected.** Home y catálogo, KPIs/lista/detalle de Center, biblioteca/detalle de Hub, Team/invitations, settings tabs y profile form.

**Findings.** UX-005/006/007/011/012/013/014/015/016/018/019. UX-022 es opcional.

**Acceptance.** KPIs globales de Center/Hub conservan su alcance aunque cambien filtros/página. Selección, filtros, drawer, recarga y Back/Forward preservan recursos y foco. Descargas siguen protegidas. Permisos, estados archived, CAS y guards de borrado no cambian. Team mantiene roles/responsabilidades distintas, un Invitar principal y ausencia de envío de email. Settings conserva preferencias/Free y Profile su endpoint existente.

No se reinstalan secciones históricas de Home, cargas globales ni navegación nueva sólo para homogeneizar composiciones.

## PHASE 6 · Interaction polish

**Scope.** Revisar estados de hover/active/focus/selected/busy y feedback de éxito/error; dropdowns, accordions, tooltip y popover. Probar motion sólo si aporta orientación. Alinear feedback de cargas con operación real.

**Dependencies.** Geometría final de componentes y flujos funcionales ya preservados. Es improductivo pulir movimiento antes de estabilizar el layout.

**Risk.** LOW–MEDIUM: bajo para color/borde; medio si interviene posición de overlay, foco, listeners o temporizadores. Conservar `createScope` y cleanup.

**Expected impact.** Uso frecuente más previsible, menor sensación de espera y feedback consistente sin decoración adicional.

**Components affected.** Primitives, review dialog, dropdown/dialog compartidos, toolbar, ejecución, disclosures y presentación de carga/error.

**Findings.** UX-011/012/014/016/020. UX-024 sólo si se aprueba su beneficio.

**Acceptance.** Respuesta al input inmediata y sin layout shift introducido por press. Escape, tabulación, cierre exterior aplicable y foco restaurado. No bloquear input esperando una animación; no añadir bounce, blur o stagger ornamental. Reduced motion conserva toda la información. Hover no es requisito exclusivo en touch ni teclado.

## PHASE 7 · Responsive / accessibility

**Scope.** Cerrar la matriz transversal con los componentes finales: tamaños, reflow, zoom, contraste, foco, labels, status, scroll local, gráficos alternativos, touch y teclado virtual.

**Dependencies.** Fases 1–6 implementadas y sus verificaciones locales aprobadas. Esta fase no permite posponer P0 anteriores.

**Risk.** MEDIUM por el alcance transversal; se corrige en el nivel canónico del patrón que falla, no agregando un override por cada captura.

**Expected impact.** Un MVP operable fuera de la resolución de demo y con condiciones de accesibilidad verificadas.

**Components affected.** Shell, Context Navigation, Case Flow, barras sticky, todos los formularios, tablas, charts, dialogs y launcher IA.

**Findings.** Revalidación de UX-002/003/004/005/006/007/008/015/016/019/020; estados relacionados en cada pantalla.

**Acceptance.**

- 1440×900, 1024×768, 768×1024 y 375×812, con scroll de página libre de overflow accidental y tablas desplazables en su región.
- Zoom 200 % y comprobación de reflow equivalente a 400 % cuando corresponda; teclado virtual y orientación horizontal.
- Foco no oculto; texto, estados y controles significativos con contraste aplicable. Las excepciones de targets web se documentan; no se confunden pt/dp con CSS px.
- Labels completos accesibles al truncar, orden de lectura, anuncios status/alert sin duplicación y sin mover foco durante polling.
- Tablas/resúmenes equivalentes para cada dato imprescindible del gráfico; operaciones sin dependencia exclusiva de hover.

La conformidad que se declare debe limitarse a lo efectivamente comprobado. Ningún escaneo aislado sustituye teclado y lectura de estados.

## PHASE 8 · Stress testing

**Scope.** Someter la UI final a contenido extremo y transiciones de estado con fixtures existentes: nombres/IDs largos, archivos extensos, pocos/muchos registros, ceros, ausentes, filtros vacíos, errores de red/JSON, conflicto, falta de Owner, archivo, stale y cambios rápidos de ruta.

**Dependencies.** Versión candidata estabilizada y criterios de aceptación por componente. Usar stack desechable y datos sintéticos; no cuentas personales ni acciones de negocio productivas.

**Risk.** MEDIUM en fixtures/integración. No ejecutar scripts de carga, destrucción, aprobación o invalidación contra producción.

**Expected impact.** Encontrar fallos de composición o recuperación que no aparecen en un recorrido ideal de demo.

**Components affected.** Todas las superficies auditadas, coordinador de workspace, cancelación y consumidores históricos que puedan verse afectados por CSS compartido.

**Findings.** Cierre de UX-001–UX-020 y decisiones explícitas de aceptar/diferir UX-021–UX-024. Los opcionales no se implementan por inercia.

**Acceptance.**

- Matriz viewer/operator/admin y miembro no elegible, con permisos verificados por backend en las suites existentes.
- Back/Forward, reload, BFCache, doble clic, Escape rápido, cambio de Case/Decision durante una consulta y disposal de vistas.
- Lectura de Runs históricos y candidatos, estados error/stale y descargas, sin restaurar aprobaciones desde cache.
- Golden workflow completo en entorno aislado; comparación de fallos con la baseline vigente para distinguir deuda histórica y regresiones nuevas.
- El árbol probado y el diff final sólo contienen cambios UX/UI aprobados; sin cambios inadvertidos en motor, SQL, OpenAPI, datasets o formatos de sesión.

Podrá utilizarse `break-ui` en una etapa futura explícitamente autorizada y acotada a fixtures. No se ejecutó en esta entrega. Lo mismo aplica a Skills adicionales de animación.

## Matriz resumida de dependencias

| Fase | Depende de | Entrega revisable |
| --- | --- | --- |
| 0 | Aprobación de alcance | Roles, consumidores, baseline y criterios |
| 1 | 0 | P0 cerrados, shell/primitives y foco |
| 2 | 1 | Datos/Map y contexto más compactos |
| 3 | 1–2 | Config D1/D2 con payloads preservados |
| 4 | 0–3 | Dashboards y evidencia precisos |
| 5 | 1; patrones estables de 2–4 | Plataformas de soporte consistentes |
| 6 | Layouts estabilizados | Estados y feedback verificados |
| 7 | 1–6 | Matriz responsive/accessibility cerrada |
| 8 | 1–7 | Candidata resistente y evidencia de regresión |

La dependencia ordena el trabajo; no requiere esperar Phase 5 para reparar el label KPI de UX-006 si se integra de forma segura con la primitive correspondiente.

## Verificación y control de regresión

La auditoría actual fue de lectura y creó únicamente estos documentos. Las verificaciones siguientes corresponden a una futura implementación aprobada:

1. Registrar SHA/estado de trabajo y baseline de los consumidores afectados. No afirmar que CI global es verde si conserva deuda histórica documentada.
2. Para cambios de presentación, inspección de computed styles, capturas y operación de los estados realmente afectados. No añadir pruebas que sólo repitan un literal CSS.
3. Para UX-002, incorporar una regresión significativa del foco visible con sticky y contenido largo; para patrones compartidos, cubrir consumidores D1 y D2.
4. Si se modifica JS, ejecutar syntax/import/contract y las pruebas pertinentes del componente. El proyecto no necesita una toolchain React/TypeScript nueva.
5. Antes de cerrar la integración, ejecutar los journeys y gates requeridos del repositorio, incluida regresión real de autoridad/lineage en stack aislado. Comparar identidades de fallos históricos, sin ocultarlos por recuento.
6. Confirmar igualdad de contratos públicos y ausencia de modificaciones en archivos protegidos de motor/SQL. Una UI más clara no justifica migraciones, replay SQL o escritura de datos productivos.

La publicación es una acción posterior con su propio resultado revisable; este roadmap no la ejecuta ni da por aprobada. El punto de cierre de esta entrega son los tres documentos.

## Próximo lote recomendado

Aprobar la dirección y un primer lote acotado de UX-001/UX-002, con criterios de aceptación por texto funcional y foco visible; después ampliar a densidad, tipografía y componentes compartidos. No iniciar implementación hasta recibir esa aprobación.

## Registro de ejecución

La auditoría y la propuesta originales se conservan. Este registro documenta la implementación autorizada posterior.

| Phase | Estado | Alcance / evidencia | Commit |
| --- | --- | --- | --- |
| 0 | Complete | Roles de tipografía, superficies y radios del sistema existente; Inter y paleta preservadas; QA: 6 tests unitarios de primitives y 7 browser de plataforma; diff check limpio | ebd4089 |
| 1 | Complete | UX-001/002/019/020: Overview vigente, foco sin oclusión, SVG y skip; familia de acciones compartida; QA: 21 browser existentes y 2 regresiones nuevas pasan; 57 observaciones de 4 resoluciones sin overflow ni errores JS; Python baseline 383 OK | 5b0c717 |
| 2 | Complete | UX-003/004/005/013: contexto compacto, ayuda desplegable, paso actual visible y metadatos legibles; QA: 13 browser del flujo OK; 9 unitarios del Map y 18 Node OK; 8 capturas finales sin overflow; entrada a decisiones 207 px antes en móvil | c4afce0 |
| 3 | Complete | Config D1/D2 compacta; UX-010 en Config: fuente aprobada y fija; mismos builders, defaults y capacidades; QA: 73 unitarios OK; 7 de 8 browser OK (1 aserción preexistente Cambiar datos/Data Pack); 8 capturas sin overflow; ejecución D2 y review/pesos verificadas | 93af44b |
| 4 | Complete | UX-007/008/009/010/016/017/018: números, launcher en toolbar, copy fiel y unidades de presentación; fotografías conservadas; QA: 38 unitarios OK; 6 browser existentes y 2 nuevas de exportación/aprobación OK; 2 tests históricos incompatibles con controles ya retirados; 9 observaciones sin overflow | 6017263 |
| 5 | Complete | UX-006/011/014/015/016: KPI móvil, errores presentables, carga compartida, filtros y áreas inline; Hub numérico; QA: 4 browser relevantes verificados (invitaciones repetida con fixture Team); 18 Node OK; 24 observaciones sin overflow; permisos y contratos preservados | 9aa532c |
| 6 | Complete | improve-animations + review-animations: retirar entradas repetidas, traslaciones y width animado; feedback inmediato conservado; review Approve; QA: 11 browser OK; dialog 375 px estable y foco restaurado con ambas preferencias; sin motion añadido ni dependencia | incluido en este commit |
| 7 | Pending | — | — |
| 8 | Pending | — | — |
