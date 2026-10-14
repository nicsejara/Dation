# Dark Rebrand / Grow-Up — Fase 5: Dashboards y toolbar

## A. Alcance

Assignment, Scheduling y los resultados históricos Dispatch adoptan superficies oscuras para KPI, evidencia, tablas, validación, comparativa, calendario, gráficos, explicación y chat. La toolbar compartida distingue Aprobar/Continuar de Decision Map, Exportar y Más mediante jerarquía e iconos SVG. No cambia el motor, las opciones enviadas, el esquema de Supabase, los permisos ni las dependencias. Se conserva el workspace privado compartido.

## B. Componentes y estilos

Los propietarios actuales conservan su DOM y sus hooks. Se retira el bridge light de `decision-dashboard` y chat. Los colores operativos compartidos de `dispatch.css` usan roles públicos; las páginas que aún tienen bridge conservan sus pares light. El gradiente del hero histórico se migra en su selector original. Los KPI mantienen sus cálculos y unidades; las tablas tienen cabecera sticky opaca, separadores sutiles, hover y scroll local. El acento textual usa un rol de contraste suficiente sobre las superficies elevadas.

`styles.mjs` extrae el loader probado de Config: deduplica por pathname, espera load, permite retry de una descarga fallida y conserva la versión de Config. Dashboard espera sus hojas antes de montar; una respuesta tardía no puede reabrir la ruta abandonada. El scope cancela listeners y observadores al navegar.

## C. Gráficos y calendario

`chart-theme.mjs` combina opciones de presentación sin mutar datos, callbacks, unidades, formatters, tipografía personalizada ni descripción accesible. Configura ejes, grilla, leyenda, títulos, series y tooltip SVG/richText con fondo oscuro. `shared.chart()` libera instancias y ResizeObserver y adapta el margen del eje al cruzar 480 px en navegación warm, sin reemplazar los datos.

Scheduling conserva fechas, offsets y duraciones. El calendario tiene altura proporcional a sus filas dentro de un viewport con scroll nativo y nombre accesible. La primera fila aparece arriba; se evita repetir el ID dentro de barras pequeñas. El eje, tooltip y tabla conservan la identificación del viaje y vehículo. Los gráficos mantienen su tabla alternativa.

## D. Interacciones y evidencia histórica

Exportar y Más son mutuamente excluyentes, incluso al abrir `details` por código. Click exterior cierra ambos; Escape restaura foco al summary. Abrir Detalles cierra menús y conserva el trap y restore del drawer. Los paneles se miden y limitan al viewport; la toolbar mide la altura real de la topbar. Aprobar, Continuar, exportación CSV/JSON y sus errores conservan sus callbacks.

La comparativa conserva Generate, Close, Reopen, Restore y Retry. Su copy habla de comparativa, sin reintroducir selección de profundidad. Abrir, cerrar o restaurar un resultado no modifica la corrida base ni recalcula el histórico. Las nuevas Assignment mantienen el contrato essential de Fase 4 y su riesgo funcional medido en el informe anterior; esta fase no cambia ese contrato.

Chat conserva historial paginado, provenance, abort y el mismo turn_id en retry. Cierre y Escape restauran foco, aria-expanded y la clase del dashboard tanto en Assignment como en Scheduling. La explicación conserva generación, regeneración, estados de carga/error y evidencia guardada; sus botones conservan SVG después de un error.

## E. Validación funcional

Gate de suites: 349 Python, 40 Node, 91 Chromium, 46 SQL en PostgreSQL 17 y siete E2E reales desechables: **533 casos**. Las tres nuevas pruebas Node verifican combinación inmutable de opciones y adaptación del gráfico sin alterar datos. Ocho nuevas pruebas Chromium cubren exclusión de menús, teclado, capas, navegación y cleanup, contraste, calendario/tooltip SVG, chat, comparativa, CSS tardío e históricos con exportación JSON original.

La suite existente sigue comprobando aprobación/continuación, retry, CSV, lineage, interpretación, historial y recuperación. El E2E usa API, worker, base y storage desechables. Compilación Python, sintaxis de 64 módulos/scripts frontend, `pip check` y `git diff --check` deben pasar. El CI debe estar verde en el head exacto del PR y en el merge de main.

## F. QA visual y publicación

Anchos 1440, 1280, 1024, 768 y 390 px, también con preferencia de sistema light. La matriz local de 60 estados cubre base, Exportar, Más, drawer, chat, pestañas y detalle de viaje. El calendario añade captura del tooltip en cada ancho y auditoría de texto SVG real. Se comprueba contraste compuesto AA, ausencia de overflow del documento, geometría de menús y foco. Una matriz adicional de 24 estados a 1440/390 px captura comparativa disponible, en cola, con error, completada, cerrada y reabierta; explicación cargando, con error y generada; chat cargando, con error y retry exitoso. Sin fallos AA ni overflow. IA, estados de comparativa y chat se ejercitan con API sintética; las escrituras funcionales se validan en E2E desechable.

La publicación usa Cloud Build enlazado a GitHub. Se verifica source SHA, cuatro pasos, revisiones y tráfico, template y assets por SHA-256, acceso privado, readiness, dependencias, ETag y heartbeat del worker. La QA productiva añade ambos dashboards, menús, drawer, chat y tooltip a la matriz anterior. Sólo permite GET y preflight/preview de cálculo; bloquea escrituras persistentes y compara hashes de los casos, corridas y comparativa revisados antes/después. No genera explicaciones ni mensajes de prueba en producción.

Capturas e informes locales: `/workspace/dation-audit/rebrand-phase5-visual/`, `rebrand-phase5-production-final.json` y evidencia final del PR. El PR registra los SHAs, CI y despliegue concretos después de completar los gates.

## G. Riesgos y deuda

La paleta es compartida por los gráficos y se prueba sobre el SVG renderizado, además de las opciones puras. Los datasets extensos siguen usando scroll local; esta fase no garantiza legibilidad simultánea de todas las filas. El error/carga compartido recibe roles semánticos; Map, historial y trace que todavía conservan bridge requieren su revisión de consolidación. No se eliminan masivamente reglas legacy sin demostrar ausencia de consumidores.

Fase 6 amplía accesibilidad y responsive, zoom, autofill, pickers nativos y recorrido completo; Fase 7 consolida estilos y retira deuda demostrada. Rollback: revertir el merge y desplegar ese commit mediante Cloud Build. No hay migraciones ni datos que revertir en esta fase.

## H. Gate

**FASE 5 COMPLETA — LISTA PARA FASE 6** sólo después de suites verdes, integración y verificación productiva del commit exacto registradas en el PR. No iniciar Fase 6 automáticamente. El entorno reutilizable conserva instalación, red y bindings y fija el commit publicado.
