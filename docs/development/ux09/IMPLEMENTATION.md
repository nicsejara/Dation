# UX09 — Ultimate Visual Refinement

Base verificada: `main` / `d2abe7f69e411fece0f44207fb720c2c682666da` (UX08, PR #124). Rama exclusiva: `codex/ux09-premium-precision`. Requerimientos: paquete UX09 v1.0 del propietario, consolidado y sus precedencias. Esta entrega prepara revisión; no autoriza merge ni activación productiva.

## Los tres bloques

1. **Core Configuration Footers.** Una fila normal de 96 px en 1536/1280, ancho exterior intacto, Previous y anillo de 44 px. Dos separadores alrededor de un slot contextual. Se trasladan los nodos de feedback existentes, conservando sus referencias vivas, roles y actualizaciones. En móvil se apilan las notas reales y los botones. Los errores/conflictos pueden aumentar la altura y conservan la acción confirmada de descarte/recarga.
2. **Data Owner & Data Sessions.** Tarjetas independientes 2:1, altura compartida desktop, iconos de 48 px, títulos de 16 px, selector de 40 px y separación de 22 px al footer. La consulta existente de preparaciones informa carga, cero, cantidad compatible o error/reintento. `Ver sesiones` es secundaria; las opciones usan fecha/estado humano. No se inventan cantidades de archivos.
3. **Decision Graph Premium Precision.** Estado del Case ocupa su columna (36 px normales). D1/D2 comparten tracks de identidad, Estado, Salida y cierre; las dos cajas tienen 40 px normales. Salida es información, sin acción. Se incorporan iconos de 22 px a Decision Owner y Acciones. Permanecen los cuatro hechos, cinco acciones, razones reales, caret, selección/toggle, cierre, Escape y restauración de foco.

No se copian estados, nombres o resultados ficticios de los mockups. Un texto largo puede crecer en altura; no se trunca un error para imponer medidas.

## Archivos de aplicación y propósito

| Archivo | Intervención |
|---|---|
| `backend/app/static/css/ultimate-foundation.css` | Grid de los tres footers, notas contextuales, dos tarjetas y reflow responsive |
| `backend/app/static/js/dispatch/models/wizard-ui.mjs` | Slot contextual: mueve los elementos existentes y conserva sus listeners/referencias |
| `backend/app/static/js/dispatch/models/forms.mjs` | Inserta el botón de recarga por conflicto dentro del slot; fallback histórico conservado |
| `backend/app/static/js/dispatch/upload/core-preparation.mjs` | Tarjeta Data Sessions, disponibilidad y recuperación segura sobre las API existentes |
| `backend/app/static/css/ultimate-graph.css` | Badge Case y geometría compartida de encabezados/íconos D1/D2 |
| `backend/app/static/js/dispatch/graph-ux05/decision-popover.mjs` | Caja informativa Salida, cierre en su track e iconos; mismas acciones y proyección de estado |

Pruebas: nuevo `backend/tests/browser/test_visual_precision_ux09.py` (siete escenarios) y adaptación de las expectativas visuales de `test_premium_refinement_ux08.py`. Se preservan sus comprobaciones funcionales. El resto del diff es documentación y evidencia aislada.

## Contrato de sesiones preservado

La lista está limitada por el backend a actor/workspace y diez entradas, con máximo de cinco preparaciones activas. Se filtra por versión y origen, excluyendo la sesión actual. DRAFT/VALIDATED requieren vigencia. **FINALIZING sigue siendo recuperable incluso después de su fecha de vencimiento**, porque el backend conserva el intento de creación congelado. CONSUMED y EXPIRED ordinarias no se ofrecen. No se cambia el servicio ni SQL.

La respuesta debe tener estructura válida y IDs únicos. Auth/permisos, 5xx, timeout o formato parcial muestran un error local y reintento; no se convierten en un falso cero ni bloquean la carga actual. Se cancela la consulta al cambiar de recurso/desmontar; se invalida por ID, revisión, versión y origen. La edición ordinaria no provoca polling. Focus y apertura permiten refrescar sin temporizadores.

Al seleccionar se verifica únicamente el recurso elegido, no cada elemento de la lista. Se valida su identidad y el intento congelado antes de cambiar el borrador; los CSV locales y el intento de creación actual conservan sus guardas. El cambio de sesión participa en la promesa de readiness existente: no puede finalizarse un Case con la sesión anterior mientras está pendiente su lectura/restauración. Un fallo de lectura o restauración rechaza esa espera; la recuperación posterior se prueba contra el mismo recurso. No se cambian payloads de creación, permisos ni ecuaciones de readiness del servidor.

El escenario duradero utiliza API/SQL/Storage aislados: induce un fallo de publicación, retoma FINALIZING vencida desde una pestaña nueva y comprueba un único Case y un único Pack final. Nunca se ejecuta contra Supabase productivo.

## Riesgo y límites

Riesgo **R2** según el clasificador sin modificaciones: presentación más consultas de disponibilidad en frontend. Riesgos cubiertos: carreras de selección/versión/desmontaje, respuesta ambigua, doble creación, conflictos de revisión, mensajes largos y reflow. La disponibilidad es una instantánea, no un lock; el servidor vuelve a validar el recurso al recuperarlo.

No se modifican backend, API, SQL, Supabase, motores, feature flags, permisos, persistencia, rutas, dashboards, dependencias, infraestructura ni workflows. La verificación de motores consiste en diff inalterado y ausencia de activación; no representa un inventario live de producción. Los snapshots muestran datos sintéticos, no datos del propietario.

## Activación posterior y rollback

1. Revisar el único PR, la matriz de 59 criterios y su SHA/checks terminales. Esta tarea deja el PR abierto.
2. Sólo con autorización posterior, integrar y usar el runbook productivo existente con una imagen de digest inmutable; no se crea otro mecanismo de despliegue aquí.
3. Verificar en la futura revisión candidata footers, lookup/error/recuperación, permisos de Owner y D2 bloqueada; conservar flags de motores y scale-to-zero.
4. Rollback de código: revertir el commit de integración de este PR y validar por los controles vigentes. Si hubiera una promoción posterior, volver al digest/revisión previamente verificados usando el runbook existente. No se propone un SHA de producción no comprobado.

No requiere migración, datos de relleno ni reparación de historial SQL. No se ha mergeado, publicado una imagen, desplegado, ejecutado Jobs ni cambiado tráfico.
